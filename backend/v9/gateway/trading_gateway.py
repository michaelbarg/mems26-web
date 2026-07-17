"""TradingGateway — 3-mode trade routing per 3-Mode Spec V3 section 8.

Modes:
  SHADOW: unlimited parallel trades, always active, record-only
  DEMO:   single slot, one trade at a time, simulated execution
  LIVE:   single slot, one trade at a time, strict risk checks, real orders

Cross-context: at route_setup time, snapshot all 6 systems' state.
"""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .risk_checks import passes_strict_checks
from .cooldown import CooldownManager, ClusterGuard
from .suffering_side_veto import SufferingSideVeto
from backend.v9.services.sierra_command import command_from_setup
from backend.v9.gateway.session_gate import is_within_firing_window
from backend.v9.services.trade_context import extract_g1_entry_context


def resolve_pattern_id(setup: dict, g1: dict) -> Optional[str]:
    """Resolve pattern_id_at_entry: prefer the firing setup's classification.

    Bug fix (2026-06-12): g1 reads from woodies_system snapshot which reflects
    S4's active pattern. For S2 trades this produced wrong pattern_ids
    (id 43: REACTIVE_LONG recorded as VEGAS). Now: setup.classification first,
    metadata.pattern second, g1 fallback last.
    """
    return (
        setup.get("classification")
        or (setup.get("metadata") or {}).get("pattern")
        or g1.get("pattern_id_at_entry")
    ) or None

logger = logging.getLogger(__name__)

import os as _os
# Use the same DATABASE_URL as db/session.py — no more hardcoded path.
# Tests can override via DATABASE_URL or db_path constructor arg.
_DB_URL = _os.environ.get("DATABASE_URL", "sqlite:///./data/mems26_local.db")
DB_PATH = _DB_URL.replace("sqlite:///", "") if _DB_URL.startswith("sqlite") else "./data/mems26_local.db"


def _zone_limit_parse_ts(value) -> Optional[float]:
    """Parse a setup bar/signal timestamp into epoch-seconds UTC (N3 gate).

    Accepts epoch seconds (int/float/numeric str), epoch milliseconds
    (heuristic: >1e12), or ISO-8601 (naive treated as UTC — repo convention,
    bar `ts` columns are UTC; Rule 4: the TZ is stated here, not assumed
    silently). Values that cannot be a modern epoch (< 1e9, e.g. a bar
    INDEX leaking into bar_ts) return None. None/unparseable → None: the
    age check is SKIPPED (fail-open), never guessed.
    """
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            ts = float(value)
        elif isinstance(value, str) and value.strip().lstrip("+-").replace(".", "", 1).isdigit():
            ts = float(value.strip())
        elif isinstance(value, str) and value.strip():
            s = value.strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        else:
            return None
        if ts > 1e12:  # epoch milliseconds
            ts /= 1000.0
        if ts < 1e9:   # not a plausible modern epoch (bar index etc.)
            return None
        return ts
    except (TypeError, ValueError):
        return None


# ── STOP_TABLE_V1 (default OFF) — per-pattern × day_type stop cap table ───────
# Michael's gap: targets ARE per-pattern×day_type (targets.yaml
# pattern_t1_points), but STOPS were a generic CONT/REV ATR-band resolver with
# no day_type input. STOP_TABLE_V1 lets STOP_RESOLVER_V1 consult the
# `pattern_stop` block in config/stop_anchors.yaml so the ATR band cap becomes
# pattern+day_type aware. The table can ONLY tighten (or equal) the generic cap
# — it NEVER widens risk beyond today's global cap. Flag OFF, or pattern×
# day_type absent, → byte-identical to the generic resolver. SHADOW-first.
_PATTERN_STOP_CACHE: Optional[Dict] = None
_PATTERN_STOP_LOADED: bool = False


def _load_pattern_stop_table() -> Dict:
    """Load the `pattern_stop` block from config/stop_anchors.yaml (cached).

    Shape mirrors targets.yaml pattern_t1_points:
        {PATTERN: {day_type: {max_risk_pts?, band_cap_atr?, anchor_type?}}}
    Reuses config_loader.load_stop_anchors (schema-validated; it ignores the
    extra top-level pattern_stop key). Fail-open to {} on any error/missing —
    which yields the unchanged generic resolver.
    """
    global _PATTERN_STOP_CACHE, _PATTERN_STOP_LOADED
    if _PATTERN_STOP_LOADED:
        return _PATTERN_STOP_CACHE or {}
    _PATTERN_STOP_LOADED = True
    _PATTERN_STOP_CACHE = {}
    try:
        from backend.v9.config_loader import load_stop_anchors
        data = load_stop_anchors()
        if isinstance(data, dict):
            ps = data.get("pattern_stop")
            if isinstance(ps, dict):
                _PATTERN_STOP_CACHE = ps
    except Exception as _ps_err:  # pragma: no cover - defensive fail-open
        logger.warning("[Gateway] pattern_stop load errored (fail-open): %s", _ps_err)
    return _PATTERN_STOP_CACHE


def _reset_pattern_stop_cache() -> None:
    """Reset the pattern_stop cache — test hygiene only."""
    global _PATTERN_STOP_CACHE, _PATTERN_STOP_LOADED
    _PATTERN_STOP_CACHE = None
    _PATTERN_STOP_LOADED = False


def _stop_table_lookup(table: Dict, classification: Optional[str],
                       day_type: Optional[str]) -> Optional[Dict]:
    """Return the pattern_stop entry for classification×day_type, else None."""
    if not table or not classification or not day_type:
        return None
    entry = (table.get(str(classification).upper()) or {}).get(day_type)
    return entry if isinstance(entry, dict) else None


def _stop_table_effective_cap(generic_cap_pts: float, atr_5m: float,
                              entry: Optional[Dict]) -> float:
    """Tighten-only cap = min(generic_cap, max_risk_pts, band_cap_atr × atr).

    entry None/empty → returns generic_cap unchanged. The result can NEVER
    exceed generic_cap: the table only makes the cap MORE specific (tighter),
    never widens risk beyond the existing global ATR cap.
    """
    cap = float(generic_cap_pts)
    if not entry:
        return cap
    mr = entry.get("max_risk_pts")
    if isinstance(mr, (int, float)) and mr > 0:
        cap = min(cap, float(mr))
    bc = entry.get("band_cap_atr")
    if isinstance(bc, (int, float)) and bc > 0 and atr_5m and atr_5m > 0:
        cap = min(cap, float(bc) * float(atr_5m))
    return cap


def _stop_table_decide_cap(*, enabled: bool, table: Dict,
                           classification: Optional[str], day_type: Optional[str],
                           generic_cap_pts: float, atr_5m: float):
    """Return (effective_cap_pts, entry_used).

    Disabled OR no matching pattern×day_type entry → (generic_cap_pts, None):
    byte-identical to the generic resolver. Otherwise → (tightened_cap, entry).
    Tighten-only (see _stop_table_effective_cap).
    """
    if not enabled:
        return float(generic_cap_pts), None
    entry = _stop_table_lookup(table, classification, day_type)
    if not entry:
        return float(generic_cap_pts), None
    return _stop_table_effective_cap(generic_cap_pts, atr_5m, entry), entry


def _stop_table_should_apply(*, in_band: bool, rejected: bool,
                             risk_points: float, effective_cap_pts: float,
                             generic_cap_pts: float) -> bool:
    """Apply the resolved stop only if it is in-band AND within the (possibly
    tightened) effective cap. A smaller effective_cap can only turn an apply
    into a keep-original — never the reverse (tighten-only, never widen).

    Byte-identical guarantee: when the effective cap is NOT tighter than the
    generic cap (flag OFF, no entry, or a no-op entry), an in-band non-rejected
    result is applied verbatim — the extra cap check is skipped entirely, so
    tick-grid snapping in resolve_stop can never flip today's decision. Only a
    genuinely tightened cap adds the risk_points ≤ effective_cap constraint.
    """
    if not in_band or rejected:
        return False
    if float(effective_cap_pts) >= float(generic_cap_pts):
        return True
    return float(risk_points) <= float(effective_cap_pts) + 1e-9


