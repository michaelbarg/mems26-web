"""System 4 — Woodies CCI Decision Maker (5-min bars + 8 active patterns).

Subscribes to woodies_5min bars via BarRouter (D-074).
Computes all 11 Woodies studies per bar via cci_calc.compute_all_studies().
Runs 8 patterns: continuation {ZLR, TLB, TT, GB100} + reversal {VEGAS, GHOST, FAMIR, HTLB}.
HFE disabled (not Michael's pattern, −$2,987 single biggest loser; flag HFE_DISABLED).
Publishes signal events independently.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, time as dtime, timezone
from typing import List, Optional, Dict

from backend.v9.systems.base.trading_system import BaseV9TradingSystem, HydrationResult, SystemType
from backend.v9.systems.woodies.cci_calc import compute_all_studies
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult
from backend.v9.systems.woodies.pattern_engine import detect_all_patterns, PATTERN_IDS
from backend.v9.systems.woodies.pattern_dispatcher import PatternDispatcher
from backend.v9.systems.woodies.direction_change_detector import detect_from_buffer as detect_direction_change
from backend.v9.systems.woodies.stages.a1_strategic_gate import TrendState
from backend.v9.systems.woodies.time_stop import TimeStopEnforcer, load_time_stop_config
from backend.v9.systems.woodies.decision_tree import (
    WoodiesDecisionContext,
    WoodiesDecisionTree,
    _fetch_touchpoints_now,
)

# P30 SLOW handler fix (2026-05-20): touchpoint pre-fetch was removed in favour
# of passing touchpoints={} directly (see process_bar comment). The wall-clock
# budget constant is retained here as documentation of the original cap value.

logger = logging.getLogger(__name__)

# RTH gate: set V9_WOODIES_RTH_ONLY=0 to allow overnight bars (test / replay only)
_RTH_ONLY = os.getenv("V9_WOODIES_RTH_ONLY", "1").lower() not in ("0", "false", "no")
# RTH window: 09:30–16:00 ET (inclusive of close bar)
_RTH_START = dtime(9, 30)
_RTH_END = dtime(16, 0)

try:
    from zoneinfo import ZoneInfo as _ZI
    _ET_TZ = _ZI("America/New_York")
except ImportError:
    try:
        import pytz as _pytz
        _ET_TZ = _pytz.timezone("America/New_York")
    except ImportError:
        _ET_TZ = None


def giant_bar_stop(entry: float, sign: float, risk: float, cap: float,
                   bar_high: float, bar_low: float,
                   frac: float = None, floor: float = None):
    """GIANT_BAR_STOP_V1 (Michael 2026-06-12): intra-entry-bar stop re-anchor.

    When the structural anchor's risk exceeds the pattern cap, place the stop
    inside the entry bar: risk' = clamp(frac×bar_range, floor, cap).
    Returns (new_stop, new_risk) or None when not applicable (smaller risk
    would not result, or degenerate inputs). Caller is flag-gated.
    """
    import os as _os
    if frac is None:
        try:
            frac = float(_os.getenv("GIANT_BAR_STOP_FRACTION", "0.38"))
        except ValueError:
            frac = 0.38
    if floor is None:
        try:
            floor = float(_os.getenv("GIANT_BAR_STOP_FLOOR_PT", "6.0"))
        except ValueError:
            floor = 6.0
    rng = bar_high - bar_low
    if rng <= 0 or cap is None or risk <= 0:
        return None
    # Precondition (2026-06-12 evening fix): only a genuinely GIANT entry bar
    # qualifies — a tiny bar must not be re-anchored via the floor (VEGAS 18:35
    # got a 6pt stop on a 1.0pt bar). Tunable via GIANT_BAR_MIN_RANGE_PT.
    try:
        min_rng = float(_os.getenv("GIANT_BAR_MIN_RANGE_PT", "12.0"))
    except ValueError:
        min_rng = 12.0
    if rng < min_rng:
        return None
    new_risk = min(max(frac * rng, floor), float(cap))
    if 0 < new_risk < risk:
        return (entry - sign * new_risk, new_risk)
    return None


def _is_rth_bar(bar_ts: float) -> bool:
    """Return True if bar_ts (UTC unix seconds) falls within RTH (09:30–16:00 ET).

    Fail-open: returns True if timestamp is zero/unknown or timezone unavailable.
    """
    if not bar_ts or _ET_TZ is None:
        return True
    try:
        dt = datetime.fromtimestamp(bar_ts, tz=_ET_TZ)
        t = dtime(dt.hour, dt.minute)
        return _RTH_START <= t <= _RTH_END
    except Exception:
        return True


# Module-level dispatcher instance (W-8)
_pattern_dispatcher = PatternDispatcher()


class WoodiesSystem(BaseV9TradingSystem):
    system_id = 4
    name = "woodies"
    color = "#f97316"
    system_type = SystemType.FIRING

    def __init__(self, db_path: str = None, rth_only: bool = None):
        self.db_path = db_path or "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
        self._gateway = None  # injected post-init via set_gateway()
        # RTH gate: instance-level override for tests. Defaults to module-level env var.
        self._rth_only: bool = _RTH_ONLY if rth_only is None else rth_only
        # Per-pattern dedup keyed by bar_ts: key=f"{pattern_id}_{direction}" → bar_ts
        # of the last bar that triggered a fire. Blocks duplicate fires when Sierra
        # sends multiple UPDATE events for the same 5-min bar.
        self._last_fired_bar_ts: Dict[str, float] = {}
        # Raw OHLCV buffers for study computation
        self._highs: List[float] = []
        self._lows: List[float] = []
        self._closes: List[float] = []
        self._bar_buffer: List[WoodiesBar] = []
        self.max_buffer = 50
        self._active_patterns: List[PatternResult] = []
        self._last_fire_setup: Optional[dict] = None  # test observability (additive)
        self._decision_tree = WoodiesDecisionTree()
        # W-10: Time stop enforcement (Registry #11) — RE-ENABLED 2026-05-28 evening.
        # Option B REVERSED: W-10 is sole TIME_STOP authority. Bug A (per-push
        # increment) fixed via _last_bar_ts_for_count. Bug D (exit_price=NULL)
        # fixed: exit_price set from _closes[-1] before close_trade().
        ts_cfg = load_time_stop_config()
        self._time_stop_enforcer = TimeStopEnforcer(
            time_stop_minutes=ts_cfg["time_stop_minutes"],
            tick_minutes=ts_cfg["tick_minutes"],
        )
        self._bar_count: int = 0
        self._htlb_dir_bias = None  # HTLB latched S4 direction bias: "UP"/"DOWN"/None (Michael 2026-06-23)
        self._last_bar_ts_for_count: Optional[float] = None
        self._open_fire_records: Dict[str, dict] = {}  # trade_id → {entry_bar_count, pattern_id}
        self.current_state: Dict = {
            "timeframe": "5min",
            "running": False,
            "hydrated": False,
            "cci_14": None,
            "cci_6_tcci": None,
            "ema_34": None,
            "lsma_value": None,
            "swi_value": None,
            "czi_value": None,
            "trend_state": "GRAY",
            "predictor_next_cci": None,
            "signal": "NEUTRAL",
            "direction": None,
            "strength": 0,
            "buffer_size": 0,
            "active_patterns": [],
            "classification": "NO_SETUP",
            "decision_tree": {},
            "entry_classification_spec": None,
            "ready_to_route": False,
        }

    def set_gateway(self, gateway) -> None:
        """Inject TradingGateway for auto-routing fire signals (Prompt 14)."""
        self._gateway = gateway

    def subscribed_bar_types(self) -> List[str]:
        return ["woodies_5min"]

    def hydrate(self) -> HydrationResult:
        """Load last N bars from v9_bars_5min_woodies for warm start."""
        from backend.v9.db.read import read_all
        loaded = 0
        try:
            rows = read_all(
                "SELECT * FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT :limit",
                {"limit": self.max_buffer},
            )

            # Reverse to oldest-first
            for row in reversed(rows):
                r = row
                self._highs.append(float(r["high"]))
                self._lows.append(float(r["low"]))
                self._closes.append(float(r["close"]))
                wb = WoodiesBar(
                    ts=0,  # historical, no exact epoch needed
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=float(r.get("volume", 0)),
                    cci_14=float(r.get("cci_14") or 0),
                    cci_6_tcci=float(r.get("cci_6_tcci") or 0),
                    ema_34=float(r.get("ema_34") or 0),
                    lsma_value=float(r.get("lsma_value") or 0),
                    swi_value=float(r.get("swi_value") or 0),
                    czi_value=float(r.get("czi_value") or 0),
                    trend_state=r.get("trend_state") or "GRAY",
                    predictor_next_cci=float(r.get("predictor_next_cci") or 0),
                    hfe_detected=bool(r.get("hfe_detected", False)),
                    hfe_direction=r.get("hfe_direction") or "NONE",
                    hfe_extreme_bars_ago=int(r.get("hfe_extreme_bars_ago") or 0),
                )
                self._bar_buffer.append(wb)
                loaded += 1
        except Exception as e:
            logger.warning("[Woodies] Hydration from DB failed (non-fatal): %s", e)

        self.current_state["running"] = True
        self.current_state["hydrated"] = True
        self.current_state["buffer_size"] = len(self._bar_buffer)

        # Recompute current studies from buffer if we have data
        if self._bar_buffer:
            last = self._bar_buffer[-1]
            self.current_state.update({
                "cci_14": last.cci_14,
                "cci_6_tcci": last.cci_6_tcci,
                "trend_state": last.trend_state,
            })

        return HydrationResult(
            success=True,
            reached_state="ACTIVE",
            confidence=1.0,
            notes=f"Woodies CCI ready; hydrated {loaded} bars from DB; subscribed to woodies_5min",
        )

    def process(self, event: Dict) -> Optional[Dict]:
        return None

    async def process_bar(self, event) -> None:
        """Process a 5-min Woodies bar: compute studies, detect patterns, persist."""
        try:
            bar = dict(event.payload) if hasattr(event, 'payload') else dict(event)
            # Floor ts to 5-min boundary for dedup — Sierra sends multiple
            # pushes per bar (each with unique ms/fractional ts). Without flooring,
            # _bar_count inflates and TIME_STOP fires at ~32 min instead of 90.
            _raw_ts = bar.get("ts")
            if _raw_ts is not None:
                try:
                    _ts_num = float(_raw_ts)
                    _bar_ts_key = int(_ts_num - (_ts_num % 300))  # floor to 5-min
                except (TypeError, ValueError):
                    # ISO string: parse to epoch then floor to 5-min bucket
                    try:
                        from datetime import datetime as _dt, timezone as _tz
                        _parsed = _dt.fromisoformat(str(_raw_ts).replace("Z", "+00:00"))
                        if _parsed.tzinfo is None:
                            _parsed = _parsed.replace(tzinfo=_tz.utc)
                        _ep = _parsed.timestamp()
                        _bar_ts_key = int(_ep - (_ep % 300))
                    except (ValueError, TypeError):
                        _bar_ts_key = str(_raw_ts)[:16]  # last resort: minute
            else:
                _bar_ts_key = None
            _is_new_bar = _bar_ts_key is not None and _bar_ts_key != self._last_bar_ts_for_count
            if _is_new_bar:
                self._bar_count += 1
                self._last_bar_ts_for_count = _bar_ts_key

            h = float(bar.get("high", bar.get("h", 0)))
            l = float(bar.get("low", bar.get("l", 0)))
            c = float(bar.get("close", bar.get("c", 0)))
            o = float(bar.get("open", bar.get("o", 0)))
            v = float(bar.get("volume", bar.get("v", 0)))

            # Append to OHLCV buffers
            self._highs.append(h)
            self._lows.append(l)
            self._closes.append(c)

            # Trim buffers
            if len(self._highs) > self.max_buffer:
                self._highs = self._highs[-self.max_buffer:]
                self._lows = self._lows[-self.max_buffer:]
                self._closes = self._closes[-self.max_buffer:]

            # Use Sierra DLL study values when present (source of truth per CLAUDE.md).
            # The DLL computes CCI/EMA/LSMA from full history → far more accurate than
            # our 50-bar local buffer. Fall back to local compute only if DLL values absent.
            if bar.get("cci_14") is not None:
                studies = {
                    "cci_14": float(bar.get("cci_14") or 0),
                    "cci_6_tcci": float(bar.get("cci_6_tcci") or 0),
                    "ema_34": float(bar.get("ema_34") or 0),
                    "lsma_value": float(bar.get("lsma_value") or 0),
                    "lsma_above_price": bool(bar.get("lsma_above_price", False)),
                    "swi_value": float(bar.get("swi_value") or 0),
                    "czi_value": float(bar.get("czi_value") or 0),
                    "trend_state": str(bar.get("trend_state") or "GRAY"),
                    "predictor_next_cci": float(bar.get("predictor_next_cci") or 0),
                    "hfe_detected": bool(bar.get("hfe_detected", False)),
                    "hfe_direction": str(bar.get("hfe_direction") or "NONE"),
                    "hfe_extreme_bars_ago": int(bar.get("hfe_extreme_bars_ago") or 0),
                    "zlr_detected": bool(bar.get("zlr_detected", False)),
                    "zlr_direction": str(bar.get("zlr_direction") or "NONE"),
                }
            else:
                # Fallback: compute locally (pre-DLL or test bars without study values)
                studies = compute_all_studies(self._highs, self._lows, self._closes)

            # D-WDIAG: Extreme-CCI trend relabel at the SINGLE source (studies dict)
            # so EVERY consumer — detection, dispatcher, decision_tree A1 gate, display,
            # persist — sees one consistent trend_state. |CCI|>=200 = strong established
            # trend; Sierra GRAY/YELLOW here is transition-lag (audit: 6 bars confirmed).
            # Flag-gated; default OFF = raw Sierra trend.
            # D-WDIAG: call shared relabel function (single source of truth)
            from backend.v9.systems.woodies.trend_relabel import apply_extreme_trend_relabel
            apply_extreme_trend_relabel(studies)

            # Build WoodiesBar for pattern engine
            bar_ts = bar.get("ts", 0)
            if isinstance(bar_ts, str):
                try:
                    bar_ts = datetime.fromisoformat(bar_ts.replace("Z", "+00:00")).timestamp()
                except Exception:
                    bar_ts = 0

            # RTH gate (filter-F17): skip non-RTH bars to prevent overnight/globex fires.
            # Disable via V9_WOODIES_RTH_ONLY=0 env var or rth_only=False constructor arg.
            if self._rth_only and not _is_rth_bar(float(bar_ts)):
                logger.debug(
                    "[Woodies] RTH gate: skipping non-RTH bar ts=%s", bar_ts
                )
                # Still run time-stop checks on any open trades
                self._check_time_stops()
                return

            wb = WoodiesBar(
                ts=float(bar_ts),
                open=o, high=h, low=l, close=c, volume=v,
                **studies,
            )
            if _is_new_bar:
                self._bar_buffer.append(wb)
                if len(self._bar_buffer) > self.max_buffer:
                    self._bar_buffer = self._bar_buffer[-self.max_buffer:]
            elif self._bar_buffer:
                self._bar_buffer[-1] = wb  # update latest with fresh OHLC

            if not _is_new_bar:
                return  # dedup: detection + fire only on genuinely new bar ts

            # Run pattern engine — DLL flags as primary, Python detectors as fallback.
            # DLL computes on full Sierra history (thousands of bars) → more accurate
            # than 50-bar Python buffer. Michael approved 2026-06-01.
            _HFE_DISABLED = os.environ.get("HFE_DISABLED", "0").lower() in ("1", "true", "yes")
            patterns = detect_all_patterns(self._bar_buffer)
            if _HFE_DISABLED:
                patterns = [p for p in patterns if p.pattern_id != "HFE"]
            # T3: filter any pattern with stop=None/0 (crash-safe — never let bad stop through)
            _bad_stops = [p for p in patterns if p.detected and (p.stop is None or p.stop <= 0)]
            if _bad_stops:
                logger.warning("[Woodies] T3 guard: %d pattern(s) with bad stop filtered: %s",
                               len(_bad_stops), [(p.pattern_id, p.stop) for p in _bad_stops])
                patterns = [p for p in patterns if not p.detected or (p.stop is not None and p.stop > 0)]

            # DLL-detected patterns: if DLL flags ZLR/HFE and Python missed it,
            # trust the DLL (source-of-truth per CLAUDE.md §Sierra real-time data).
            # Compute a real stop (not None/0.0) using the same ATR machinery as
            # the Python detectors — stop=None crashes PatternResult (schemas.py:78),
            # stop=0.0 → R:R garbage → blocked by r_t1_gate. Bug #1 fix 2026-06-08.
            _dll_pattern_ids = {p.pattern_id for p in patterns}
            if (wb.zlr_detected and "ZLR" not in _dll_pattern_ids) or \
               (wb.hfe_detected and "HFE" not in _dll_pattern_ids):
                from backend.v9.systems.woodies.schemas import PatternResult
                from backend.v9.systems.woodies.atr_stop import compute_stop, compute_stop_v2, PatternGroup
                from backend.v9.shared.atr import flag as _flag
                # Compute ATR-14 from buffer (same as Python detectors)
                _dll_atr = 0.0
                if len(self._bar_buffer) >= 14:
                    _trs = []
                    for _i, _b in enumerate(self._bar_buffer):
                        _br = _b.high - _b.low
                        if _i > 0:
                            _pc = self._bar_buffer[_i-1].close
                            _br = max(_br, abs(_b.high - _pc), abs(_b.low - _pc))
                        _trs.append(_br)
                    _dll_atr = sum(_trs[:14]) / 14
                    for _tr in _trs[14:]:
                        _dll_atr = ((_dll_atr * 13) + _tr) / 14
                    _dll_atr = _dll_atr / 0.25  # convert to ticks

            if wb.zlr_detected and "ZLR" not in _dll_pattern_ids:
                _zlr_dir = "LONG" if wb.zlr_direction == "UP" else "SHORT" if wb.zlr_direction == "DOWN" else None
                if _zlr_dir and _dll_atr > 0:
                    _zlr_group = PatternGroup.CONT_TIGHT
                    if _flag("STOP_ANCHORS_V2"):
                        from backend.v9.config_loader import load_stop_anchors
                        from backend.v9.systems.stop_anchors import resolver as SA
                        _sa_cfg = load_stop_anchors()
                        if _sa_cfg:
                            _a = _sa_cfg["anchors"]["ZLR"]
                            _w_bars = self._bar_buffer[-_a["window"]:]
                            _struct = SA.resolve_anchor_from_window(_w_bars, _zlr_dir,
                                        _sa_cfg["principles"]["anchor_offset_ticks"], 0.25)
                            _v2 = compute_stop_v2(_zlr_dir, wb.close, _struct, _zlr_group, _dll_atr)
                            _zlr_stop = _v2.stop_price
                        else:
                            _sr = compute_stop(_zlr_dir, wb, swing_anchor=None,
                                               pattern_group=_zlr_group, atr_14=_dll_atr)
                            _zlr_stop = _sr.stop_price
                    else:
                        _sr = compute_stop(_zlr_dir, wb, swing_anchor=None,
                                           pattern_group=_zlr_group, atr_14=_dll_atr)
                        _zlr_stop = _sr.stop_price
                    _zlr_t1 = wb.close + (4 * 0.25 if _zlr_dir == "LONG" else -4 * 0.25)
                    # T3: guard against stop=None → PatternResult crash (pydantic ValidationError)
                    if _zlr_stop is not None and _zlr_stop > 0:
                        patterns.append(PatternResult(
                            detected=True, pattern_id="ZLR", direction=_zlr_dir,
                            confidence=0.65, raw_confidence=0.65,
                            entry_price=wb.close, stop=_zlr_stop, targets=[_zlr_t1],
                            group="CONTINUATION", cci_at_signal=wb.cci_14,
                            bar_index=len(self._bar_buffer) - 1, ts=wb.ts,
                            details={"source": "dll_flag", "zlr_direction": wb.zlr_direction},
                        ))
                    else:
                        logger.warning("[Woodies] DLL ZLR skipped: stop=%s (None/0 — T3 guard)", _zlr_stop)
            if wb.hfe_detected and "HFE" not in _dll_pattern_ids and not _HFE_DISABLED:
                _hfe_dir = "LONG" if wb.hfe_direction == "UP" else "SHORT" if wb.hfe_direction == "DOWN" else None
                if _hfe_dir and _dll_atr > 0:
                    _hfe_group = PatternGroup.REV
                    _lb = min(12, len(self._bar_buffer))
                    _swing = min(b.low for b in self._bar_buffer[-_lb:]) if _hfe_dir == "LONG" \
                        else max(b.high for b in self._bar_buffer[-_lb:])
                    if _flag("STOP_ANCHORS_V2"):
                        from backend.v9.config_loader import load_stop_anchors
                        from backend.v9.systems.stop_anchors import resolver as SA
                        _sa_cfg = load_stop_anchors()
                        if _sa_cfg:
                            _struct = SA.apply_offset(_swing, _hfe_dir,
                                        _sa_cfg["principles"]["anchor_offset_ticks"], 0.25)
                            _v2 = compute_stop_v2(_hfe_dir, wb.close, _struct, _hfe_group, _dll_atr)
                            _hfe_stop = _v2.stop_price
                        else:
                            _sr = compute_stop(_hfe_dir, wb, swing_anchor=_swing,
                                               pattern_group=_hfe_group, atr_14=_dll_atr)
                            _hfe_stop = _sr.stop_price
                    else:
                        _sr = compute_stop(_hfe_dir, wb, swing_anchor=_swing,
                                           pattern_group=_hfe_group, atr_14=_dll_atr)
                        _hfe_stop = _sr.stop_price
                    _hfe_t1 = wb.close + (4 * 0.25 if _hfe_dir == "LONG" else -4 * 0.25)
                    # T3: guard against stop=None → PatternResult crash
                    if _hfe_stop is not None and _hfe_stop > 0:
                        patterns.append(PatternResult(
                            detected=True, pattern_id="HFE", direction=_hfe_dir,
                            confidence=0.60, raw_confidence=0.60,
                            entry_price=wb.close, stop=_hfe_stop, targets=[_hfe_t1],
                            group="REVERSAL", cci_at_signal=wb.cci_14,
                            bar_index=len(self._bar_buffer) - 1, ts=wb.ts,
                            details={"source": "dll_flag", "hfe_direction": wb.hfe_direction,
                                     "hfe_extreme_bars_ago": wb.hfe_extreme_bars_ago},
                        ))
                    else:
                        logger.warning("[Woodies] DLL HFE skipped: stop=%s (None/0 — T3 guard)", _hfe_stop)

            # ── HTLB direction gate (Michael 2026-06-23 · flag HTLB_DIRECTION_GATE, default OFF) ──
            # HTLB signals the directional bias for ALL Woodies patterns. A zoned HTLB break
            # latches its direction (UP/DOWN) until the next zoned HTLB; while a bias is latched
            # and the flag is on, only patterns in that direction may fire. Fail-open.
            try:
                from backend.v9.systems.woodies.patterns.htlb import htlb_zoned_direction as _htlb_zd
                from backend.v9.shared.atr import flag
                _zd = _htlb_zd(self._bar_buffer)
                if _zd:
                    self._htlb_dir_bias = _zd  # latch until the next zoned HTLB
                if flag("HTLB_DIRECTION_GATE") and self._htlb_dir_bias:
                    _allowed = "LONG" if self._htlb_dir_bias == "UP" else "SHORT"
                    _n0 = len(patterns)
                    patterns = [p for p in patterns if getattr(p, "direction", None) == _allowed]
                    if len(patterns) != _n0:
                        logger.info("[Woodies] HTLB dir-gate (bias=%s->%s): %d->%d patterns",
                                    self._htlb_dir_bias, _allowed, _n0, len(patterns))
            except Exception as _hdg_err:
                logger.warning("[Woodies] HTLB dir-gate errored (fail-open): %s", _hdg_err)

            self._active_patterns = patterns

            # W3-β: Direction Change detection (TCCI crosses CCI14)
            dir_change = detect_direction_change(self._bar_buffer)
            if dir_change:
                self.current_state["last_direction_change"] = dir_change
                logger.info("[Woodies] Direction change: %s — %s",
                            dir_change["direction"], dir_change["reasoning_notes"])

            # Classify overall state
            signal = "NEUTRAL"
            direction = None
            strength = 0
            classification = "NO_SETUP"
            sizing = "reject"

            # F-16: resolve trend state before dispatch — needed for YELLOW guard below
            # D-S4FIX: use studies (current bar, post-relabel) not stale current_state
            trend_state_str = (studies.get("trend_state") or "GRAY").upper()
            try:
                _ts = TrendState(trend_state_str)
            except ValueError:
                _ts = TrendState.GRAY

            # P-W5 LOCK A: YELLOW blocks all 9 patterns. detect_all_patterns runs
            # unconditionally; we drop here rather than letting select_winner raise
            # ValueError into the outer except handler (F-16 fix).
            if patterns and _ts == TrendState.YELLOW:
                logger.warning("[Woodies] YELLOW state — %d pattern(s) blocked (P-W5 LOCK A)", len(patterns))
                patterns = []

            if patterns:
                # W-8: Two-tier R_t1 dispatch replaces naive max(confidence)
                dispatch_result = _pattern_dispatcher.select_winner(patterns, _ts)
                best = dispatch_result.winner
                if best is None:
                    best = max(patterns, key=lambda p: p.confidence)  # safety net
                signal = best.pattern_id
                direction = best.direction
                strength = int(best.confidence * 4)
                classification = "STRATEGIC" if best.group == "REVERSAL" else "TACTICAL"
                sizing = self.calculate_size(signal, direction)
                # Provisional day_type (shared with fire_setup below)
                # Priority: current_state → promoted 7-type classifier (day_type_machine)
                # → v9_day_type_state (persisted) → hardcoded "Normal"
                _s4_day_type = self.current_state.get("day_type")
                if not _s4_day_type or _s4_day_type in ("UNKNOWN", "None"):
                    try:
                        import importlib as _il
                        _app2 = _il.import_module("backend.v9.app").app
                        _dtm2 = getattr(_app2.state, "day_type_machine", None)
                        if _dtm2:
                            _dt2 = getattr(_dtm2, "day_type", None)
                            _dt2_val = _dt2.value if hasattr(_dt2, "value") else (str(_dt2) if _dt2 else None)
                            if _dt2_val and _dt2_val not in ("UNKNOWN", "None", "INDETERMINATE"):
                                _s4_day_type = _dt2_val
                    except Exception:
                        pass
                if not _s4_day_type or _s4_day_type in ("UNKNOWN", "None"):
                    try:
                        from backend.v9.db.read import read_one as _r1
                        from datetime import datetime as _datetime
                        from zoneinfo import ZoneInfo as _ZI
                        _ct = _ZI("America/Chicago")
                        _today_s4 = _datetime.now(_ct).date().isoformat()
                        _row = _r1(
                            "SELECT day_type FROM v9_day_type_state "
                            "WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d "
                            "ORDER BY id DESC LIMIT 1", {"d": _today_s4})
                        if _row and _row.get("day_type"):
                            _s4_day_type = _row["day_type"]
                    except Exception:
                        pass
                if not _s4_day_type or _s4_day_type in ("UNKNOWN", "None"):
                    _s4_day_type = "Normal"

                # V2 sizing override when flag ON
                from backend.v9.shared.atr import flag as _flag
                if _flag("STOP_ANCHORS_V2") and best.entry_price and best.stop:
                    try:
                        from backend.v9.config_loader import load_stop_anchors, load_auth_matrix
                        from backend.v9.systems.stop_anchors.sizing import compute_v2_sizing
                        _sa_cfg = load_stop_anchors()
                        if _sa_cfg:
                            _auth = load_auth_matrix()
                            _trend = studies.get("trend_state", "GRAY")
                            _day_has_dir = _trend in ("BLUE", "RED")
                            _with_trend = (
                                (direction == "LONG" and _trend == "BLUE") or
                                (direction == "SHORT" and _trend == "RED")
                            ) if _day_has_dir else None
                            _is_rev = best.group == "REVERSAL"
                            _anchor_cfg = _sa_cfg["anchors"].get(signal, {})
                            _v2s = compute_v2_sizing(
                                entry_price=best.entry_price,
                                stop_price=best.stop,
                                direction=direction,
                                pattern_key=signal,
                                day_type=_s4_day_type,
                                confidence_tier="medium",
                                day_has_direction=_day_has_dir,
                                trade_with_trend=_with_trend,
                                value_area_full_traverse=None,
                                cfg=_sa_cfg,
                                auth_matrix=_auth,
                                reversal=_is_rev,
                                ladder_shift=_anchor_cfg.get("t1_ladder_shift", 0),
                            )
                            if _v2s is None:
                                sizing = "reject"
                            else:
                                _c = _v2s.contracts
                                sizing = "full" if _c >= 3 else ("half" if _c >= 2 else ("reject" if _c == 0 else "half"))
                                logger.info("[Woodies] V2 sizing: %s contracts=%d mode=%s risk=%.1fpt",
                                            signal, _c, _v2s.mode, _v2s.risk_points)
                    except Exception as _e:
                        logger.warning("[Woodies] V2 sizing failed (%s) — using legacy", _e)
                # ζ.H1: reasoning_notes (AP-SY02)
                reasoning_notes = (f"{signal} {direction} size={sizing}: "
                                   f"CCI={studies['cci_14']:.1f}, trend={studies['trend_state']}, "
                                   f"conf={best.confidence:.2f}, group={best.group}")
                self.current_state["last_reasoning_notes"] = reasoning_notes

            # _s4_day_type already computed above (shared with sizing)

            fire_setup = None
            if patterns and direction and sizing != "reject":
                if best.entry_price and best.stop:
                    # PHASE 1 (2026-06-10): S4 targets per spec table.
                    # T1 = ladder/measure per pattern. T2 = VEGAS only (Measure×1.0).
                    # All CCI-cross targets (CONT T2/T3, GHOST T2/T3, etc.) = None
                    # (deferred to CCI-cross monitor §1.6). Flag-gated STOP_ANCHORS_V2.
                    _s4_entry = best.entry_price
                    _s4_stop = best.stop
                    _s4_risk = abs(_s4_entry - _s4_stop)
                    _s4_sign = 1.0 if direction == "LONG" else -1.0
                    _s4_t1 = _s4_entry + _s4_sign * _s4_risk  # 1R fallback
                    _s4_t2 = None  # CCI-cross default (honest None)
                    _s4_t3 = None
                    _s4_time_stop = 90
                    _pid = best.pattern_id

                    # PATTERN_RISK_CAPS: per-pattern max risk (2026-06-12 anchor trial)
                    if _flag("PATTERN_RISK_CAPS") and _flag("STOP_ANCHORS_V2"):
                        try:
                            from backend.v9.config_loader import load_stop_anchors as _lsa_rc
                            _rc_cfg = _lsa_rc()
                            if _rc_cfg:
                                _rc_anchor = _rc_cfg["anchors"].get(_pid, {})
                                _rc_max = _rc_anchor.get("max_risk_points")
                                # PATTERN_LOSS_BREAKER (Michael 2026-06-12 evening — "stricter
                                # rules for losing patterns, from today"): after N losing
                                # closes on this pattern today, block it for the session.
                                if _flag("PATTERN_LOSS_BREAKER"):
                                    try:
                                        import os as _lb_os
                                        _lb_n = int(_lb_os.getenv("PATTERN_LOSS_BREAKER_N", "2"))
                                        from backend.v9.db.read import read_scalar as _lb_rs
                                        _lb_losses = _lb_rs(
                                            "SELECT COUNT(*) FROM v9_trades WHERE entry_ts::date = CURRENT_DATE "
                                            "AND pattern_id_at_entry = :pid AND pnl_usd < 0 AND state = 'CLOSED'",
                                            {"pid": _pid},
                                        ) or 0
                                        if _lb_losses >= _lb_n:
                                            logger.info(
                                                "[Woodies] PATTERN_LOSS_BREAKER: %s blocked for session (%d losses today >= %d)",
                                                _pid, _lb_losses, _lb_n,
                                            )
                                            sizing = "reject"
                                    except Exception as _lb_err:
                                        logger.warning("[Woodies] PATTERN_LOSS_BREAKER check failed: %s", _lb_err)

                                if _rc_max and _s4_risk > _rc_max and sizing != "reject":
                                    # GIANT_BAR exclusion (Michael 2026-06-12 evening): for
                                    # patterns where the re-anchor softening was a mistake
                                    # (ZLR, HFE) — over-cap means SKIP, no re-anchor.
                                    import os as _gx_os
                                    _gb_excluded = _pid in [s.strip() for s in _gx_os.getenv(
                                        "GIANT_BAR_EXCLUDE", "ZLR,HFE").split(",") if s.strip()]
                                    if _gb_excluded:
                                        logger.info(
                                            "[Woodies] RISK_CAP_STRICT_SKIP: %s %s risk=%.1fpt > cap=%dpt (excluded pattern→SKIP)",
                                            _pid, direction, _s4_risk, _rc_max,
                                        )
                                        sizing = "reject"
                                if _rc_max and _s4_risk > _rc_max and sizing != "reject":
                                    # GIANT_BAR_STOP_V1 (Michael approved 2026-06-12 midday):
                                    # when the structural anchor is beyond the pattern cap,
                                    # re-anchor the stop INSIDE the entry bar instead of
                                    # SIZE_DOWN/SKIP: risk = max(fraction×bar_range, floor),
                                    # never above the cap. Fixes the giant-bar chain: inflated
                                    # risk → scalp T1 → absurd 2R T2 → S2 R:R rejections.
                                    _gb_done = False
                                    if _flag("GIANT_BAR_STOP_V1") and self._bar_buffer:
                                        try:
                                            _eb = self._bar_buffer[-1]
                                            _gb = giant_bar_stop(
                                                _s4_entry, _s4_sign, _s4_risk, _rc_max,
                                                float(_eb.high), float(_eb.low),
                                            )
                                            if _gb is not None:
                                                _gb_old = _s4_stop
                                                _s4_stop, _s4_risk = _gb
                                                _s4_t1 = _s4_entry + _s4_sign * _s4_risk  # refresh 1R fallback
                                                logger.info(
                                                    "[Woodies] GIANT_BAR_STOP: %s %s anchor=%.2f (%.1fpt) → intra-bar stop=%.2f (%.1fpt, bar_range=%.1f)",
                                                    _pid, direction, _gb_old,
                                                    abs(_s4_entry - _gb_old), _s4_stop, _s4_risk,
                                                    float(_eb.high) - float(_eb.low),
                                                )
                                                _gb_done = True
                                        except Exception as _gb_err:
                                            logger.warning("[Woodies] GIANT_BAR_STOP failed: %s", _gb_err)
                                    if _gb_done:
                                        pass  # re-anchored within cap — no SKIP/SIZE_DOWN needed
                                    elif (_rc_anchor.get("group", best.group or "CONT")) == "REV" or best.group == "REVERSAL":
                                        logger.info(
                                            "[Woodies] RISK_CAP_SKIP: %s %s risk=%.1fpt > cap=%dpt (REV→SKIP)",
                                            _pid, direction, _s4_risk, _rc_max,
                                        )
                                        sizing = "reject"
                                    else:
                                        logger.info(
                                            "[Woodies] RISK_CAP_SIZE_DOWN: %s %s risk=%.1fpt > cap=%dpt (CONT→1 contract)",
                                            _pid, direction, _s4_risk, _rc_max,
                                        )
                                        sizing = "half" if sizing != "reject" else sizing
                        except Exception as _rc_err:
                            logger.warning("[Woodies] PATTERN_RISK_CAPS check failed: %s", _rc_err)

                    if _flag("STOP_ANCHORS_V2") and _s4_risk > 0:
                        try:
                            from backend.v9.config_loader import load_stop_anchors
                            from backend.v9.systems.stop_anchors import resolver as SA
                            _sa = load_stop_anchors()
                            if _sa:
                                _acfg = _sa["anchors"].get(_pid, {})
                                _is_rev = _acfg.get("group") == "REV" or best.group == "REVERSAL"
                                _measure_cap = _acfg.get("t1_measure_cap")
                                _shift = _acfg.get("t1_ladder_shift", 0)

                                if _pid in ("VEGAS",) and _measure_cap:
                                    # VEGAS: T1 = Measure×cap, T2 = Measure×t2_mult
                                    # FIX A: measure from detector (Rule 1), NO proxy
                                    _measure = best.details.get("measure_pts") if best.details else None
                                    if _measure and _measure > 0:
                                        _s4_t1 = _s4_entry + _s4_sign * _measure_cap * _measure
                                        _t2_mult = _acfg.get("t2_measure_mult", 1.0)
                                        _s4_t2 = _s4_entry + _s4_sign * _t2_mult * _measure
                                    # else: T1/T2 stay as 1R fallback / None (honest)
                                elif _pid in ("GHOST",) and _measure_cap:
                                    # GHOST: T1 = Measure×cap, T2/T3 = None (CCI-cross)
                                    # FIX A: measure from detector (Rule 1), NO proxy
                                    _measure = best.details.get("measure_pts") if best.details else None
                                    if _measure and _measure > 0:
                                        _s4_t1 = _s4_entry + _s4_sign * _measure_cap * _measure
                                else:
                                    # CONT + FAMIR/HTLB/HFE: T1 from risk ladder
                                    _t1_v2 = _flag("T1_LADDER_V2")
                                    _s4_t1 = SA.t1_price(
                                        _s4_entry, _s4_stop, direction,
                                        t1_ladder_cont=_sa.get("t1_ladder_continuation_v2", _sa["t1_ladder_continuation"]) if _t1_v2 else _sa["t1_ladder_continuation"],
                                        reversal=_is_rev,
                                        reversal_mult=_sa.get("t1_reversal_multiplier_v2", 0.8) if _t1_v2 else _sa.get("t1_reversal_multiplier", 0.8),
                                        t1_floor_points=_sa.get("t1_floor_points", 3.0),
                                        ladder_shift=_shift,
                                    )
                                    # T2/T3 = None (CCI-cross, deferred §1.6)
                        except Exception as _e:
                            logger.warning("[Woodies] S4 target calc failed: %s", _e)

                    # RUNNER_TARGETS_V1: compute T2 for the runner (flag-gated, default OFF)
                    if _flag("RUNNER_TARGETS_V1") and _s4_t2 is None and _s4_risk > 0:
                        try:
                            _acfg_rt = {}
                            if _flag("STOP_ANCHORS_V2"):
                                from backend.v9.config_loader import load_stop_anchors as _lsa_rt
                                _rt_cfg = _lsa_rt()
                                if _rt_cfg:
                                    _acfg_rt = _rt_cfg["anchors"].get(_pid, {})
                            _rt_is_rev = _acfg_rt.get("group") == "REV" or best.group == "REVERSAL"
                            _rt_r_mult = 1.5 if _rt_is_rev else 2.0
                            _rt_t2_r = _s4_entry + _s4_sign * _rt_r_mult * _s4_risk

                            # Structural level from day_type (IB edge / POC / VA)
                            _rt_struct = None
                            try:
                                from backend.v9.systems.day_type.day_type_targets import compute_targets_for_day_type
                                _rt_dt = _s4_day_type if _s4_day_type and _s4_day_type != "UNKNOWN" else "Variation"
                                _rt_dt_targets = compute_targets_for_day_type(
                                    day_type=_rt_dt,
                                    entry_price=_s4_entry,
                                    stop_price=_s4_stop,
                                    direction=direction,
                                )
                                if _rt_dt_targets:
                                    _rt_struct = _rt_dt_targets.get("t2_price")
                                    if _rt_struct is None:
                                        logger.debug(
                                            "[Woodies] RUNNER_T2 struct=None: dt=%s targets=%s",
                                            _rt_dt, {k: v for k, v in _rt_dt_targets.items() if k.startswith("t")},
                                        )
                                else:
                                    logger.debug("[Woodies] RUNNER_T2: compute_targets returned None for dt=%s", _rt_dt)
                            except Exception as _struct_err:
                                logger.warning("[Woodies] RUNNER_T2 struct calc error: %s", _struct_err)

                            # T2 = closer-of R-multiple and structural level
                            if _rt_struct is not None:
                                if direction == "LONG":
                                    _s4_t2 = min(_rt_t2_r, _rt_struct)
                                else:
                                    _s4_t2 = max(_rt_t2_r, _rt_struct)
                            else:
                                _s4_t2 = _rt_t2_r

                            logger.info(
                                "[Woodies] RUNNER_T2: %s %s t2=%.2f (R-mult=%.2f struct=%s rev=%s)",
                                _pid, direction, _s4_t2, _rt_t2_r,
                                f"{_rt_struct:.2f}" if _rt_struct else "None",
                                _rt_is_rev,
                            )
                        except Exception as _rt_err:
                            logger.warning("[Woodies] RUNNER_TARGETS_V1 T2 calc failed: %s", _rt_err)

                    fire_setup = {
                        "direction": direction,
                        "entry_price": _s4_entry,
                        "stop_price": _s4_stop,
                        "t1_price": _s4_t1,
                        "t2_price": _s4_t2,
                        "time_stop_minutes": _s4_time_stop,
                        "confidence": int(best.confidence * 100),
                    }
                    self._last_fire_setup = fire_setup  # test observability

            # P30: Skip sync HTTP touchpoint fetch — it self-deadlocks the
            # event loop (5 requests × 2s timeout to localhost:8000 which
            # can't respond because THIS handler is blocking it).
            # asyncio.to_thread didn't help: the thread's HTTP requests
            # still target the same single-worker uvicorn that's blocked.
            # Touchpoints are advisory-only (A4 stage) — empty dict is safe.
            # TODO: replace with in-process cache populated by a background task.

            # Populate day_type touchpoint from DB (same source S2 uses via hydrate)
            _tp = {}
            try:
                from backend.v9.db.read import read_one
                _dt_row = read_one(
                    "SELECT day_type, confidence, lock_state FROM v9_day_type_state "
                    "ORDER BY id DESC LIMIT 1", {},
                )
                if _dt_row and _dt_row["day_type"] and _dt_row["day_type"] != "UNKNOWN":
                    _tp["day_type"] = {
                        "classified": True,
                        "data": {"day_type": _dt_row["day_type"]},
                        "day_type": _dt_row["day_type"],
                        "confidence": float(_dt_row["confidence"] or 0),
                    }
            except Exception:
                pass

            dt_ctx = WoodiesDecisionContext(
                bars=list(self._bar_buffer),
                studies=studies,
                patterns=patterns,
                classification=classification,
                direction=direction,
                sizing=sizing,
                current_state=self.current_state,
                fire_setup=fire_setup,
                touchpoints=_tp,
            )
            dt_summary = self._decision_tree.evaluate_bar(dt_ctx)

            # Update current state
            self.current_state.update({
                "bar_count": self._bar_count,  # D-S4FIX: expose for Build-Status
                "cci_14": studies["cci_14"],
                "cci_6_tcci": studies["cci_6_tcci"],
                "ema_34": studies["ema_34"],
                "lsma_value": studies["lsma_value"],
                "swi_value": studies["swi_value"],
                "czi_value": studies["czi_value"],
                "trend_state": studies["trend_state"],
                "trend_original": studies.get("trend_original"),  # D-WDIAG: A/B relabel
                "predictor_next_cci": studies["predictor_next_cci"],
                "signal": signal,
                "direction": direction,
                "strength": strength,
                "buffer_size": len(self._bar_buffer),
                "classification": classification,
                "active_patterns": [
                    {
                        "pattern_id": p.pattern_id,
                        "direction": p.direction,
                        "confidence": round(p.confidence, 3),
                        "group": p.group,
                        "entry_price": p.entry_price,
                        "stop": p.stop,
                        "targets": p.targets,
                    }
                    for p in patterns
                ],
                "decision_tree": dt_summary,
                "entry_classification_spec": dt_summary.get("entry_classification_spec"),
                "ready_to_route": dt_summary.get("ready_to_route", False),
                "failed_stages": dt_summary.get("failed_stages", []),
                "pending_stages": dt_summary.get("pending_stages", []),
            })

            # Prompt 14: auto-route to TradingGateway when ready
            if dt_summary.get("ready_to_route") and self._gateway and patterns:
                # best already set by W-8 dispatcher above
                # Dedup: same bar_ts + same pattern+direction = already fired this bar.
                # Sierra sends multiple UPDATE events per 5-min bar as it builds;
                # without this gate, each UPDATE fires a new SHADOW trade.
                _fire_key = f"{best.pattern_id}_{best.direction or 'LONG'}"
                _last_ts = self._last_fired_bar_ts.get(_fire_key, -1.0)
                if float(bar_ts) <= _last_ts:
                    logger.debug(
                        "[Woodies] Skipping duplicate fire: %s bar_ts=%s already fired",
                        _fire_key, bar_ts,
                    )
                    self.current_state["last_route"] = {
                        "skipped": True, "reason": "duplicate_bar_ts", "key": _fire_key,
                    }
                    return
                sizing = self.calculate_size(best.pattern_id, best.direction or "LONG")
                if sizing != "reject":
                    # Reuse fire_setup targets (already computed per spec above)
                    _gw_t1 = fire_setup["t1_price"] if fire_setup else (best.targets or [0])[0]
                    _gw_t2 = fire_setup.get("t2_price") if fire_setup else None
                    setup = {
                        "firing_system": 4,
                        "direction": best.direction or "LONG",
                        "classification": best.pattern_id,
                        "confidence": best.confidence,
                        "entry_price": best.entry_price,
                        "stop": best.stop or 0.0,
                        "t1": _gw_t1,
                        "t2": _gw_t2,
                        "t3": None,
                        "metadata": {"pattern": best.pattern_id, "sizing": sizing},
                    }
                    try:
                        route_result = self._gateway.route_setup(setup, 4)
                        self.current_state["last_route"] = route_result
                        if route_result.get("blocked_by"):
                            logger.warning(
                                "[Woodies] Gateway blocked: %s", route_result.get("blocked_by")
                            )
                        elif route_result.get("shadow"):
                            # Record bar_ts so duplicate UPDATE events on same bar are skipped.
                            self._last_fired_bar_ts[_fire_key] = float(bar_ts)
                            # W-10: track open fire for time stop enforcement
                            shadow_id = str(route_result["shadow"])
                            self._open_fire_records[shadow_id] = {
                                "entry_bar_count": self._bar_count,
                                "pattern_id": best.pattern_id,
                            }
                            logger.info(
                                "[Woodies] SHADOW recorded: %s %s size=%s id=%s bar_ts=%s",
                                best.pattern_id, best.direction, sizing,
                                route_result.get("shadow"), bar_ts,
                            )
                    except Exception as e:
                        self.current_state["last_route"] = {"error": str(e)}
                        logger.warning("[Woodies] Gateway route_setup failed: %s", e)
            else:
                if not dt_summary.get("ready_to_route"):
                    self.current_state["last_route"] = {
                        "skipped": True,
                        "reason": "not_ready_to_route",
                        "failed_stages": dt_summary.get("failed_stages", []),
                    }
                elif not self._gateway:
                    self.current_state["last_route"] = {"skipped": True, "reason": "no_gateway"}
                elif not patterns:
                    self.current_state["last_route"] = {"skipped": True, "reason": "no_patterns"}

            # W-10: time stop enforcement on all tracked open fires
            self._check_time_stops()

            # Persist patterns to DB (LIVE mode only)
            mode = getattr(event, 'mode', bar.get('mode', 'LIVE'))
            if mode == "LIVE":
                self._persist_bar(bar_ts, o, h, l, c, v, studies)
                for p in patterns:
                    self._persist_pattern(bar_ts, event, studies, p)

        except Exception as e:
            logger.error("[Woodies] process_bar error: %s", e, exc_info=True)

    def _persist_bar(self, ts, o, h, l, c, v, studies):
        """Write enriched bar to v9_bars_5min_woodies via safe_writer."""
        from backend.v9.db.safe_writer import safe_execute
        # Axis 6b fix: convert unix int to ISO timestamp (PG requires timestamp, not int)
        if ts and isinstance(ts, (int, float)):
            bar_ts = datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
        elif ts:
            bar_ts = str(ts)
        else:
            bar_ts = datetime.now(timezone.utc).isoformat()
        safe_execute(
            """INSERT OR REPLACE INTO v9_bars_5min_woodies
            (ts, symbol, open, high, low, close, volume,
             cci_14, cci_6_tcci, lsma_value, swi_value, czi_value,
             ema_34, trend_state, predictor_next_cci, zlr_detected, zlr_direction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                bar_ts, "MES",
                o, h, l, c, int(v),
                studies["cci_14"], studies["cci_6_tcci"],
                studies["lsma_value"], studies["swi_value"], studies["czi_value"],
                studies["ema_34"], studies["trend_state"], studies["predictor_next_cci"],
                0, "NONE",
            ),
        )

    def _persist_pattern(self, bar_ts, event, studies, pattern: PatternResult):
        """Write detected pattern to v9_woodies_signals via safe_writer."""
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
            """INSERT INTO v9_woodies_signals
            (ts, bar_id, cci_14, cci_prev, signal_type, direction, strength,
             reasoning, session, created_at,
             czi_state, swi_state, persistence_bars,
             signal_type_core, signal_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                None,
                studies["cci_14"],
                None,
                pattern.pattern_id,
                pattern.direction,
                int(pattern.confidence * 4),
                f"{pattern.pattern_id} {pattern.direction} conf={pattern.confidence:.2f} "
                f"CCI={studies['cci_14']:.1f} trend={studies['trend_state']}",
                getattr(event, 'session', 'UNKNOWN'),
                datetime.now(timezone.utc).isoformat(),
                "CZI" if abs(studies["cci_14"]) < 100 else "TREND_ZONE",
                "SWI" if abs(studies["cci_14"]) >= 200 else "NORMAL",
                len(self._bar_buffer),
                pattern.pattern_id,
                pattern.confidence,
            ),
        )
        logger.info(
            "[Woodies] Pattern %s %s fired: CCI=%.1f conf=%.2f trend=%s",
            pattern.pattern_id, pattern.direction,
            studies["cci_14"], pattern.confidence, studies["trend_state"],
        )

    def _check_time_stops(self) -> None:
        """W-10: Check all tracked open fires for time stop expiry.

        For each open fire, compute bars_open and check against limit.
        If fired: set exit_price = last close, then close via trade_manager.
        Idempotent: already-closed trades are removed silently.

        ──────────────────────────────────────────────────────────────────
        2026-05-28 evening · RE-ENABLED (Option B REVERSED · Michael).
        ──────────────────────────────────────────────────────────────────
        W-10 (Registry #11) is the SOLE TIME_STOP authority. Layer 4 time
        stop code removed from bar_level_detector.py. Bug A fixed: _bar_count
        increments only on new bar ts. Bug D fixed: exit_price set from
        self._closes[-1] before close_trade().
        """
        if not self._open_fire_records:
            return

        to_remove = []
        for trade_id, record in self._open_fire_records.items():
            bars_open = self._bar_count - record["entry_bar_count"]
            result = self._time_stop_enforcer.check(
                bars_open=bars_open,
                pattern_id=record["pattern_id"],
                trade_id=trade_id,
            )
            if result.fired:
                # Attempt close via gateway → trade_manager
                tm = getattr(self._gateway, '_trade_manager', None) if self._gateway else None

                if not self._closes:
                    logger.warning(
                        "[woodies] TIME_STOP fired but _closes is empty — skipping close "
                        "for trade %s (no exit_price available)", trade_id,
                    )
                    to_remove.append(trade_id)
                    continue

                if tm is not None:
                    try:
                        trade_obj = tm._get_trade(int(trade_id))
                        if trade_obj is not None:
                            trade_obj.exit_price = float(self._closes[-1])
                    except Exception as exc:
                        logger.warning(
                            "[woodies] TIME_STOP exit_price set failed for trade %s: %s",
                            trade_id, exc,
                        )
                        to_remove.append(trade_id)
                        continue

                    try:
                        tm.close_trade(int(trade_id), "TIME_STOP")
                        tm._db.commit()
                    except Exception as exc:
                        # Trade may already be closed (idempotent) or ID invalid
                        logger.debug(
                            "[woodies] TIME_STOP close_trade(%s) skipped: %s",
                            trade_id, exc,
                        )
                to_remove.append(trade_id)

        for tid in to_remove:
            del self._open_fire_records[tid]

    # Constitution V2 PART 6 — pattern tier map
    PATTERN_TIER = {
        'ZLR':   'high',    # Premier continuation
        'TT':    'high',    # Tony Trade
        'GB100': 'high',    # Deep pullback continuation
        'VEGAS': 'medium',  # Cup & Handle reversal
        'GHOST': 'medium',  # Head & Shoulders
        'FAMIR': 'medium',  # Failed ZLR (reversal)
        'HTLB':  'medium',  # Hooked TLB
        'TLB':   'low',     # Standalone = LOW per spec
    }

    def calculate_size(self, pattern_name: str, direction: str) -> str:
        """S4 per-system internal sizing. Cockpit V5 LOCKED + Constitution V2 PART 6.

        Uses ONLY S4 internal data: pattern tier + SWI/CZI/TCCI/LSMA/EMA34.
        NO cross-system inputs.

        Returns: 'full' (3 contracts) | 'half' (2) | 'reject'
        """
        base_tier = self.PATTERN_TIER.get(pattern_name, 'low')

        # Auxiliary alignment checks (direction-aware, from current studies)
        st = self.current_state
        cci_14 = st.get("cci_14") or 0
        tcci = st.get("cci_6_tcci") or 0
        swi = st.get("swi_value") or 0
        czi = st.get("czi_value") or 0
        lsma = st.get("lsma_value") or 0
        ema34 = st.get("ema_34") or 0
        last_close = self._closes[-1] if self._closes else 0

        is_long = direction == "LONG"

        # SWI aligned: positive for LONG, negative for SHORT
        swi_aligned = (swi > 0) if is_long else (swi < 0)

        # CZI aligned: positive for LONG, negative for SHORT
        czi_aligned = (czi > 0) if is_long else (czi < 0)

        # TCCI leads CCI14 in trade direction
        tcci_leading = (tcci > cci_14) if is_long else (tcci < cci_14)

        aux_count = sum([swi_aligned, czi_aligned, tcci_leading])

        # Trend context: LSMA + EMA34 alignment
        lsma_ok = (last_close > lsma) if is_long else (last_close < lsma)
        ema34_ok = (last_close > ema34) if is_long else (last_close < ema34)
        trend_ok = lsma_ok and ema34_ok

        # Decision tree
        if base_tier == 'high' and aux_count >= 3 and trend_ok:
            return 'full'    # 3 contracts — pristine setup
        elif base_tier in ('high', 'medium') and aux_count >= 2:
            return 'half'    # 2 contracts — solid
        elif base_tier == 'low':
            # TLB standalone = LOW — only allow with strong auxiliary
            return 'half' if aux_count >= 2 else 'reject'
        else:
            return 'reject'

    def get_current(self) -> dict:
        return dict(self.current_state)

    def get_layer4_context(self) -> dict:
        """Return Layer 4 context dict for TrailEngine._apply_layer4().

        Returns:
            {
                "swi": {"value": float, "color": str},
                "cci_history": List[float],   # CCI14 values, oldest first
                "direction_change_event": Optional[dict],
                "current_bar_ts": Optional[str],
            }
        """
        from backend.v9.systems.woodies.direction_change_detector import detect_from_buffer

        # SWI state from current_state
        swi_value = self.current_state.get("swi_value") or 0.0
        if swi_value > 0:
            swi_color = "green"
        elif swi_value < 0:
            swi_color = "red"
        else:
            swi_color = "gray"

        swi = {"value": swi_value, "color": swi_color}

        # CCI14 history from bar_buffer
        cci_history = [
            b.cci_14 if hasattr(b, "cci_14") else (b.get("cci_14") if isinstance(b, dict) else 0.0)
            for b in self._bar_buffer
        ]

        # Direction change from last 2 bars in buffer
        direction_change_event = detect_from_buffer(self._bar_buffer)

        # Current bar timestamp from last bar in buffer
        current_bar_ts: Optional[str] = None
        if self._bar_buffer:
            last = self._bar_buffer[-1]
            ts_val = last.ts if hasattr(last, "ts") else (last.get("ts") if isinstance(last, dict) else None)
            if ts_val is not None:
                current_bar_ts = str(ts_val)

        return {
            "swi": swi,
            "cci_history": cci_history,
            "direction_change_event": direction_change_event,
            "current_bar_ts": current_bar_ts,
        }