class TradingGateway:
    """Central trade routing: SHADOW (unlimited) / DEMO (1 slot) / LIVE (1 slot + risk)."""

    def __init__(self, db_path: str = None, system_registry: Dict = None):
        self.db_path = db_path or DB_PATH
        self._system_registry = system_registry or {}
        self.shadow_trades: List[Dict] = []
        self.demo_slot: Optional[Dict] = None
        self.live_slot: Optional[Dict] = None
        self._demo_enabled_systems: set = set()
        self._live_enabled_systems: set = set()
        self._daily_trades: int = 0
        self._daily_pnl: float = 0.0
        self._consecutive_losses: int = 0
        # ζ.A4 + ζ.A5 + ζ.B2: risk filters
        self.cooldown = CooldownManager()
        self.cluster_guard = ClusterGuard()
        self.ssv = SufferingSideVeto()
        self._trade_manager = None
        # D-094: R:R fire selection (flag OFF = first-wins, flag ON = same-bar buffering)
        import os
        self._rr_selection_enabled = os.environ.get(
            "RR_FIRE_SELECTION", ""
        ).lower() in ("1", "true", "yes")
        self._slot_candidates: List[Dict] = []  # buffered DEMO/LIVE candidates
        self._recent_fires: List[Dict] = []  # idempotency: catch exact double-fires (e.g. 199/200)
        # P3: opposite-pattern exit counter (flag OPPOSITE_EXIT_V1, default OFF)
        self._opposite_count: int = 0
        self._opposite_bar_ts: Optional[str] = None  # reset per bar
        # 07-15 Michael ("שיהיה ברור בכל רגע נתון למה לא ירה"): every route_setup
        # decision — fired OR blocked+reason — recorded in-memory for the panel.
        # Ring buffer, no I/O on the hot path; survives until backend restart
        # (full history stays in logs/DB as before).
        from collections import deque as _deque
        self.decisions = _deque(maxlen=300)

    def set_system_registry(self, registry: Dict) -> None:
        """Inject system references for cross-context snapshots."""
        self._system_registry = registry

    def set_trade_manager(self, trade_manager) -> None:
        """W11 TradeManager — SHADOW lifecycle + PnL via BarLevelDetector."""
        self._trade_manager = trade_manager

    def hydrate_demo_slot(self) -> None:
        """Restore demo_slot from an open PARTIAL/FILLED demo trade in v9_trades.

        On restart, the slot is None — any open demo trade is orphaned.
        This queries the DB for the most recent non-CLOSED demo trade and
        re-populates the slot so (a) it's managed by BarLevelDetector and
        (b) new signals don't create a second demo trade.
        """
        try:
            from backend.v9.db.read import read_one
            row = read_one(
                "SELECT id, direction, entry_price, pattern_id_at_entry, firing_system "
                "FROM v9_trades "
                "WHERE mode = 'demo' AND state NOT IN ('CLOSED', 'CANCELLED') "
                "ORDER BY id DESC LIMIT 1", {},
            )
            if row:
                self.demo_slot = {
                    "trade_id": row["id"],
                    "direction": row.get("direction"),
                    "entry_price": float(row.get("entry_price") or 0),
                    "mode": "demo",
                }
                logger.info("[Gateway] hydrated demo_slot from DB: trade %d (%s %s)",
                            row["id"], row.get("pattern_id_at_entry"), row.get("direction"))
            else:
                logger.info("[Gateway] no open demo trade in DB — demo_slot=None (free)")
        except Exception as e:
            logger.warning("[Gateway] demo_slot hydration FAILED (query error, slot stays None): %s", e)

    def hydrate_live_pnl(self) -> None:
        """BOOT_HYDRATION_V1: Restore daily PnL counters from v9_trades.

        On restart, _daily_pnl/_daily_trades/_consecutive_losses reset to 0.
        This is a risk hole: the daily loss halt forgets prior losses.
        Restores from today's closed LIVE trades in the DB.
        """
        try:
            from backend.v9.db.read import read_all, read_scalar
            from backend.v9.services.market_clock import now_et
            from datetime import time as _time_cls, timedelta

            et_now = now_et()
            # RTH session date: today if after 09:30 ET, else yesterday
            if et_now.time() >= _time_cls(9, 30):
                session_date = et_now.strftime("%Y-%m-%d")
            else:
                session_date = (et_now - timedelta(days=1)).strftime("%Y-%m-%d")
            session_start = session_date + " 09:30:00"

            daily_pnl = read_scalar(
                "SELECT COALESCE(SUM(pnl_usd), 0.0) FROM v9_trades "
                "WHERE mode = 'live' AND state = 'CLOSED' "
                "AND exit_ts >= :ss",
                {"ss": session_start},
            )
            daily_trades = read_scalar(
                "SELECT COUNT(*) FROM v9_trades "
                "WHERE mode = 'live' AND state = 'CLOSED' "
                "AND exit_ts >= :ss",
                {"ss": session_start},
            )

            # Consecutive losses: walk backwards from most recent
            rows = read_all(
                "SELECT pnl_usd FROM v9_trades "
                "WHERE mode = 'live' AND state = 'CLOSED' "
                "AND exit_ts >= :ss "
                "ORDER BY exit_ts DESC",
                {"ss": session_start},
            )
            cons_losses = 0
            for row in rows:
                if float(row["pnl_usd"]) < 0:
                    cons_losses += 1
                else:
                    break

            self._daily_pnl = float(daily_pnl or 0.0)
            self._daily_trades = int(daily_trades or 0)
            self._consecutive_losses = cons_losses

            logger.info(
                "[Gateway] BOOT_HYDRATION: daily_pnl=$%.2f trades=%d consecutive_losses=%d "
                "(from %s 09:30 ET)",
                self._daily_pnl, self._daily_trades, self._consecutive_losses, session_date,
            )
        except Exception as e:
            logger.warning("[Gateway] BOOT_HYDRATION failed (non-fatal, counters stay 0): %s", e)

    def enable_demo(self, system_id: int) -> None:
        self._demo_enabled_systems.add(system_id)

    def disable_demo(self, system_id: int) -> None:
        self._demo_enabled_systems.discard(system_id)

    def enable_live(self, system_id: int) -> None:
        self._live_enabled_systems.add(system_id)

    def disable_live(self, system_id: int) -> None:
        self._live_enabled_systems.discard(system_id)

    @staticmethod
    def _rr_unclassified_relief_window() -> bool:
        """RR relief window for UNCLASSIFIED-label periods: 10:00–16:00 ET.

        Michael ruling 2026-07-16 (~17:55 IDT, "מאשר — תקן עכשיו"): the strict-1.0
        R:R fallback while the day is merely unclassified (get_live_day_type →
        None, low-conf early session) blocked the 7597×2 borderline winners
        before a +15pt run. Relief may apply in that state too — but NEVER in
        the opening 30min (chase window) and never on error paths.
        Fail-conservative: any error → False (strict 1.0 stays).
        """
        try:
            from datetime import datetime as _dt
            from zoneinfo import ZoneInfo as _zi
            _now = _dt.now(_zi("America/New_York"))
            _m = _now.hour * 60 + _now.minute
            return 600 <= _m <= 960  # 10:00–16:00 ET
        except Exception:
            return False

    def route_setup(self, setup: dict, system_id: int) -> Dict:
        """Route a setup, then LOG the gate block reason so blocks are not silent
        (no silent failures — every blocked setup records WHY it didn't fire)."""
        # 07-15 Michael decision 3/6: pattern propagates through the WHOLE chain.
        # Producers fill `classification`; half the consumers (t1-overrides,
        # playbook, logs, trade record) read `pattern` — which arrived empty on
        # every 07-14 fire ("pattern=None"). Normalize ONCE at the entry point.
        if not setup.get("pattern"):
            _pat = (setup.get("classification")
                    or (setup.get("metadata") or {}).get("pattern"))
            if _pat:
                setup["pattern"] = _pat
        # ── CONFLUENCE_RI_ZLR_V1 (default OFF) — S2×S4 same-bar route-join hook
        # (spec docs/handoff/CONFLUENCE_PATTERN_SPEC_2026-07-17.md §4.1). Register
        # EVERY route attempt BEFORE the gate chain, so a join is seen even when a
        # parent is later blocked by a parent-specific gate (e.g. pattern_loss_
        # breaker:ZLR). observe_route returns the combined setup when this route
        # completes an S2(REACTIVE/INITIATIVE)×S4(ZLR) same-bar/same-direction/
        # Δentry≤1pt join, else None. Flag OFF → immediate None, zero registration.
        # Wrapped so a detector bug can NEVER break parent routing (trading path).
        _conf_setup = None
        try:
            from backend.v9.systems.confluence.confluence_ri_zlr import (
                observe_route as _conf_observe,
            )
            _conf_setup = _conf_observe(setup, system_id)
        except Exception as _conf_err:
            logger.warning(
                "[Gateway] confluence detector errored (parents unaffected): %s",
                _conf_err)
        result = self._route_setup_inner(setup, system_id)
        bb = result.get("blocked_by")
        if bb:
            logger.warning(
                "[Gateway] BLOCKED system=%s pattern=%s dir=%s entry=%s blocked_by=%s",
                system_id,
                setup.get("pattern") or setup.get("pattern_id") or setup.get("setup_kind"),
                setup.get("direction"), setup.get("entry_price"), bb,
            )
        # 07-15: record the decision for the "why didn't it fire" panel (in-memory,
        # newest-last; never raises into the trading path).
        try:
            _outcome = ("blocked" if bb else
                        "live" if result.get("live") else
                        "demo" if result.get("demo") else
                        "shadow_only" if result.get("shadow") else "none")
            self.decisions.append({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "system": system_id,
                "pattern": (setup.get("pattern") or setup.get("pattern_id")
                            or setup.get("setup_kind")),
                "direction": setup.get("direction"),
                "entry": setup.get("entry_price"),
                "blocked_by": bb,
                "outcome": _outcome,
                "trade_id": result.get("live") or result.get("demo") or result.get("shadow"),
            })
        except Exception:
            pass
        # N12 (Michael 2026-07-17 "מסמך שמקבל שורה כל הזמן"): every routing
        # decision → one line in the central daily OPS_LOG. log_event never
        # raises, and the whole hook is wrapped anyway (trading path safety).
        # Skip 'none' outcomes (setup didn't reach any mode — pure noise).
        try:
            if _outcome != "none":
                from scripts.ops_log import log_event as _ops
                _pat = (setup.get("pattern") or setup.get("pattern_id")
                        or setup.get("setup_kind") or "?")
                if bb:
                    _ops("gateway", "WARN",
                         f"BLOCKED {_pat} {setup.get('direction')} "
                         f"@{setup.get('entry_price')} gate={bb} (sys{system_id})")
                else:
                    _ops("gateway", "INFO",
                         f"FIRED[{_outcome}] {_pat} {setup.get('direction')} "
                         f"@{setup.get('entry_price')} trade={result.get('live') or result.get('demo') or result.get('shadow')} (sys{system_id})")
        except Exception:
            pass
        # CONFLUENCE_RI_ZLR: route the joined combined setup as its OWN new setup
        # (classification=CONFLUENCE_RI_ZLR, system 4) through the full gate chain
        # AFTER the parent's routing completed. V1 is SHADOW-ONLY (guard in
        # _route_setup_inner) and parents are NOT suppressed (spec §4.4-V1): by the
        # time the join completes on the second parent's route, the first parent —
        # usually the ZLR — has already routed; holding/suppressing parents is the
        # V2 confluence-priority design and needs a separate Michael ruling. The
        # double-count caveat for the n>=15 analysis is documented in the
        # confluence module docstring. Errors never propagate to the parent.
        if _conf_setup is not None:
            try:
                logger.info(
                    "[Gateway] CONFLUENCE_RI_ZLR join complete: %s entry=%s "
                    "(parents S2+S4 same bar) → routing shadow-only",
                    _conf_setup.get("direction"), _conf_setup.get("entry_price"))
                self.route_setup(_conf_setup, 4)
            except Exception as _conf_err:
                logger.warning(
                    "[Gateway] confluence routing errored (parent result unaffected): %s",
                    _conf_err)
        return result

    def _route_setup_inner(self, setup: dict, system_id: int) -> Dict:
        """Route a trade setup through all 3 modes per spec section 8.

        Args:
            setup: Dict with firing_system, direction, classification,
                   confidence, stop, t1, t2, t3, entry_price, metadata.
            system_id: The firing system ID (1, 2, or 4).

        Returns:
            Dict summarizing what happened in each mode.
        """
        cross_context = self._capture_cross_context()
        result = {"shadow": None, "demo": None, "live": None, "blocked_by": None}

        # CONFLUENCE_RI_ZLR (spec §2/§4.5): C1/C2 = entry±4/±8 and the ≤7pt-capped
        # structural stop are DEFINITIONAL for the combined pattern — the stop/
        # target producers below must not rewrite them (their flags stay untouched
        # for every other pattern). Blocking gates (session, feed, risk, playbook,
        # location, halts, …) still apply to the confluence setup like any other.
        _confluence_fixed = (
            str(setup.get("classification") or "").strip().upper()
            == "CONFLUENCE_RI_ZLR"
        )

        # T5: Kill-switch — instant halt of ALL firing
        try:
            from backend.v9.services.kill_switch import is_engaged as _ks_check
            _ks_on, _ks_reason = _ks_check()
            if _ks_on:
                result["blocked_by"] = "kill_switch"
                logger.warning("[Gateway] BLOCKED by kill-switch: %s", _ks_reason)
                return result
        except Exception:
            pass  # fail-open

        # B-13 D3: session firing gate — NO firing outside 08:30–15:00 CT in ANY mode
        if not is_within_firing_window():
            result["blocked_by"] = "session_gate_closed"
            logger.info("[Gateway] BLOCKED by session gate: outside 08:30–15:00 CT (all modes)")
            return result

        # Item-21: EOD entry cutoff — no new entries in the last 45 minutes before close
        if os.getenv("EOD_RISK_WINDOW_V1", "0").lower() in ("1", "true", "yes"):
            try:
                from datetime import datetime as _dt_eod
                from zoneinfo import ZoneInfo as _ZI_eod
                _ct_now = _dt_eod.now(_ZI_eod("America/Chicago"))
                _ct_min = _ct_now.hour * 60 + _ct_now.minute
                _cutoff_min = int(os.getenv("EOD_ENTRY_CUTOFF_MIN", "45"))
                _close_min = 15 * 60  # 15:00 CT
                if _ct_min >= (_close_min - _cutoff_min):
                    result["blocked_by"] = "eod_entry_cutoff"
                    logger.info("[Gateway] BLOCKED by EOD entry cutoff: %d min before close", _close_min - _ct_min)
                    return result
            except Exception:
                pass  # fail-open

        # T2: Feed watchdog — block ALL fires when canonical streams are stale (LIVE blocker #0)
        # 06-19 incident: bridge died mid-RTH, orphan position. Never trade on a dead feed.
        try:
            from backend.v9.services.feed_watchdog import is_feed_alive
            _feed_ok, _feed_reason = is_feed_alive()
            if not _feed_ok:
                result["blocked_by"] = "feed_watchdog"
                logger.warning("[Gateway] BLOCKED by feed watchdog: %s", _feed_reason)
                return result
        except Exception as _fw_err:
            logger.debug("[Gateway] feed watchdog check failed (fail-open): %s", _fw_err)

        # ζ.A4 + ζ.A5 + ζ.B2 + ζ.F2: pre-trade risk gates (GW-02: no record_attempt before PASS)
        direction = setup.get("direction", "")
        if self.cooldown.is_blocked():
            result["blocked_by"] = "cooldown"
            logger.info("[Gateway] BLOCKED by 2-stop cooldown")
            return result
        # SSV (D-049) — 07-15 Michael ruling ("מאשר את ההמלצה"): ran UNGATED and
        # UNRULED until 07-14, where SHADOW noise poisoned it and vetoed 22 real
        # fires all afternoon (19:00-21:00). Now behind SSV_GATE_V1 (default OFF)
        # and fed by real-money outcomes only (see on_trade_close). Re-enable =
        # calibration on a week of real outcomes + Michael ruling.
        if os.getenv("SSV_GATE_V1", "0").lower() in ("1", "true", "yes"):
            if self.ssv.check_veto(direction):
                result["blocked_by"] = "suffering_side_veto"
                logger.info("[Gateway] BLOCKED by SSV D-049: %s is suffering side", direction)
                return result

        # Idempotency dedup — reject the SAME signal fired twice within a short window
        # (ids 199/200 on 2026-06-22: identical S2 REACTIVE_SHORT @7537.75, 2.16s apart).
        # Applies in ALL modes incl SHADOW (a true duplicate is noise, not a parallel signal).
        # Flag DEDUP_FIRE_GUARD, default OFF. Key = system+direction+pattern+entry(±0.5pt) within 30s.
        if os.getenv("DEDUP_FIRE_GUARD", "0").lower() in ("1", "true", "yes"):
            import time as _dd_time
            _dd_now = _dd_time.time()
            _dd_pat = (setup.get("classification") or (setup.get("metadata") or {}).get("pattern"))
            _dd_ep = setup.get("entry_price")
            self._recent_fires = [f for f in self._recent_fires if _dd_now - f["ts"] < 30.0]
            for _f in self._recent_fires:
                if (_f["system"] == system_id and _f["direction"] == direction
                        and _f["pattern"] == _dd_pat and _dd_ep is not None
                        and _f["entry"] is not None and abs(float(_dd_ep) - float(_f["entry"])) < 0.5):
                    result["blocked_by"] = "duplicate_fire"
                    logger.info("[Gateway] BLOCKED duplicate fire: S%s %s %s @%s (within 30s of an identical fire)",
                                system_id, direction, _dd_pat, _dd_ep)
                    return result
            # I-60 (2026-07-02 18:50 live): registration MOVED to after ALL gates pass
            # (just before shadow execution). Registering here poisoned the 30s window
            # when a fire was blocked downstream (cont_trend_filter) — the improved
            # retry (conf 0.79) was then rejected as duplicate_fire of a fire that
            # never traded.

        # Layer-0 chop fire-veto — DISABLED by default (Michael 2026-06-08).
        # chop_state==SEARCHING must NOT block fires until explicit re-approval.
        # Re-enable ONLY by setting env LAYER0_CHOP_GATE=1 AND with Michael's
        # explicit approval. See CLAUDE.md § "Chop Gates (disabled — approval to
        # re-enable)". When disabled we still compute + log chop_state for
        # observability, but do not block.
        _layer0_chop_enabled = os.getenv("LAYER0_CHOP_GATE", "0").lower() in ("1", "true", "yes")
        if _layer0_chop_enabled:
            chop_state = self._get_chop_state()
            if chop_state == "SEARCHING":
                result["blocked_by"] = "chop_searching"
                logger.info("[Gateway] BLOCKED by Layer 0: chop_state=SEARCHING (high chop)")
                return result
        # FIX 4: skip _get_chop_state entirely when gate disabled (avoids
        # HTTP self-calls that deadlock single-worker uvicorn)

        # #68 FIX B: Opening-type gate — blocks counter-drive during opening window
        # (RTH open → IB lock). After IB lock, inert. Flag OPENING_TYPE_GATE, default OFF.
        if os.getenv("OPENING_TYPE_GATE", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.systems.opening_type_gate import decide as _og_decide
                _og_tpo = (cross_context.get("tpo_system") if isinstance(cross_context, dict) else None) or {}
                _og_ib_locked = bool(_og_tpo.get("ib_locked"))
                # RTH bars from the classifier accumulator (exposed on app.state by main.py)
                _og_rth_bars = getattr(
                    cross_context.get("_cls_rth_bars_ref"), "bars", None
                ) if isinstance(cross_context, dict) else None
                # Fallback: read from day_type_machine in system_registry
                if _og_rth_bars is None:
                    _og_dtm = self._system_registry.get("day_type_machine")
                    _og_rth_bars = getattr(_og_dtm, '_opening_gate_bars', []) if _og_dtm else []
                _allow, _reason = _og_decide(
                    direction=direction,
                    rth_bars=_og_rth_bars or [],
                    ib_locked=_og_ib_locked,
                )
                if not _allow:
                    result["blocked_by"] = "opening_type_gate"
                    logger.info("[Gateway] BLOCKED by opening-type gate: %s", _reason)
                    return result
                logger.debug("[Gateway] opening-type gate PASS: %s", _reason)
            except Exception as _og_err:
                logger.warning("[Gateway] opening-type gate errored (fail-open): %s", _og_err)

        # Day-type playbook fire-veto — DISABLED by default (env DAYTYPE_PLAYBOOK=1
        # + Michael approval). Blocks fires that the pattern×day-type playbook marks
        # SKIP (reversals on a trend day, counter-trend REACTIVE, Nontrend, ...) per
        # config/daytype_playbook.yaml. decide() is fail-open (returns FULL when the
        # flag is off OR pattern/day-type is unmapped), and the whole block is wrapped
        # so a bug can NEVER block a fire. Mirrors the Layer-0 chop gate above.
        # Re-enable is a trading-risk-surface change → strategic stop + Michael sign-off.
        if os.getenv("DAYTYPE_PLAYBOOK", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.systems.daytype_playbook import decide as _pb_decide
                _pb_g1 = extract_g1_entry_context(cross_context)
                _pb_woodies = cross_context.get("woodies_system") if isinstance(cross_context, dict) else None
                _pb = _pb_decide(
                    pattern=resolve_pattern_id(setup, _pb_g1),
                    day_type=_pb_g1.get("day_type_at_entry"),
                    direction=direction,
                    trend_state=(_pb_woodies or {}).get("trend_state"),
                )
                if not _pb.allow:
                    # Item-10 OPENING_WINDOW_FIRE_V1 (default OFF): in the first
                    # 30 min of RTH a POSITIVE with-drive opening signal overrides
                    # a playbook SKIP — the day-type label is an immature stage-1
                    # guess at that hour (incident 2026-07-02 16:35:04 IL:
                    # "ZLR SKIP on Nontrend" 5 min after open). Positive
                    # confirmation only; every other gate still applies.
                    _ow_ok = False
                    try:
                        from backend.v9.systems.opening_type_gate import (
                            opening_window_override as _ow_decide,
                        )
                        _ow_ok, _ow_reason = _ow_decide(direction=direction)
                        if _ow_ok:
                            logger.warning(
                                "[Gateway] OPENING_WINDOW override: playbook '%s' bypassed — %s",
                                _pb.reason, _ow_reason,
                            )
                    except Exception as _ow_err:
                        logger.warning(
                            "[Gateway] opening-window override errored (no override): %s",
                            _ow_err,
                        )
                    if not _ow_ok:
                        result["blocked_by"] = "daytype_playbook"
                        logger.info("[Gateway] BLOCKED by day-type playbook: %s", _pb.reason)
                        return result
                logger.debug("[Gateway] day-type playbook PASS: %s", _pb.reason)
            except Exception as _pb_err:  # fail-open — never block a fire on a bug
                logger.warning("[Gateway] day-type playbook check errored (fail-open): %s", _pb_err)

        # --- Legacy gates (kept for backward compat when old flags ON) ---
        # Trend Direction Gate (CCI-based) — SUPERSEDED by DAYTYPE_POSITION_GATE.
        # When DAYTYPE_POSITION_GATE is ON, this is skipped regardless of its own flag.
        _position_gate_on = os.getenv("DAYTYPE_POSITION_GATE", "0").lower() in ("1", "true", "yes")
        if not _position_gate_on and os.getenv("TREND_DIRECTION_GATE", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.systems.trend_direction_gate import decide as _td_decide
                _td_g1 = extract_g1_entry_context(cross_context)
                _td_ws = (cross_context.get("woodies_system") if isinstance(cross_context, dict) else None) or {}
                _td_ts = _td_ws.get("trend_state")
                _allow, _reason = _td_decide(resolve_pattern_id(setup, _td_g1), direction, _td_ts)
                if not _allow:
                    result["blocked_by"] = "trend_direction_gate"
                    logger.info("[Gateway] BLOCKED by trend-direction gate: %s", _reason)
                    return result
            except Exception as _td_err:
                logger.warning("[Gateway] trend-direction gate errored (fail-open): %s", _td_err)

        # Reactive Location Gate — SUPERSEDED by DAYTYPE_POSITION_GATE.
        if not _position_gate_on and os.getenv("REACTIVE_LOCATION_GATE", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.systems.reactive_location_gate import decide as _rl_decide
                _rl_g1 = extract_g1_entry_context(cross_context)
                _rl_tpo = (cross_context.get("tpo_system") if isinstance(cross_context, dict) else None) or {}
                _allow, _reason = _rl_decide(
                    resolve_pattern_id(setup, _rl_g1), direction,
                    setup.get("entry_price"), _rl_tpo.get("poc"),
                )
                if not _allow:
                    result["blocked_by"] = "reactive_location"
                    logger.info("[Gateway] BLOCKED by reactive-location gate: %s", _reason)
                    return result
            except Exception as _rl_err:
                logger.warning("[Gateway] reactive-location gate errored (fail-open): %s", _rl_err)

        # --- DAYTYPE_LOCATION_GATE v1 (Michael 07-15, default OFF) ---
        # REV fades on rotation days only at the correct value edge in the fade
        # direction (LONG@VAL-side, SHORT@VAH-side). Blocks the #372 class
        # (LONG at the VAH ceiling on Variation). CONT/Trend untouched. Fail-open.
        if os.getenv("DAYTYPE_LOCATION_GATE", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.systems.location_gate import decide_location as _lg_decide
                from backend.v9.systems.daytype_position_gate import _pattern_family as _lg_fam_fn
                _lg_g1 = extract_g1_entry_context(cross_context)
                _lg_tpo = (cross_context.get("tpo_system") if isinstance(cross_context, dict) else None) or {}
                # 07-15: the CANONICAL expansion signal (volume-accepted reference
                # break, P0-1-v2) feeds the gate — CONT on Variation must go WITH it.
                try:
                    from backend.v9.services.trade_context import get_live_expansion as _lg_exp_fn
                    _lg_exp = _lg_exp_fn()
                except Exception:
                    _lg_exp = None
                _lg_allow, _lg_reason = _lg_decide(
                    family=_lg_fam_fn(resolve_pattern_id(setup, _lg_g1) or ""),
                    direction=direction,
                    day_type=_lg_g1.get("day_type_at_entry"),
                    entry_price=setup.get("entry_price"),
                    levels={"vah": _lg_tpo.get("vah"), "val": _lg_tpo.get("val"),
                            "ib_width": (_lg_tpo.get("ib_high") - _lg_tpo.get("ib_low"))
                            if (_lg_tpo.get("ib_high") and _lg_tpo.get("ib_low")) else None},
                    expansion=_lg_exp,
                )
                if not _lg_allow:
                    result["blocked_by"] = "location_gate"
                    logger.info("[Gateway] BLOCKED by location gate: %s", _lg_reason)
                    return result
            except Exception as _lg_err:  # fail-open — never block on a bug
                logger.warning("[Gateway] location gate errored (fail-open): %s", _lg_err)

        # --- #68 Unified Day-Type Position Gate (replaces both above) ---
        # Direction allowed by day-type + price position relative to IB/VA/POC.
        # Flag: DAYTYPE_POSITION_GATE (default OFF). Fail-open.
        if _position_gate_on:
            try:
                from backend.v9.systems.daytype_position_gate import decide as _dp_decide
                _dp_g1 = extract_g1_entry_context(cross_context)
                _dp_tpo = (cross_context.get("tpo_system") if isinstance(cross_context, dict) else None) or {}
                _dp_ws = (cross_context.get("woodies_system") if isinstance(cross_context, dict) else None) or {}
                _allow, _reason = _dp_decide(
                    pattern=resolve_pattern_id(setup, _dp_g1),
                    direction=direction,
                    day_type=_dp_g1.get("day_type_at_entry"),
                    entry_price=setup.get("entry_price"),
                    tpo_ctx=_dp_tpo,
                    trend_state=_dp_ws.get("trend_state"),
                )
                if not _allow:
                    result["blocked_by"] = "daytype_position_gate"
                    logger.info("[Gateway] BLOCKED by day-type position gate: %s", _reason)
                    return result
                logger.debug("[Gateway] position gate PASS: %s", _reason)
            except Exception as _dp_err:
                logger.warning("[Gateway] day-type position gate errored (fail-open): %s", _dp_err)

        # --- #68 Direction-Context gate — blocks fires AGAINST the live CVD+breakout
        # auction direction (direction_context). Flag: DIRECTION_CONTEXT (default OFF),
        # fail-open. The CVD-in-direction lever (validated to fix Neutral/chop, e.g. 06-11:
        # blocks the wrong-side shorts into a failed-low→reversal). Re-enable = trading-
        # surface change → Michael sign-off + backtest.
        if os.getenv("DIRECTION_CONTEXT", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.systems.direction_context_live import current as _dc_current
                _dc = _dc_current()
                _set_dir = "UP" if str(direction).upper() == "LONG" else "DOWN"

                # CONT_TREND_FILTER (default OFF): CONTINUATION patterns must fire WITH a
                # SUSTAINED trend (K-bar LSMA side, dir_sustained). REVERSAL patterns are
                # EXEMPT — they fire against the trend by design (a sustained filter would
                # kill HTLB/VEGAS/GHOST/FAMIR — counterfactual 2026-06-25). Fixes the
                # BULL_FLAG_LONG chop fires that the single-bar veto passed (momentary poke).
                if os.getenv("CONT_TREND_FILTER", "0").lower() in ("1", "true", "yes"):
                    from backend.v9.systems.daytype_position_gate import _pattern_family
                    _pat = resolve_pattern_id(setup, extract_g1_entry_context(cross_context)) or ""
                    _fam = _pattern_family(_pat)
                    # REV (REACTIVE, GHOST, VEGAS, HnS, Double, …) are EXEMPT — they
                    # fire against the trend by design. Only CONT requires sustained trend.
                    # Unknown pattern (_fam=None) → fail-open (not filtered).
                    if _fam == "CONT":
                        _sus = _dc.get("dir_sustained", "NEUTRAL")
                        if _sus != _set_dir:   # NEUTRAL (chop) or opposite → no sustained trend
                            result["blocked_by"] = "cont_trend_filter"
                            logger.info("[Gateway] BLOCKED by cont-trend-filter: %s (CONT) setup %s vs sustained %s",
                                        _pat, _set_dir, _sus)
                            return result

                _dc_dir = _dc.get("dir")
                if _dc_dir in ("UP", "DOWN"):
                    if _set_dir != _dc_dir:
                        # NEUTRAL_RESPONSIVE_V1 (Michael ruling 2026-07-08, live):
                        # on a NEUTRAL day (2-sided, rotational — Dalton) the
                        # direction-context is a trend control and is category-
                        # inappropriate for RESPONSIVE (REV-family) fades at the
                        # extremes — the doctrine play on Neutral days. CONT
                        # patterns stay filtered. Same family map as the
                        # cont-trend-filter exemption above.
                        _nr_exempt = False
                        if os.getenv("NEUTRAL_RESPONSIVE_V1", "0").lower() in ("1", "true", "yes"):
                            try:
                                from backend.v9.systems.daytype_position_gate import _pattern_family as _nr_fam_fn
                                _nr_dt = (extract_g1_entry_context(cross_context) or {}).get("day_type_at_entry") or ""
                                _nr_pat = resolve_pattern_id(setup, extract_g1_entry_context(cross_context)) or ""
                                # 07-15 Michael ("לבדוק שאין מחסם לתבניות במיקום הנכון לפי סוג היום"):
                                # the responsive-fade exemption extends to VARIATION days —
                                # per the doctrine a Variation day finds new value then ROTATES
                                # around VAH/VAL/POC, so REV fades at the edges are THE play
                                # there too, not only on Neutral (07-14: correct fades were
                                # direction-context-blocked while the wrong-side LONG passed).
                                _nr_exempt = (str(_nr_dt).startswith(("Neutral", "Variation", "Normal_Variation"))
                                              and _nr_fam_fn(_nr_pat) == "REV")
                                if _nr_exempt:
                                    logger.info(
                                        "[Gateway] direction-context EXEMPT (neutral-responsive): %s %s on %s",
                                        _nr_pat, _set_dir, _nr_dt)
                            except Exception:
                                _nr_exempt = False  # fail-closed to the original block
                        if not _nr_exempt:
                            result["blocked_by"] = "direction_context"
                            logger.info("[Gateway] BLOCKED by direction-context: setup %s vs %s (%s)",
                                        _set_dir, _dc_dir, _dc.get("reason"))
                            return result
            except Exception as _dc_err:  # fail-open — never block on a bug
                logger.warning("[Gateway] direction-context check errored (fail-open): %s", _dc_err)

        # --- LSMA-flat gate (Michael 2026-07-08): NO fires while the Woodies LSMA is
        # too horizontal (no clear trend angle). |slope| in points/bar over
        # LSMA_FLAT_LOOKBACK_BARS (default 4) must be >= LSMA_FLAT_MIN_SLOPE_PTS
        # (default 0.25 = 1 tick/bar), else BLOCK. Distinct from CONT_TREND_FILTER
        # (SIDE-of-LSMA): flat LSMA + price hugging one side passes dir_sustained but
        # fails here. Distinct from the DISABLED chop gates (S2 choppiness_ok /
        # Layer-0 chop) — those stay OFF per standing decision 2026-06-08; this is a
        # NEW metric. Flag: LSMA_FLAT_GATE_V1 (default OFF). Scope: LSMA_FLAT_SCOPE=
        # ALL (default, per Michael's wording "no trades") | CONT (exempt reversals,
        # same family map as CONT_TREND_FILTER). Fail-open: slope unavailable
        # (missing lsma_value / DB error) → PASS + rate-visible warning (Rule 1 —
        # honest missing, never a synthetic block).
        if os.getenv("LSMA_FLAT_GATE_V1", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.systems.direction_context_live import current as _lf_current
                _lf_slope = (_lf_current() or {}).get("lsma_slope_ppb")
                _lf_min = float(os.getenv("LSMA_FLAT_MIN_SLOPE_PTS", "0.25") or "0.25")
                _lf_scope = (os.getenv("LSMA_FLAT_SCOPE", "ALL") or "ALL").strip().upper()
                _lf_applies = True
                if _lf_scope == "CONT":
                    from backend.v9.systems.daytype_position_gate import _pattern_family as _lf_fam_fn
                    _lf_fam = _lf_fam_fn(resolve_pattern_id(setup, extract_g1_entry_context(cross_context)) or "")
                    _lf_applies = (_lf_fam == "CONT")
                if _lf_slope is None:
                    logger.warning("[Gateway] lsma-flat gate: slope unavailable -> fail-open PASS")
                elif _lf_applies and abs(_lf_slope) < _lf_min:
                    result["blocked_by"] = "lsma_flat"
                    logger.info(
                        "[Gateway] BLOCKED by lsma-flat gate: |slope %.4f| < %.4f pts/bar (flat LSMA, scope=%s)",
                        _lf_slope, _lf_min, _lf_scope)
                    return result
            except Exception as _lf_err:  # fail-open — never block on a bug
                logger.warning("[Gateway] lsma-flat gate errored (fail-open): %s", _lf_err)

        # --- IDEA-1 news blackout (Michael 2026-07-13): NO new entries inside the
        # window around a RED economic event (CPI/PPI/FOMC/NFP — config/news_calendar.yaml).
        # Blocks ENTRY only; management of open trades is untouched. Fail-open on any
        # calendar problem (Rule 1 — honest missing, never a synthetic block).
        # Flag: NEWS_BLACKOUT_V1 (default OFF).
        try:
            from backend.v9.services import news_blackout as _nb
            if _nb.enabled():
                _nb_hit = _nb.check()
                if _nb_hit:
                    result["blocked_by"] = "news_blackout"
                    result["news_event"] = _nb_hit["event"]
                    logger.info("[Gateway] BLOCKED by news-blackout: %s @%s ET (%s)",
                                _nb_hit["event"], _nb_hit["event_time_et"], _nb_hit["window"])
                    return result
        except Exception as _nb_err:  # fail-open — never block on a bug
            logger.warning("[Gateway] news-blackout gate errored (fail-open): %s", _nb_err)

        # Item-18: Day Direction Doctrine (DAY_DIRECTION_DOCTRINE_V1, default OFF)
        # On directional days (Variation/Trend), only with-expansion entries allowed
        # unless a "halt proof" (2 consecutive closes back through the expansion level)
        # has been observed. Reference = expansion side (IB break), NOT local LSMA.
        if os.getenv("DAY_DIRECTION_DOCTRINE_V1", "0").lower() in ("1", "true", "yes"):
            try:
                _dd_g1 = extract_g1_entry_context(cross_context)
                _dd_dt = _dd_g1.get("day_type_at_entry")
                if _dd_dt in ("Variation", "Trend_Normal", "Trend_DD"):
                    _dd_tpo = (cross_context.get("tpo_system") if isinstance(cross_context, dict) else None) or {}
                    _dd_ibh = _dd_tpo.get("ib_high")
                    _dd_ibl = _dd_tpo.get("ib_low")
                    _dd_sh = _dd_tpo.get("session_high") or _dd_tpo.get("rth_high")
                    _dd_sl = _dd_tpo.get("session_low") or _dd_tpo.get("rth_low")
                    # Determine expansion direction
                    _dd_exp_dir = None
                    if _dd_ibh and _dd_ibl and _dd_sh and _dd_sl:
                        _up = float(_dd_sh) > float(_dd_ibh)
                        _dn = float(_dd_sl) < float(_dd_ibl)
                        if _up and not _dn:
                            _dd_exp_dir = "UP"
                        elif _dn and not _up:
                            _dd_exp_dir = "DOWN"
                        # Both broken → no doctrine (allow both)
                    if _dd_exp_dir:
                        _dd_setup_dir = "UP" if direction.upper() == "LONG" else "DOWN"
                        if _dd_setup_dir != _dd_exp_dir:
                            # Counter-expansion → block UNLESS a halt-proof shows the
                            # trend has stalled (item-18 halt-proof: 2 closes back
                            # through the expansion level). Reference level = the IB
                            # edge that was broken (UP→ib_high, DOWN→ib_low).
                            _dd_proof = False
                            try:
                                from backend.v9.systems.day_direction import (
                                    halt_proof_met as _hp, gather_recent_closes as _grc,
                                    min_closes_required as _mcr,
                                )
                                _dd_level = float(_dd_ibh) if _dd_exp_dir == "UP" else float(_dd_ibl)
                                _dd_proof = _hp(
                                    expansion_dir=_dd_exp_dir, expansion_level=_dd_level,
                                    recent_closes=_grc(3), min_closes=_mcr(),
                                )
                            except Exception as _hp_err:
                                logger.debug("[Gateway] halt-proof check errored (stay blocked): %s", _hp_err)
                            if _dd_proof:
                                logger.warning(
                                    "[Gateway] day-direction doctrine: %s counter allowed — halt-proof met (%s expansion stalled)",
                                    direction, _dd_exp_dir,
                                )
                            else:
                                result["blocked_by"] = "day_direction_doctrine"
                                logger.info(
                                    "[Gateway] BLOCKED by day-direction doctrine: %s against %s expansion on %s (no halt-proof)",
                                    direction, _dd_exp_dir, _dd_dt,
                                )
                                return result
            except Exception as _ddd_err:
                logger.debug("[Gateway] day-direction doctrine errored (fail-open): %s", _ddd_err)

        # Item-4: structural stop resolver (STOP_RESOLVER_V1, default OFF).
        # Single choke point covering S2 + S4: re-derive the stop from a REAL
        # bar-extreme rung ladder within the ATR band, replacing a financed
        # (too-tight) or absurd stop. Runs BEFORE structural targets + R:R gate
        # so both see the corrected stop. Fail-safe: no rung fits the band, any
        # error, or missing bars → keep the original stop. Backtest evidence:
        # 31/86 stops were below the 0.5×ATR floor (BACKTEST_STOP_RESOLVER_ITEM4).
        # (CONFLUENCE_RI_ZLR is exempt: its stop is already structural + capped 7pt.)
        if (not _confluence_fixed) and os.getenv("STOP_RESOLVER_V1", "0").lower() in ("1", "true", "yes"):
            try:
                _sr_entry = setup.get("entry_price")
                _sr_stop = setup.get("stop")
                if _sr_entry and _sr_stop:
                    _sr_entry = float(_sr_entry)
                    _sr_dir = str(direction).upper()
                    from backend.v9.db.read import read_all as _sr_read
                    _sr_rows = _sr_read(
                        "SELECT high, low, close FROM v9_bars_5min_woodies "
                        "ORDER BY ts DESC LIMIT 12", {})
                    _sr_bars = [{"high": float(r["high"]), "low": float(r["low"]),
                                 "close": float(r["close"])} for r in _sr_rows][::-1]
                    if len(_sr_bars) >= 3:
                        _sr_trs, _sr_prev = [], None
                        for _b in _sr_bars[-14:]:
                            _sr_trs.append(_b["high"] - _b["low"] if _sr_prev is None
                                           else max(_b["high"] - _b["low"],
                                                    abs(_b["high"] - _sr_prev),
                                                    abs(_b["low"] - _sr_prev)))
                            _sr_prev = _b["close"]
                        _sr_atr = sum(_sr_trs) / len(_sr_trs) if _sr_trs else 7.0
                        # FIX-8 (incident 333, 16:40): early session ATR from 1-2 bars
                        # is too small → cap_risk rejects legitimate structural stops.
                        # Floor with yesterday's close ATR when < 14 bars available.
                        if os.getenv("EARLY_ATR_FLOOR_V1", "0").lower() in ("1", "true", "yes"):
                            if len(_sr_trs) < 14:
                                try:
                                    from datetime import datetime as _atr_dt
                                    from zoneinfo import ZoneInfo as _atr_ZI
                                    _atr_yest = (_atr_dt.now(_atr_ZI("America/Chicago")).date()
                                                 - __import__("datetime").timedelta(days=1)).isoformat()
                                    _yest_bars = _sr_read(
                                        "SELECT high, low, close FROM v9_bars_5min_woodies "
                                        "WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d "
                                        "ORDER BY ts", {"d": _atr_yest})
                                    if _yest_bars and len(_yest_bars) >= 14:
                                        _yb = [{"high": float(r["high"]), "low": float(r["low"]),
                                                "close": float(r["close"])} for r in _yest_bars]
                                        from backend.v9.shared.atr import atr_5min as _atr_fn
                                        _yest_atr = _atr_fn(_yb, 14)
                                        if _yest_atr and _yest_atr > _sr_atr:
                                            logger.info(
                                                "[Gateway] FIX-8 ATR floor: session ATR %.2f → %.2f "
                                                "(yesterday close, %d bars today)", _sr_atr, _yest_atr,
                                                len(_sr_trs))
                                            _sr_atr = _yest_atr
                                except Exception as _atr_err:
                                    logger.debug("[Gateway] FIX-8 ATR floor error (fail-open): %s", _atr_err)
                        if _sr_dir == "SHORT":
                            _sr_rungs = sorted({round(_b["high"], 2) for _b in _sr_bars
                                                if _b["high"] > _sr_entry})
                        else:
                            _sr_rungs = sorted({round(_b["low"], 2) for _b in _sr_bars
                                                if _b["low"] < _sr_entry}, reverse=True)
                        _sr_cls = str(setup.get("classification", "")).upper()
                        _sr_fam = "REV" if _sr_cls.startswith(
                            ("REACTIVE", "HFE", "GHOST", "FAMIR", "HNS", "DOUBLE", "INVERSE")) else "CONT"
                        if _sr_rungs:
                            from backend.v9.systems.stop_anchors.stop_resolver import resolve_stop as _sr_resolve
                            # 07-15 decision 5/6: pass the live day type so the
                            # resolver applies the rotation floor (0.8×ATR on
                            # Variation/Neutral — #372 died on a 0.55×ATR stop).
                            _sr_dt = None
                            try:
                                from backend.v9.services.trade_context import get_live_day_type as _sr_gldt
                                _sr_dt = _sr_gldt()
                            except Exception:
                                _sr_dt = None
                            _sr_res = _sr_resolve(
                                direction=_sr_dir, entry_price=_sr_entry,
                                rungs=_sr_rungs[:5],
                                rung_names=[f"r{i}" for i in range(len(_sr_rungs[:5]))],
                                atr_5m=_sr_atr, family=_sr_fam, day_type=_sr_dt)
                            # STOP_TABLE_V1 (default OFF): make the ATR band cap
                            # pattern×day_type aware. Tighten-only — never widens
                            # risk beyond the generic cap. Flag OFF, or pattern×
                            # day_type absent, → effective cap == generic cap →
                            # byte-identical to the generic resolver below.
                            _stbl_on = os.getenv("STOP_TABLE_V1", "0").lower() in ("1", "true", "yes")
                            _st_day_type = None
                            if _stbl_on:
                                try:
                                    _st_g1 = extract_g1_entry_context(cross_context)
                                    _st_day_type = _st_g1.get("day_type_at_entry")
                                except Exception:
                                    _st_day_type = None
                            _sr_eff_cap, _sr_tbl_entry = _stop_table_decide_cap(
                                enabled=_stbl_on,
                                table=_load_pattern_stop_table() if _stbl_on else {},
                                classification=_sr_cls, day_type=_st_day_type,
                                generic_cap_pts=_sr_res.cap_pts, atr_5m=_sr_atr)
                            if _stop_table_should_apply(
                                    in_band=_sr_res.in_band, rejected=_sr_res.rejected,
                                    risk_points=_sr_res.risk_points,
                                    effective_cap_pts=_sr_eff_cap,
                                    generic_cap_pts=_sr_res.cap_pts):
                                if _sr_tbl_entry is not None and _sr_eff_cap < _sr_res.cap_pts:
                                    logger.info(
                                        "[Gateway] STOP_TABLE_V1: %s×%s cap %.1f → %.1f "
                                        "(anchor_type=%s, advisory)",
                                        _sr_cls, _st_day_type, _sr_res.cap_pts,
                                        _sr_eff_cap, _sr_tbl_entry.get("anchor_type"))
                                logger.warning(
                                    "[Gateway] STOP_RESOLVER_V1: stop %.2f → %.2f "
                                    "(rung=%s, band [%.1f, %.1f], atr=%.1f)",
                                    float(_sr_stop), _sr_res.stop_price, _sr_res.rung_name,
                                    _sr_res.floor_pts, _sr_res.cap_pts, _sr_atr)
                                setup["stop"] = _sr_res.stop_price
                            elif (_stbl_on and _sr_tbl_entry is not None
                                    and _sr_res.in_band and not _sr_res.rejected):
                                # Resolved rung exceeds the tighter pattern×day_type
                                # cap → decline the reshape and KEEP the original
                                # detector stop (the resolver's existing reject →
                                # keep-original contract). Bounded by the generic
                                # cap; never widens vs today. SHADOW signal.
                                logger.warning(
                                    "[Gateway] STOP_TABLE_V1: %s×%s resolved risk %.1fpt "
                                    "> pattern cap %.1fpt → kept original stop %.2f "
                                    "(generic cap %.1f, atr=%.1f)",
                                    _sr_cls, _st_day_type, _sr_res.risk_points,
                                    _sr_eff_cap, float(_sr_stop), _sr_res.cap_pts, _sr_atr)
            except Exception as _sr_err:
                logger.warning("[Gateway] stop resolver errored (kept original stop): %s", _sr_err)

        # #68 Structural targets: override setup t1/t2/t3 with IB/POC/VA levels
        # when day-type style is "location" (Normal, Variation, NeuE, NeuC).
        # Flag-gated DAYTYPE_TARGETS_STRUCTURAL (default OFF). Fail-safe: on error
        # or missing levels → keeps original R-based targets.
        # (CONFLUENCE_RI_ZLR is exempt: ±4/±8 targets are definitional.)
        if (not _confluence_fixed) and os.getenv("DAYTYPE_TARGETS_STRUCTURAL", "0").lower() in ("1", "true", "yes"):
            # FIX-4 (incident 333): skip structural targets before IB lock.
            # Pre-lock IB = running session high/low → structural targets land
            # too close (C1 at 1.25pt, R:R 0.05).
            _st_ib_locked = True  # default: assume locked (fail-open)
            try:
                from datetime import datetime as _st_dt
                from zoneinfo import ZoneInfo as _st_ZI
                _st_ct = _st_dt.now(_st_ZI("America/Chicago"))
                _st_min = (_st_ct.hour * 60 + _st_ct.minute) - (8 * 60 + 30)
                if _st_min < 60:
                    _st_ib_locked = False
            except Exception:
                pass  # fail-open on TZ error
            if not _st_ib_locked:
                logger.info("[Gateway] structural targets SKIPPED: IB not locked")
            else:
                try:
                    from backend.v9.systems.structural_targets import resolve_structural_targets
                    _st_g1 = extract_g1_entry_context(cross_context)
                    _st_tpo = (cross_context.get("tpo_system") if isinstance(cross_context, dict) else None) or {}
                    _st_bars = None
                    try:
                        _dtm = self._system_registry.get("day_type_machine")
                        _st_bars = getattr(_dtm, "_opening_gate_bars", None) or []
                    except Exception:
                        pass
                    from backend.v9.systems.daytype_position_gate import _pattern_family as _pf
                    _st_pat = resolve_pattern_id(setup, _st_g1) or ""
                    _st = resolve_structural_targets(
                        day_type=_st_g1.get("day_type_at_entry"),
                        direction=direction,
                        entry_price=setup.get("entry_price", 0.0),
                        stop_price=setup.get("stop", 0.0),
                        tpo_ctx=_st_tpo,
                        bars=_st_bars,
                        pattern_family=_pf(_st_pat),
                    )
                    if _st is not None:
                        _old_t1 = setup.get("t1")
                        _old_t2 = setup.get("t2")
                        if _st.get("t1_price") is not None:
                            setup["t1"] = _st["t1_price"]
                        if _st.get("t2_price") is not None:
                            setup["t2"] = _st["t2_price"]
                        if _st.get("t3_price") is not None:
                            setup["t3"] = _st["t3_price"]
                        logger.info(
                            "[Gateway] #68 structural targets: %s %s → C1=%.2f C2=%s C3=%s (was t1=%s t2=%s)",
                            direction, _st.get("day_type"),
                            _st.get("t1_price", 0),
                            _st.get("t2_price"), _st.get("t3_price"),
                            _old_t1, _old_t2,
                        )
                except Exception as _st_err:
                    logger.warning("[Gateway] structural targets errored (fail-safe): %s", _st_err)

        # TP-audit pattern T1 overrides (Michael ruling 2026-07-10):
        # Fixed-point T1 per pattern×day_type from MFE p25-p50 analysis.
        # Overrides R-based T1 when a matching entry exists in targets.yaml.
        # T2 = entry ± 2×pts, T3 = entry ± 3×pts (runner, subject to TP-1 clamp).
        try:
            _pt_cls = str(setup.get("classification", "")).upper()
            _pt_g1 = extract_g1_entry_context(cross_context)
            _pt_dt = _pt_g1.get("day_type_at_entry")
            # (CONFLUENCE_RI_ZLR is exempt: a future targets.yaml row must not
            # silently rewrite the definitional ±4/±8 ladder.)
            if _pt_cls and _pt_dt and not _confluence_fixed:
                from backend.v9.config_loader import load_pattern_t1_points
                _pt_overrides = load_pattern_t1_points()
                _pt_pts = (_pt_overrides.get(_pt_cls) or {}).get(_pt_dt)
                if _pt_pts is not None and _pt_pts > 0:
                    _pt_entry = float(setup.get("entry_price", 0))
                    _pt_sign = 1.0 if str(direction).upper() == "LONG" else -1.0
                    _pt_old_t1 = setup.get("t1")
                    setup["t1"] = round(_pt_entry + _pt_sign * _pt_pts, 2)
                    setup["t2"] = round(_pt_entry + _pt_sign * 2 * _pt_pts, 2)
                    setup["t3"] = round(_pt_entry + _pt_sign * 3 * _pt_pts, 2)
                    logger.info(
                        "[Gateway] PATTERN_T1_OVERRIDE: %s×%s → T1=%.2f (%.1fpt) was=%.2f",
                        _pt_cls, _pt_dt, setup["t1"], _pt_pts, _pt_old_t1 or 0,
                    )
        except Exception as _pt_err:
            logger.warning("[Gateway] pattern T1 override errored (fail-safe): %s", _pt_err)

        # Item-22: target zones (TARGET_ZONES_V1, default OFF). Refine C2/C3
        # (t2/t3) to level-confluence ZONES beyond T1 — real shelves (IB/POC/VA +
        # prior-day + swings), not R-multiples — so the runner targets where price
        # actually reacts. Runs before the I-61 guard (which then validates the
        # zone targets). Fail-safe: no zone / error → keeps the structural targets.
        # (CONFLUENCE_RI_ZLR is exempt: ±4/±8 targets are definitional.)
        if (not _confluence_fixed) and os.getenv("TARGET_ZONES_V1", "0").lower() in ("1", "true", "yes"):
            try:
                _tz_entry = setup.get("entry_price")
                _tz_t1 = setup.get("t1")
                if _tz_entry and _tz_t1:
                    from backend.v9.systems.target_zones import (
                        cluster_levels as _tz_cl, select_target_zones as _tz_sel,
                        zone_tol_pts as _tz_tol,
                    )
                    _tz_tpo = (cross_context.get("tpo_system") if isinstance(cross_context, dict) else None) or {}
                    _tz_levels = []
                    for _k, _lbl in (("ib_high", "ibh"), ("ib_low", "ibl"),
                                     ("poc", "poc"), ("vah", "vah"), ("val", "val")):
                        _v = _tz_tpo.get(_k)
                        if _v:
                            _tz_levels.append((float(_v), _lbl))
                    try:
                        from backend.v9.db.read import read_all as _tz_read
                        _pr = _tz_read(
                            "SELECT poc_price, vah_price, val_price, range_high, range_low "
                            "FROM v9_tpo_sessions WHERE session_type = 'CASH' "
                            "ORDER BY id DESC LIMIT 2", {})
                        for _row in (_pr[1:2] if len(_pr) > 1 else []):
                            for _c, _lbl in (("poc_price", "pd_poc"), ("vah_price", "pd_vah"),
                                             ("val_price", "pd_val"), ("range_high", "pd_h"),
                                             ("range_low", "pd_l")):
                                if _row.get(_c):
                                    _tz_levels.append((float(_row[_c]), _lbl))
                        _bz = _tz_read("SELECT high, low FROM v9_bars_5min_woodies "
                                       "ORDER BY ts DESC LIMIT 20", {})
                        for _b in _bz:
                            _tz_levels.append((float(_b["high"]), "swing_h"))
                            _tz_levels.append((float(_b["low"]), "swing_l"))
                    except Exception:
                        pass
                    if _tz_levels:
                        _zones = _tz_cl(_tz_levels, tol_pts=_tz_tol(7.0))
                        _sel = _tz_sel(direction=str(direction).upper(),
                                       entry_price=float(_tz_entry), t1_price=float(_tz_t1),
                                       zones=_zones, min_strength=2)
                        if _sel.get("c2") is not None:
                            logger.warning("[Gateway] TARGET_ZONES_V1: t2 %s → %.2f (shelf strength %s)",
                                           setup.get("t2"), _sel["c2"],
                                           getattr(_sel.get("c2_zone"), "strength", None))
                            setup["t2"] = _sel["c2"]
                        if _sel.get("c3") is not None:
                            setup["t3"] = _sel["c3"]
            except Exception as _tz_err:
                logger.warning("[Gateway] target zones errored (kept targets): %s", _tz_err)

        # I-61 (Michael 2026-07-02 ~20:1x, trades 279/280): FINAL target-side guard for
        # EVERY setup (S2 has no A7 validator — a LONG went to Sierra with t2/t3 BELOW
        # entry and disintegrated instantly). Any target on the wrong side of entry is
        # dropped to None (honest) with a loud log. Applies after the structural
        # override so it guards both R-based and resolver-produced ladders.
        _tg_entry = setup.get("entry_price")
        if _tg_entry:
            _tg_dir = str(direction).upper()
            for _tk in ("t1", "t2", "t3"):
                _tv = setup.get(_tk)
                if _tv is None:
                    continue
                try:
                    _wrong = (float(_tv) <= float(_tg_entry)) if _tg_dir == "LONG" \
                        else (float(_tv) >= float(_tg_entry))
                except (TypeError, ValueError):
                    continue
                if _wrong:
                    logger.warning(
                        "[Gateway] I-61 target-side guard: %s %s=%.2f on wrong side of entry=%.2f → None",
                        _tg_dir, _tk, float(_tv), float(_tg_entry),
                    )
                    setup[_tk] = None

        # TP-1 (Michael 2026-07-08, trade 310): targets live inside the day
        # structure — clamp beyond-IB targets to the IB edge unless the day
        # type travels (Neutral_*/Trend_*). Flag TARGET_STRUCTURE_CLAMP_V1
        # (default OFF). Fail-open: missing IB/day_type → untouched.
        # (CONFLUENCE_RI_ZLR is exempt: ±4/±8 targets are definitional.)
        if (not _confluence_fixed) and os.getenv("TARGET_STRUCTURE_CLAMP_V1", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.systems.target_structure_clamp import clamp_targets_to_ib
                _tc_g1 = extract_g1_entry_context(cross_context)
                _tc_tpo = (cross_context.get("tpo_system") if isinstance(cross_context, dict) else None) or {}
                # FIX-2: compute ib_locked (60 min after 08:30 CT = 09:30 CT)
                from datetime import datetime as _tc_dt
                from zoneinfo import ZoneInfo as _tc_ZI
                _tc_ct = _tc_dt.now(_tc_ZI("America/Chicago"))
                _tc_min_since_open = (_tc_ct.hour * 60 + _tc_ct.minute) - (8 * 60 + 30)
                _tc_ib_locked = _tc_min_since_open >= 60

                setup, _tc_notes = clamp_targets_to_ib(
                    setup,
                    day_type=_tc_g1.get("day_type_at_entry"),
                    ib_high=_tc_tpo.get("ib_high"),
                    ib_low=_tc_tpo.get("ib_low"),
                    ib_locked=_tc_ib_locked,
                )
                if _tc_notes:
                    result["target_clamp"] = _tc_notes
            except Exception as _tc_err:  # fail-open — never block on a bug
                logger.warning("[Gateway] target-clamp errored (fail-open): %s", _tc_err)

        # FIX-16 (TARGET_REALISM_V1, default OFF — Michael ruling 2026-07-10,
        # trade 350): T1 must be REALISTIC to fill. When every structural level
        # sits behind the entry, the R-fallback can put T1 beyond the session
        # extreme (350: T1=7617.5 vs day-high 7614 → missed by 2 ticks). Final
        # word on t1 after all producers: ceiling = session extreme + today's
        # average breakout step. Tighten-only; honest skip when bars missing.
        # (CONFLUENCE_RI_ZLR is exempt: ±4/±8 targets are definitional.)
        if (not _confluence_fixed) and os.getenv("TARGET_REALISM_V1", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.systems.structural_targets import realism_ceiling as _rc
                _rc_entry = setup.get("entry_price")
                _rc_t1 = setup.get("t1")
                if _rc_entry and _rc_t1 is not None:
                    _rc_dir = str(direction).upper()
                    _ceil = _rc(_rc_dir, float(_rc_entry))
                    _too_far = (_ceil is not None) and (
                        float(_rc_t1) > _ceil if _rc_dir == "LONG" else float(_rc_t1) < _ceil)
                    if _too_far:
                        # keep t1 strictly beyond entry (≥2 ticks) — never cross sides
                        _floor2t = (float(_rc_entry) + 0.5) if _rc_dir == "LONG" \
                            else (float(_rc_entry) - 0.5)
                        _new_t1 = max(_ceil, _floor2t) if _rc_dir == "LONG" \
                            else min(_ceil, _floor2t)
                        logger.warning(
                            "[Gateway] TARGET_REALISM_V1: t1 %.2f → %.2f (%s ceiling from "
                            "session extreme + avg breakout step)",
                            float(_rc_t1), _new_t1, _rc_dir)
                        setup["t1"] = _new_t1
                        # 07-15 Michael ruling (decision 2/6): the R:R gate judges
                        # the ORIGINAL structural intent, not the realism-capped
                        # order price — two conservatisms must not double-count
                        # (07-14: 14 morning fires blocked at R:R 0.2-0.94).
                        setup["t1_pre_realism"] = float(_rc_t1)
                        result["target_realism"] = {"t1_was": float(_rc_t1), "t1": _new_t1}
            except Exception as _rc_err:  # fail-open
                logger.warning("[Gateway] target-realism errored (fail-open): %s", _rc_err)

        # Ladder-collapse guard (trade 337: t1=t2=t3=7583.75).
        # When target producers converge on a single level, the ladder degenerates
        # into a point — no runner differentiation. Fix: deduplicate by nudging
        # t2/t3 farther by 1-2 ticks so the bracket has distinct levels.
        _lc_entry = setup.get("entry_price")
        _lc_t1 = setup.get("t1")
        _lc_t2 = setup.get("t2")
        _lc_t3 = setup.get("t3")
        _lc_dir = str(direction).upper()
        _lc_sign = 1.0 if _lc_dir == "LONG" else -1.0
        if _lc_entry and _lc_t1 is not None:
            if _lc_t2 is not None and abs(float(_lc_t2) - float(_lc_t1)) < 0.25:
                setup["t2"] = round(float(_lc_t1) + _lc_sign * 0.5, 2)  # +2 ticks
                logger.info("[Gateway] ladder-dedup: t2=%.2f collapsed to t1=%.2f → nudged to %.2f",
                            float(_lc_t2), float(_lc_t1), setup["t2"])
            if _lc_t3 is not None and (
                abs(float(_lc_t3) - float(_lc_t1)) < 0.25 or
                (setup.get("t2") is not None and abs(float(_lc_t3) - float(setup["t2"])) < 0.25)
            ):
                _lc_base = float(setup.get("t2", _lc_t1))
                setup["t3"] = round(_lc_base + _lc_sign * 0.5, 2)  # +2 ticks beyond t2
                logger.info("[Gateway] ladder-dedup: t3=%.2f collapsed → nudged to %.2f",
                            float(_lc_t3), setup["t3"])

        # Item-6: entry confirm (S4_ENTRY_CONFIRM_V1, default OFF). Require the
        # most recent (signal) bar to close in the trade direction before firing
        # — "עוד ודאות בכניסה". Fail-open on missing bars / error.
        if os.getenv("S4_ENTRY_CONFIRM_V1", "0").lower() in ("1", "true", "yes"):
            try:
                from backend.v9.db.read import read_all as _ec_read
                from backend.v9.systems.entry_confirm import entry_confirmed as _ec
                # Michael ruling 2026-07-08: the confirm test is relative to the
                # average candle — a counter-close within frac×ATR(14) is noise.
                _ec_rows = _ec_read("SELECT open, close, high, low FROM v9_bars_5min_woodies "
                                    "ORDER BY ts DESC LIMIT 15", {})
                if _ec_rows:
                    _ec_tol = 0.0
                    _ranges = [float(r["high"]) - float(r["low"])
                               for r in _ec_rows[1:15]
                               if r.get("high") is not None and r.get("low") is not None]
                    if _ranges:
                        _ec_frac = float(os.getenv("ENTRY_CONFIRM_TOL_ATR_FRAC", "0.10") or 0)
                        _ec_min_pts = float(os.getenv("ENTRY_CONFIRM_TOL_MIN_PTS", "0.5") or 0)
                        _ec_tol = max(_ec_frac * (sum(_ranges) / len(_ranges)), _ec_min_pts)
                    _ec_bar = {"o": float(_ec_rows[0]["open"]), "c": float(_ec_rows[0]["close"])}
                    _ec_ok, _ec_reason = _ec(direction=str(direction).upper(), bars=[_ec_bar],
                                             tol_points=_ec_tol)
                    if not _ec_ok:
                        result["blocked_by"] = "entry_not_confirmed"
                        logger.info("[Gateway] BLOCKED by entry-confirm: %s", _ec_reason)
                        return result
            except Exception as _ec_err:
                logger.warning("[Gateway] entry-confirm errored (fail-open): %s", _ec_err)

        # Item-3: R:R entry gate — block if T1 closer than the stop (net-negative R:R)
        # FIX-1 (incident 333): signed distance, not abs(). A LONG with t1 < entry
        # had positive abs-distance but was on the WRONG SIDE → must block.
        if os.getenv("RR_ENTRY_GATE_V1", "0").lower() in ("1", "true", "yes"):
            # 07-15 Michael ruling (decision 2/6, "מאשר המלצה"): judge the
            # PRE-realism T1 (structural intent). The realism cap still applies
            # to the actual order; it must not also fail the R:R test.
            _rr_t1 = setup.get("t1_pre_realism", setup.get("t1"))
            _rr_stop = setup.get("stop")
            _rr_entry = setup.get("entry_price")
            if _rr_t1 is not None and _rr_stop is not None and _rr_entry is not None:
                try:
                    _rr_dir = str(direction).upper()
                    _rr_e = float(_rr_entry)
                    # Signed T1 distance: positive = correct side, negative = wrong side
                    if _rr_dir == "LONG":
                        _t1_dist = float(_rr_t1) - _rr_e
                    else:
                        _t1_dist = _rr_e - float(_rr_t1)
                    _stop_dist = abs(_rr_e - float(_rr_stop))

                    if _t1_dist <= 0:
                        result["blocked_by"] = "t1_wrong_side"
                        logger.warning(
                            "[Gateway] BLOCKED t1_wrong_side: %s t1=%.2f entry=%.2f "
                            "(t1 on wrong side of entry)",
                            _rr_dir, float(_rr_t1), _rr_e,
                        )
                        return result
                    # CONFLUENCE_RI_ZLR per-pattern R:R (spec §2/§5.4): the generic
                    # T1-only test (4pt vs a ≤7pt stop → 0.57..0.86 < 1.0) would
                    # dead-letter the pattern exactly on the Trend day-types where
                    # it is allowed. Judge the DEFINITIONAL position average
                    # (C1+C2)/2 = 6pt against a dedicated minimum CONFLUENCE_RR_MIN
                    # (default 0.85 — worst-case capped stop 7.0 → 6/7≈0.857
                    # passes; a wider stop is impossible by construction). The
                    # generic path below is untouched for every other pattern.
                    if _confluence_fixed:
                        _rr_t2c = setup.get("t2")
                        if _rr_t2c is not None:
                            _t2_dist = (float(_rr_t2c) - _rr_e) if _rr_dir == "LONG" \
                                else (_rr_e - float(_rr_t2c))
                        else:
                            _t2_dist = _t1_dist
                        _avg_dist = (_t1_dist + _t2_dist) / 2.0
                        try:
                            _conf_rr_min = float(
                                os.getenv("CONFLUENCE_RR_MIN", "0.85") or "0.85")
                        except (TypeError, ValueError):
                            _conf_rr_min = 0.85
                        if _stop_dist > 0 and _avg_dist < _stop_dist * _conf_rr_min:
                            result["blocked_by"] = "rr_entry_gate"
                            logger.info(
                                "[Gateway] BLOCKED by R:R gate (confluence avg): "
                                "avg_dist=%.2f < stop_dist=%.2f × min=%.2f",
                                _avg_dist, _stop_dist, _conf_rr_min,
                            )
                            return result
                    # 07-15 evening (Michael: "תיקון שיסדר את הבעיה כדי שהמערכת
                    # תסחר היום"): graded R:R minimum on ROTATION days. The
                    # 0.8×ATR stop floor (decision 5/6) × nearest-shelf T1 made
                    # T1-only R:R ~always <1 on a narrow rotation day — blocked
                    # the winning 18:15 ZLR SHORT (R:R 0.65, T0+T1 both hit).
                    # With the T0=3.5 fast-take ladder, T1-only R:R is double-
                    # conservative. RR_MIN_ROTATION (e.g. "0.65") lowers the
                    # required ratio ONLY on rotation day-types; unset → 1.0
                    # everywhere (unchanged). Trend days always 1.0. Fail-
                    # conservative: any error → 1.0.
                    _rr_min = 1.0
                    _rr_min_env = os.getenv("RR_MIN_ROTATION", "").strip()
                    if _rr_min_env:
                        try:
                            from backend.v9.services.trade_context import (
                                get_live_day_type as _rr_dt_fn,
                            )
                            _rr_dt = str(_rr_dt_fn() or "")
                            _rr_relief = _rr_dt.startswith(
                                ("Variation", "Normal_Variation", "Normal", "Neutral")
                            )
                            # 07-16 Michael ("מאשר — תקן עכשיו"): relief ALSO
                            # while the label is UNCLASSIFIED (""), but only in
                            # the post-opening window (see helper). Trend labels
                            # keep 1.0; error paths keep 1.0 (except below).
                            if not _rr_relief and _rr_dt == "":
                                _rr_relief = self._rr_unclassified_relief_window()
                            if _rr_relief:
                                _rr_min = max(0.1, min(float(_rr_min_env), 1.0))
                        except Exception:
                            _rr_min = 1.0
                    if (not _confluence_fixed) and _stop_dist > 0 and _t1_dist < _stop_dist * _rr_min:
                        result["blocked_by"] = "rr_entry_gate"
                        logger.info(
                            "[Gateway] BLOCKED by R:R gate: T1_dist=%.2f < stop_dist=%.2f"
                            " × min=%.2f (R:R=%.2f)",
                            _t1_dist, _stop_dist, _rr_min, _t1_dist / _stop_dist,
                        )
                        return result
                except (TypeError, ValueError):
                    pass  # fail-open

        # N3 (ZONE_LIMIT_ENTRY_V1, default OFF) — no-late-entry gate.
        # Michael ruling 2026-07-17: "לא תהיה כניסה באף תבנית בשלב מאוחר מדי"
        # — no pattern may enter too late after its signal. Two lateness axes:
        #   (a) ADVERSE price drift (= chasing): live price beyond entry by
        #       more than ZONE_LIMIT_MAX_DRIFT_PT in the trade direction
        #       (LONG: live > entry + max; SHORT: live < entry − max).
        #       FAVORABLE drift (price came back toward a better fill) passes.
        #   (b) signal age: now − signal bar ts > ZONE_LIMIT_MAX_AGE_SEC,
        #       ONLY when the setup carries a parseable timestamp (bar_ts /
        #       metadata.bar_ts / metadata.signal_ts). Today only
        #       CONFLUENCE_RI_ZLR setups attach bar_ts — S2/S4 producers do
        #       not — so (b) is dormant for S2/S4 until they attach one; (a)
        #       covers them meanwhile. No exemptions: CONFLUENCE_RI_ZLR is
        #       gated like any other pattern.
        # Live price comes from the SAME canonical source as
        # GET /api/v9/live_price (bridge in-memory cache → DLL
        # live_price.json) via price_routes.get_live_price_snapshot — no
        # second price reader. Missing/stale price or missing timestamp →
        # fail-OPEN (Source-of-Truth Rule 1: honest missing beats synthetic;
        # a safety gate must not manufacture blocks from absent data).
        # NOTE: this gate is the BLOCKING half of N3 only. The resting-limit
        # entry half (docs/handoff/N3_ZONE_LIMIT_ENTRY_SPEC_2026-07-17.md)
        # needs the DLL limit-PLACE capability check + a full sim cycle and
        # stays with cc-imac per that spec.
        if os.getenv("ZONE_LIMIT_ENTRY_V1", "0").lower() in ("1", "true", "yes"):
            try:
                _zl_entry = setup.get("entry_price")
                _zl_dir = str(direction).upper()
                if _zl_entry is not None and _zl_dir in ("LONG", "SHORT"):
                    try:
                        _zl_max_drift = float(os.getenv("ZONE_LIMIT_MAX_DRIFT_PT", "2.0"))
                    except (TypeError, ValueError):
                        _zl_max_drift = 2.0
                    try:
                        _zl_max_age = float(os.getenv("ZONE_LIMIT_MAX_AGE_SEC", "180"))
                    except (TypeError, ValueError):
                        _zl_max_age = 180.0
                    # (a) adverse price drift — chasing the move
                    from backend.v9.api.v9.price_routes import (
                        get_live_price_snapshot as _zl_price_fn,
                    )
                    _zl_snap = _zl_price_fn()
                    if (_zl_snap is not None and _zl_snap.get("price") is not None
                            and _zl_max_drift > 0):
                        _zl_px = float(_zl_snap["price"])
                        _zl_e = float(_zl_entry)
                        _zl_adverse = (_zl_px - _zl_e) if _zl_dir == "LONG" else (_zl_e - _zl_px)
                        if _zl_adverse > _zl_max_drift:
                            result["blocked_by"] = "zone_limit_late_entry"
                            logger.info(
                                "[Gateway] BLOCKED by zone-limit late-entry (drift): %s "
                                "entry=%.2f live=%.2f adverse_drift=%.2fpt > max=%.2fpt "
                                "(price_src=%s age=%.1fs)",
                                _zl_dir, _zl_e, _zl_px, _zl_adverse, _zl_max_drift,
                                _zl_snap.get("source"),
                                float(_zl_snap.get("age_sec") or 0.0),
                            )
                            return result
                    # (b) signal age — only when the setup carries a timestamp
                    _zl_raw_ts = (setup.get("bar_ts")
                                  or (setup.get("metadata") or {}).get("bar_ts")
                                  or (setup.get("metadata") or {}).get("signal_ts"))
                    _zl_sig_epoch = _zone_limit_parse_ts(_zl_raw_ts)
                    if _zl_sig_epoch is not None and _zl_max_age > 0:
                        import time as _zl_time
                        _zl_age = _zl_time.time() - _zl_sig_epoch
                        if _zl_age > _zl_max_age:
                            result["blocked_by"] = "zone_limit_late_entry"
                            logger.info(
                                "[Gateway] BLOCKED by zone-limit late-entry (age): %s "
                                "entry=%s signal_age=%.0fs > max=%.0fs (bar_ts=%s)",
                                _zl_dir, _zl_entry, _zl_age, _zl_max_age, _zl_raw_ts,
                            )
                            return result
            except Exception as _zl_err:
                logger.warning("[Gateway] zone-limit gate errored (fail-open): %s", _zl_err)

        # Item-19: daily-loss / consecutive-loss STOP-DAY halt (Michael approved
        # 2026-07-03: halt at −$450). BLOCK-ONLY safety — it can only stop
        # trading, never add risk. Enforced in ALL modes when RISK_HALT_V1=1 so
        # the 5-demo-day validation window is a real test (the legacy
        # passes_strict_checks only fires in mode="live" → the 06-29 guards-bus
        # was inert in demo). Uses the gateway's own running counters
        # (_daily_pnl updated on every close). Default OFF → ZERO effect until
        # Michael starts the validation window. Number change = Michael sign-off.
        if os.getenv("RISK_HALT_V1", "0").lower() in ("1", "true", "yes"):
            try:
                _dl_cap = float(os.getenv("RISK_DAILY_LOSS_CAP", "450"))
            except (TypeError, ValueError):
                _dl_cap = 450.0
            if _dl_cap > 0 and self._daily_pnl <= -_dl_cap:
                result["blocked_by"] = "daily_loss_halt"
                logger.warning(
                    "[Gateway] BLOCKED by daily-loss halt: pnl=$%.2f <= -$%.0f (STOP DAY)",
                    self._daily_pnl, _dl_cap,
                )
                # IDEA-2 (Michael 07-13): the halt tripping = a phone-worthy moment.
                try:
                    from backend.v9.services.phone_alert import push as _phone_push
                    _phone_push("daily_loss_halt", "🛑 MEMS26: עצירת-יום",
                                f"P&L ${self._daily_pnl:.2f} חצה את התקרה -${_dl_cap:.0f} — אין כניסות חדשות היום.",
                                priority=1)
                except Exception:
                    pass
                return result
            # Consecutive-loss STOP-DAY — only bites when a limit is explicitly
            # set (default 0 = off; Michael has not fixed this number yet).
            try:
                _cl_lim = int(os.getenv("RISK_CONSECUTIVE_LOSS_LIMIT", "0"))
            except (TypeError, ValueError):
                _cl_lim = 0
            if _cl_lim > 0 and self._consecutive_losses >= _cl_lim:
                result["blocked_by"] = "consecutive_loss_halt"
                logger.warning(
                    "[Gateway] BLOCKED by consecutive-loss halt: %d losses >= %d (STOP DAY)",
                    self._consecutive_losses, _cl_lim,
                )
                return result

        # Item-11 Phase 3: S4 risk-cap gate (SIZING_CONSOLIDATION_V1).
        # Under the consolidation flag, risk-cap rejects that were previously
        # embedded as silent sizing="reject" inside the S4 detector now surface
        # here as explicit blocked_by — no silent failures. The detector passes
        # the rejection reason in setup.metadata.s4_risk_cap_block.
        _s4_rcb = (setup.get("metadata") or {}).get("s4_risk_cap_block")
        if _s4_rcb:
            # P5 (2026-07-16): distinguish the per-pattern loss-breaker from the
            # risk-POINTS cap. Both used to surface as "s4_risk_cap", which made
            # the 07-15 evening blocks (pattern_loss_breaker:ZLR:2>=2) look like a
            # sizing/points-cap problem. The reason string is kind-prefixed.
            _rcb_kind = str(_s4_rcb).split(":", 1)[0]
            result["blocked_by"] = (
                "pattern_loss_breaker" if _rcb_kind == "pattern_loss_breaker"
                else "s4_risk_cap")
            logger.warning("[Gateway] BLOCKED by S4 %s: %s", result["blocked_by"], _s4_rcb)
            return result

        # D-088: cluster_guard blocks DEMO/LIVE only — SHADOW still records (3-Mode §8)
        cluster_blocked = self.cluster_guard.is_blocked()
        if not cluster_blocked:
            # ζ.A5: count only setups that passed cooldown/SSV/chop (GW-02)
            self.cluster_guard.record_attempt()

        # I-60: register for dedup ONLY now — every hard gate has passed, this fire
        # WILL be recorded. A blocked fire never poisons the dedup window.
        if os.getenv("DEDUP_FIRE_GUARD", "0").lower() in ("1", "true", "yes"):
            import time as _dd_time2
            self._recent_fires.append({
                "ts": _dd_time2.time(), "system": system_id, "direction": direction,
                "pattern": (setup.get("classification") or (setup.get("metadata") or {}).get("pattern")),
                "entry": setup.get("entry_price"),
            })

        # SHADOW: always log when past hard gates, unlimited slots
        shadow_trade = self._execute_shadow(setup, system_id, cross_context)
        self.shadow_trades.append(shadow_trade)
        if len(self.shadow_trades) > 500:
            self.shadow_trades = self.shadow_trades[-300:]
        result["shadow"] = shadow_trade["trade_id"]

        # ── CONFLUENCE_RI_ZLR V1: shadow-only by default; LIVE by Michael ruling ──
        # Research verdict (spec §0/§3.3): n=5, +4-first hit-rate 40% — small sample.
        # Original build (07-17 morning) shipped a REFUSING stub pending sign-off.
        # **Michael sign-off 2026-07-17 ~11:15 IL (explicit, in writing): "לגבי
        # התבנית החדשה מאושר להפעיל על לייב"** → CONFLUENCE_RI_ZLR_LIVE=1 now
        # routes to the NORMAL demo/live slot path below (same limits/halts/slots
        # as every pattern; 2-contract sizing enforced at effective_contracts;
        # stop capped 7pt at build). Risk per trade ≤ 2c × 7pt × $5 = $70.
        # With the LIVE flag unset/0 the pattern remains SHADOW-ONLY (returns
        # here, never reaches demo/live) — that is still the code default.
        if _confluence_fixed:
            if os.getenv("CONFLUENCE_RI_ZLR_LIVE", "0").lower() not in ("1", "true", "yes"):
                result["confluence_shadow_only"] = True
                return result
            logger.info(
                "[Gateway] CONFLUENCE_RI_ZLR routing to demo/live per Michael "
                "ruling 2026-07-17 (CONFLUENCE_RI_ZLR_LIVE=1); 2c, stop<=7pt.")

        # P3: Opposite-pattern exit (OPPOSITE_EXIT_V1, default OFF)
        # When a trade is active and ≥2 signals fire in the opposite direction
        # → close the active trade (don't wait for stop/target).
        if os.getenv("OPPOSITE_EXIT_V1", "0").lower() in ("1", "true", "yes"):
            if self.demo_slot is not None:
                _active_dir = self.demo_slot.get("direction", "").upper()
                _setup_dir = direction.upper()
                if _active_dir and _setup_dir != _active_dir:
                    # Track per-bar: reset counter when bar changes
                    _bar_ts = str(setup.get("bar_ts", ""))
                    if _bar_ts != self._opposite_bar_ts:
                        self._opposite_count = 0
                        self._opposite_bar_ts = _bar_ts
                    self._opposite_count += 1
                    _threshold = int(os.getenv("OPPOSITE_EXIT_THRESHOLD", "2"))
                    if self._opposite_count >= _threshold:
                        _active_id = self.demo_slot.get("trade_id")
                        logger.info(
                            "[Gateway] OPPOSITE_2X: %d opposite signals (%s vs active %s) → closing trade %s",
                            self._opposite_count, _setup_dir, _active_dir, _active_id,
                        )
                        # Close the active trade via TradeManager
                        if self._trade_manager and _active_id:
                            try:
                                self._trade_manager.close_trade(
                                    _active_id, reason="OPPOSITE_2X",
                                    exit_price=setup.get("entry_price"),
                                )
                            except Exception as _opp_err:
                                logger.warning("[Gateway] OPPOSITE_2X close failed: %s", _opp_err)
                        # Free the slot
                        self.on_trade_close({
                            "trade_id": _active_id, "mode": "demo",
                            "outcome": "OPPOSITE_2X", "direction": _active_dir,
                        })
                        self._opposite_count = 0

        if cluster_blocked:
            result["blocked_by"] = "cluster_guard"
            logger.info(
                "[Gateway] SHADOW recorded; DEMO/LIVE blocked by cluster guard D-037"
            )
            return result

        # DEMO/LIVE: D-094 R:R selection or first-wins
        # Self-heal (Michael 2026-07-02: "שתמיד יהיה ניקוי של המערכת"): if the demo
        # slot points at a trade that is already CLOSED/CANCELLED in the DB (a close
        # path that bypassed on_trade_close — e.g. Sierra-driven FillPoller close,
        # I-57 trades 271/272), free it HERE so a stuck slot can never block trading.
        self._selfheal_demo_slot()

        if self._rr_selection_enabled:
            # Buffer candidate for bar-close flush (slot NOT filled yet)
            candidate = {
                "setup": setup,
                "system_id": system_id,
                "cross_context": cross_context,
                "result_ref": result,
            }
            if self._is_demo_enabled(system_id) or self._is_live_enabled(system_id):
                if self.demo_slot is None or self.live_slot is None:
                    self._slot_candidates.append(candidate)
                    logger.info(
                        "[Gateway] D-094 buffered: system=%d classification=%s (awaiting bar-close flush)",
                        system_id, setup.get("classification", "?"),
                    )
                else:
                    logger.info("[Gateway] D-094: all slots occupied, skipping system %d", system_id)
        else:
            # Original first-wins logic (flag OFF)
            # DEMO: single slot
            if self._is_demo_enabled(system_id):
                if self.demo_slot is None:
                    demo_trade = self._execute_demo(setup, system_id, cross_context)
                    self.demo_slot = demo_trade
                    result["demo"] = demo_trade["trade_id"]
                else:
                    logger.info("[Gateway] DEMO slot occupied, skipping system %d setup", system_id)

            # LIVE: single slot + strict risk checks
            if self._is_live_enabled(system_id):
                if self.live_slot is None and passes_strict_checks(setup, "live", self):
                    live_trade = self._execute_live(setup, system_id, cross_context)
                    self.live_slot = live_trade
                    result["live"] = live_trade["trade_id"]
                elif self.live_slot is not None:
                    logger.info("[Gateway] LIVE slot occupied, skipping system %d setup", system_id)

        return result

    async def on_bar_close(self, event=None) -> None:
        """D-094: Flush buffered candidates at bar close — select winner by R:R.

        Called by BarRouter on new 5min bar (= previous bar closed).
        Only active when RR_FIRE_SELECTION flag is ON.
        """
        if not self._rr_selection_enabled or not self._slot_candidates:
            return

        from backend.v9.gateway.rr_score import compute_rr_score

        candidates = self._slot_candidates
        self._slot_candidates = []

        # Score each candidate
        scored = []
        for c in candidates:
            rr = compute_rr_score(c["setup"])
            confidence = c["setup"].get("confidence", 0.0)
            system_id = c["system_id"]
            scored.append((rr or 0.0, confidence, -system_id, c))

        # Sort: highest R:R → highest confidence → lowest system_id (tie-break)
        scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

        winner = scored[0][3] if scored else None

        if winner:
            setup = winner["setup"]
            system_id = winner["system_id"]
            cross_context = winner["cross_context"]

            # DEMO slot fill
            if self._is_demo_enabled(system_id) and self.demo_slot is None:
                demo_trade = self._execute_demo(setup, system_id, cross_context)
                self.demo_slot = demo_trade
                logger.info(
                    "[Gateway] D-094 WINNER: system=%d R:R=%.2f classification=%s → DEMO slot filled",
                    system_id, scored[0][0], setup.get("classification", "?"),
                )

            # LIVE slot fill
            if self._is_live_enabled(system_id) and self.live_slot is None:
                if passes_strict_checks(setup, "live", self):
                    live_trade = self._execute_live(setup, system_id, cross_context)
                    self.live_slot = live_trade
                    logger.info(
                        "[Gateway] D-094 WINNER: system=%d R:R=%.2f → LIVE slot filled",
                        system_id, scored[0][0],
                    )

        # Log outranked candidates
        for i, (rr, conf, neg_sys, c) in enumerate(scored[1:], 1):
            logger.info(
                "[Gateway] D-094 OUTRANKED #%d: system=%d R:R=%.2f classification=%s",
                i, c["system_id"], rr, c["setup"].get("classification", "?"),
            )

    def _get_chop_state(self) -> str:
        """ζ.F2: Read Layer 0 chop state for gating (direct compute — no self-HTTP)."""
        try:
            from backend.v9.systems.layer0.chop_score import get_chop_score

            data = get_chop_score()
            state = data.get("state")
            if state:
                return str(state)
            score = data.get("chop_score")
            if score is None:
                return "UNKNOWN"
            from backend.v9.systems.layer0.chop_score import classify_state

            return classify_state(float(score))
        except Exception:
            return "UNKNOWN"

    def _selfheal_demo_slot(self) -> None:
        """Free the demo slot if its trade is already closed in the DB.

        Defensive cleanup (fail-open: any error keeps the slot untouched).
        Root incident: 2026-07-02 trades 271/272 closed via the Sierra-driven
        FillPoller path which did not call on_trade_close → slot stayed
        occupied and blocked every subsequent demo order.
        """
        if self.demo_slot is None:
            return
        trade_id = self.demo_slot.get("trade_id")
        if not trade_id:
            return
        try:
            from backend.v9.db.read import read_one
            row = read_one(
                "SELECT state FROM v9_trades WHERE id = :tid",
                {"tid": int(trade_id)},
            )
            if row is not None and str(row.get("state", "")).upper() in ("CLOSED", "CANCELLED"):
                logger.warning(
                    "[Gateway] demo_slot SELF-HEAL: trade %s is %s in DB but slot was still "
                    "occupied → freeing (close path bypassed on_trade_close)",
                    trade_id, row.get("state"),
                )
                self.demo_slot = None
        except Exception as e:  # fail-open — never break routing on a heal attempt
            logger.warning("[Gateway] demo_slot self-heal check failed (slot kept): %s", e)

    def on_trade_close(self, trade: dict) -> None:
        """Handle trade closure — free slots, update daily stats, update risk filters."""
        trade_id = trade.get("trade_id")
        mode = trade.get("mode")
        pnl = trade.get("pnl_usd", 0.0)
        outcome = trade.get("outcome", "WIN" if pnl >= 0 else "STOP")
        direction = trade.get("direction", "")

        # ζ.A4: cooldown tracking
        self.cooldown.on_trade_close(outcome)
        # ζ.B2: SSV tracking — 07-15 fix: REAL outcomes only. Shadow noise fed the
        # veto on 07-14 (4 shadow stops → LONG declared "suffering" → 22 real
        # fires blocked). Shadow trades must never gate real trading.
        if mode in ("live", "demo"):
            self.ssv.record_outcome(direction, outcome)

        # Normalize trade_id comparison: slot stores str, notify sends int
        if self.demo_slot and str(self.demo_slot.get("trade_id")) == str(trade_id):
            self.demo_slot = None
            logger.info("[Gateway] DEMO slot freed: %s", trade_id)

        if self.live_slot and str(self.live_slot.get("trade_id")) == str(trade_id):
            self.live_slot = None
            self._daily_trades += 1
            self._daily_pnl += pnl
            if pnl < 0:
                self._consecutive_losses += 1
            else:
                self._consecutive_losses = 0
            logger.info("[Gateway] LIVE slot freed: %s pnl=%.2f", trade_id, pnl)

        # System 6 learning loop (SYSTEM6_EXIT_JOURNAL): stamp the outcome on this
        # trade's pending journal rows so per-signal hit-rates accrue. "helped" is
        # a first-pass proxy (no profit → the exit signal that fired was likely
        # right); a precise MFE-after-signal fill is a later EOD-batch refinement.
        try:
            from backend.v9.systems.system6_journal import (
                fill_outcome as _s6_fill, enabled as _s6_je,
            )
            if _s6_je() and trade_id is not None:
                _s6_fill(int(trade_id),
                         outcome={"pnl_usd": float(pnl), "outcome": outcome},
                         helped=(float(pnl) <= 0.0))
        except Exception as _s6_err:
            logger.debug("[Gateway] System6 outcome-fill errored: %s", _s6_err)

        # Persist exit
        self._persist_exit(trade)

    def reset_daily(self) -> None:
        """Reset daily counters (called at session start)."""
        self._daily_trades = 0
        self._daily_pnl = 0.0
        self._consecutive_losses = 0

    def get_status(self) -> dict:
        """Return gateway status for API."""
        return {
            "shadow_active_count": len(self.shadow_trades),
            "demo_slot": self.demo_slot.get("trade_id") if self.demo_slot else None,
            "demo_slot_system": self.demo_slot.get("firing_system") if self.demo_slot else None,
            "live_slot": self.live_slot.get("trade_id") if self.live_slot else None,
            "live_slot_system": self.live_slot.get("firing_system") if self.live_slot else None,
            "daily_pnl": round(self._daily_pnl, 2),
            "trades_today": self._daily_trades,
            "consecutive_losses": self._consecutive_losses,
            "demo_enabled_systems": sorted(self._demo_enabled_systems),
            "live_enabled_systems": sorted(self._live_enabled_systems),
            "cooldown": self.cooldown.get_state(),
            "cluster_guard": self.cluster_guard.get_state(),
            "ssv": self.ssv.get_state(),
            "chop_state": self._get_chop_state(),
        }

    # ── Internal ──

    def _is_demo_enabled(self, system_id: int) -> bool:
        # Pipeline 5: DEMO_EXECUTION_ENABLED flag gates the DEMO branch at runtime
        if os.getenv("DEMO_EXECUTION_ENABLED", "0").lower() not in ("1", "true", "yes"):
            return False
        return system_id in self._demo_enabled_systems

    def _is_live_enabled(self, system_id: int) -> bool:
        return system_id in self._live_enabled_systems

    def _execute_shadow(self, setup: dict, system_id: int, cross_context: dict) -> dict:
        """SHADOW: TradeManager row + auto-close on 5min bars (PnL in v9_trades)."""
        if self._trade_manager is not None:
            entry = setup.get("entry_price")
            # G1: extract queryable columns from the SAME cross_context snapshot
            g1 = extract_g1_entry_context(cross_context)
            tm_setup = {
                "firing_system": system_id,
                "direction": setup.get("direction", "LONG"),
                "stop": setup.get("stop", 0.0),
                "t1": setup.get("t1", 0.0),
                "t2": setup.get("t2", 0.0),
                "t3": setup.get("t3", 0.0),
                "entry_price": entry,
                "classification": setup.get("classification", ""),
                "confidence": setup.get("confidence", 0.0),
                "metadata": setup.get("metadata") or {},
                "trigger": (
                    setup.get("classification")
                    or (setup.get("metadata") or {}).get("pattern")
                    or (setup.get("metadata") or {}).get("signal")
                ),
                "cross_context": cross_context,
                # G1 promoted columns
                "day_type_at_entry": g1["day_type_at_entry"],
                "pattern_id_at_entry": resolve_pattern_id(setup, g1),
                "session_at_entry": g1["session_at_entry"],
            }
            trade_id = self._trade_manager.accept_setup(tm_setup, "shadow")
            if entry is not None:
                self._trade_manager.on_fill(trade_id, float(entry))
            try:
                self._trade_manager._db.commit()
            except Exception as commit_err:
                logger.warning("[Gateway] SHADOW trade commit failed: %s", commit_err)
            logger.info(
                "[Gateway] SHADOW trade TM id=%d: %s %s system=%d",
                trade_id, tm_setup["direction"], setup.get("classification", ""), system_id,
            )
            return {
                "trade_id": str(trade_id),
                "mode": "shadow",
                "firing_system": system_id,
                "direction": tm_setup["direction"],
                "state": "FILLED",
                "entry_price": entry,
                "entry_ts": datetime.now(timezone.utc).isoformat(),
            }

        trade = self._build_trade("shadow", setup, system_id, cross_context)
        self._persist_trade(trade)
        logger.info("[Gateway] SHADOW trade (legacy persist): %s system=%d",
                     trade["direction"], system_id)
        return trade

    def _execute_demo(self, setup: dict, system_id: int, cross_context: dict) -> dict:
        """DEMO: create a REAL TM trade (mode=demo) + write Sierra SIM command.

        Mirrors _execute_shadow's TM setup but with mode="demo" so the manager's
        _is_demo_mode returns True → dynamic MODIFY_STOP/TARGET reach Sierra.
        Does NOT also create the legacy _build_trade dict.
        """
        if self._trade_manager is not None:
            g1 = extract_g1_entry_context(cross_context)

            # B: seed runner targets if t3 is missing (initial trail target)
            t1 = setup.get("t1") or 0.0
            t2 = setup.get("t2") or 0.0
            t3 = setup.get("t3") or 0.0
            if t1 > 0 and t2 > 0 and t3 <= 0:
                # initial trail target: one structural step beyond t2
                t3 = 2 * t2 - t1
            # Ensure t2 has a value if t1 exists (same formula, one step)
            if t1 > 0 and t2 <= 0:
                direction = (setup.get("direction") or "").upper()
                t2 = t1 + abs(t1 - (setup.get("stop") or t1)) if direction == "LONG" \
                    else t1 - abs(t1 - (setup.get("stop") or t1))

            tm_setup = {
                "firing_system": system_id,
                "direction": setup.get("direction", "LONG"),
                "stop": setup.get("stop", 0.0),
                "t1": t1,
                "t2": t2,
                "t3": t3,
                "entry_price": setup.get("entry_price"),
                "classification": setup.get("classification", ""),
                "confidence": setup.get("confidence", 0.0),
                "metadata": setup.get("metadata") or {},
                "trigger": (
                    setup.get("classification")
                    or (setup.get("metadata") or {}).get("pattern")
                    or (setup.get("metadata") or {}).get("signal")
                ),
                "cross_context": cross_context,
                "day_type_at_entry": g1["day_type_at_entry"],
                "pattern_id_at_entry": resolve_pattern_id(setup, g1),
                "session_at_entry": g1["session_at_entry"],
            }

            trade_id = self._trade_manager.accept_setup(tm_setup, "demo")
            try:
                self._trade_manager._db.commit()
            except Exception as commit_err:
                logger.warning("[Gateway] DEMO trade commit failed: %s", commit_err)

            # Write Sierra command with the seeded targets
            demo_setup = dict(setup)
            demo_setup["t2"] = t2
            demo_setup["t3"] = t3
            command = command_from_setup(
                demo_setup,
                trade_id=str(trade_id),
                account="PA-APEX-125218-01",
                mode="demo",
            )

            logger.info(
                "[Gateway] DEMO trade TM id=%d: %s %s system=%d t1=%.2f t2=%.2f t3=%.2f",
                trade_id, tm_setup["direction"], setup.get("classification", ""),
                system_id, t1, t2, t3,
            )
            return {
                "trade_id": str(trade_id),
                "mode": "demo",
                "firing_system": system_id,
                "direction": tm_setup["direction"],
                "state": "PENDING",
                "entry_price": setup.get("entry_price"),
                "sierra_command": command,
            }

        # Fallback: legacy persist (no TM available)
        trade = self._build_trade("demo", setup, system_id, cross_context)
        self._persist_trade(trade)
        logger.info("[Gateway] DEMO trade (legacy): %s system=%d", trade["direction"], system_id)
        return trade

    def _execute_live(self, setup: dict, system_id: int, cross_context: dict) -> dict:
        """LIVE: create a REAL TM trade (mode=live) + write Sierra LIVE command.

        Mirrors _execute_demo but routes to the LIVE account (APEX-125218-13).
        Flag-gated: LIVE_EXECUTION_V1 must be ON or this stays the old stub
        (log intent, persist, no Sierra order). When ON, Sierra receives the
        order via trade_command.json with mode:"live".
        """
        # Flag gate: if OFF, fall back to stub behavior (zero Sierra orders)
        if os.environ.get("LIVE_EXECUTION_V1", "0").lower() not in ("1", "true", "yes"):
            trade = self._build_trade("live", setup, system_id, cross_context)
            self._persist_trade(trade)
            logger.warning("[Gateway] LIVE trade (stub, LIVE_EXECUTION_V1=OFF): %s %s system=%d — NOT sent to Sierra",
                            trade["direction"], trade.get("classification", ""), system_id)
            return trade

        # Real live execution — mirror of _execute_demo with mode="live"
        if self._trade_manager is not None:
            g1 = extract_g1_entry_context(cross_context)

            t1 = setup.get("t1") or 0.0
            t2 = setup.get("t2") or 0.0
            t3 = setup.get("t3") or 0.0
            if t1 > 0 and t2 > 0 and t3 <= 0:
                t3 = 2 * t2 - t1
            if t1 > 0 and t2 <= 0:
                direction = (setup.get("direction") or "").upper()
                t2 = t1 + abs(t1 - (setup.get("stop") or t1)) if direction == "LONG" \
                    else t1 - abs(t1 - (setup.get("stop") or t1))

            tm_setup = {
                "firing_system": system_id,
                "direction": setup.get("direction", "LONG"),
                "stop": setup.get("stop", 0.0),
                "t1": t1,
                "t2": t2,
                "t3": t3,
                "entry_price": setup.get("entry_price"),
                "classification": setup.get("classification", ""),
                "confidence": setup.get("confidence", 0.0),
                "metadata": setup.get("metadata") or {},
                "trigger": (
                    setup.get("classification")
                    or (setup.get("metadata") or {}).get("pattern")
                    or (setup.get("metadata") or {}).get("signal")
                ),
                "cross_context": cross_context,
                "day_type_at_entry": g1["day_type_at_entry"],
                "pattern_id_at_entry": resolve_pattern_id(setup, g1),
                "session_at_entry": g1["session_at_entry"],
            }

            trade_id = self._trade_manager.accept_setup(tm_setup, "live")
            try:
                self._trade_manager._db.commit()
            except Exception as commit_err:
                logger.warning("[Gateway] LIVE trade commit failed: %s", commit_err)

            # Write Sierra command — LIVE account
            live_setup = dict(setup)
            live_setup["t2"] = t2
            live_setup["t3"] = t3
            command = command_from_setup(
                live_setup,
                trade_id=str(trade_id),
                account=os.environ.get("SIERRA_LIVE_ACCOUNT", "APEX-125218-13"),
                mode="live",
            )

            logger.warning(
                "[Gateway] LIVE trade TM id=%d: %s %s system=%d t1=%.2f t2=%.2f t3=%.2f account=%s",
                trade_id, tm_setup["direction"], setup.get("classification", ""),
                system_id, t1, t2, t3,
                os.environ.get("SIERRA_LIVE_ACCOUNT", "APEX-125218-13"),
            )
            return {
                "trade_id": str(trade_id),
                "mode": "live",
                "firing_system": system_id,
                "direction": tm_setup["direction"],
                "state": "PENDING",
                "entry_price": setup.get("entry_price"),
                "sierra_command": command,
            }

        # Fallback: legacy persist (no TM available)
        trade = self._build_trade("live", setup, system_id, cross_context)
        self._persist_trade(trade)
        logger.info("[Gateway] LIVE trade (legacy): %s system=%d", trade["direction"], system_id)
        return trade

    def _build_trade(self, mode: str, setup: dict, system_id: int, cross_context: dict) -> dict:
        # G1: extract queryable columns from the SAME cross_context snapshot
        g1 = extract_g1_entry_context(cross_context)
        return {
            "trade_id": str(uuid.uuid4())[:12],
            "mode": mode,
            "firing_system": system_id,
            "direction": setup.get("direction", "LONG"),
            "classification": setup.get("classification", ""),
            "state": "OPEN",
            "entry_ts": datetime.now(timezone.utc).isoformat(),
            "entry_price": setup.get("entry_price"),
            "stop": setup.get("stop", 0.0),
            "t1": setup.get("t1", 0.0),
            "t2": setup.get("t2", 0.0),
            "t3": setup.get("t3", 0.0),
            "confidence": setup.get("confidence", 0.0),
            "cross_context": cross_context,
            "metadata": setup.get("metadata", {}),
            # G1 promoted columns
            "day_type_at_entry": g1["day_type_at_entry"],
            "pattern_id_at_entry": resolve_pattern_id(setup, g1),
            "session_at_entry": g1["session_at_entry"],
        }

    def _capture_cross_context(self) -> dict:
        """Snapshot all 6 systems' current state."""
        ctx = {}
        for name, sys_ref in self._system_registry.items():
            try:
                if hasattr(sys_ref, "get_current"):
                    ctx[name] = sys_ref.get_current()
                elif hasattr(sys_ref, "current_state"):
                    ctx[name] = dict(sys_ref.current_state) if isinstance(sys_ref.current_state, dict) else {}
            except Exception:
                ctx[name] = {"error": "snapshot failed"}
        return ctx

    def _persist_trade(self, trade: dict) -> None:
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
            """INSERT INTO v9_trades
            (mode, firing_system, direction, state, entry_ts, entry_price,
             stop, t1, t2, t3, cross_context,
             day_type_at_entry, pattern_id_at_entry, session_at_entry,
             created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade["mode"], trade["firing_system"], trade["direction"],
                trade["state"], trade["entry_ts"], trade["entry_price"],
                trade["stop"], trade["t1"], trade["t2"], trade["t3"],
                json.dumps(trade["cross_context"], default=str),
                trade.get("day_type_at_entry"),
                trade.get("pattern_id_at_entry"),
                trade.get("session_at_entry"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def _persist_exit(self, trade: dict) -> None:
        from backend.v9.db.safe_writer import safe_execute
        # D2 (trade 329/331): truncate varchar fields to column width.
        # Raw SQL bypasses ORM @validates — guard here too.
        _exit_reason = trade.get("exit_reason")
        if _exit_reason and len(str(_exit_reason)) > 30:
            _exit_reason = str(_exit_reason)[:30]
        _outcome = trade.get("outcome")
        if _outcome and len(str(_outcome)) > 10:
            _outcome = str(_outcome)[:10]
        safe_execute(
            """UPDATE v9_trades SET state='CLOSED', exit_ts=?, exit_price=?,
               exit_reason=?, pnl_usd=?, pnl_r=?, outcome=?, updated_at=?
               WHERE mode=? AND entry_ts=? AND state='OPEN'""",
            (
                trade.get("exit_ts"), trade.get("exit_price"),
                _exit_reason, trade.get("pnl_usd"),
                trade.get("pnl_r"), _outcome,
                datetime.now(timezone.utc).isoformat(),
                trade.get("mode"), trade.get("entry_ts"),
            ),
        )
