"""System 4 — Woodies CCI Decision Maker (5-min bars + 9 patterns).

Subscribes to woodies_5min bars via BarRouter (D-074).
Computes all 11 Woodies studies per bar via cci_calc.compute_all_studies().
Runs 9-pattern engine (ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE).
Publishes signal events independently.
"""
import asyncio
import json
import logging
import os
import sqlite3
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
        loaded = 0
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT ?",
                (self.max_buffer,),
            ).fetchall()
            conn.close()

            # Reverse to oldest-first
            for row in reversed(rows):
                r = dict(row)
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
            if _bar_ts_key is not None and _bar_ts_key != self._last_bar_ts_for_count:
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
            self._bar_buffer.append(wb)
            if len(self._bar_buffer) > self.max_buffer:
                self._bar_buffer = self._bar_buffer[-self.max_buffer:]

            # Run 9-pattern engine — DLL flags as primary, Python detectors as fallback.
            # DLL computes on full Sierra history (thousands of bars) → more accurate
            # than 50-bar Python buffer. Michael approved 2026-06-01.
            patterns = detect_all_patterns(self._bar_buffer)

            # DLL-detected patterns: if DLL flags ZLR/HFE and Python missed it,
            # trust the DLL (source-of-truth per CLAUDE.md §Sierra real-time data).
            _dll_pattern_ids = {p.pattern_id for p in patterns}
            if wb.zlr_detected and "ZLR" not in _dll_pattern_ids:
                from backend.v9.systems.woodies.schemas import PatternResult
                _zlr_dir = "LONG" if wb.zlr_direction == "UP" else "SHORT" if wb.zlr_direction == "DOWN" else None
                if _zlr_dir:
                    patterns.append(PatternResult(
                        detected=True, pattern_id="ZLR", direction=_zlr_dir,
                        confidence=0.65, raw_confidence=0.65,
                        entry_price=wb.close, stop=None, targets=[],
                        group="CONTINUATION", cci_at_signal=wb.cci_14,
                        bar_index=len(self._bar_buffer) - 1, ts=wb.ts,
                        details={"source": "dll_flag", "zlr_direction": wb.zlr_direction},
                    ))
            if wb.hfe_detected and "HFE" not in _dll_pattern_ids:
                from backend.v9.systems.woodies.schemas import PatternResult
                _hfe_dir = "LONG" if wb.hfe_direction == "UP" else "SHORT" if wb.hfe_direction == "DOWN" else None
                if _hfe_dir:
                    patterns.append(PatternResult(
                        detected=True, pattern_id="HFE", direction=_hfe_dir,
                        confidence=0.60, raw_confidence=0.60,
                        entry_price=wb.close, stop=None, targets=[],
                        group="REVERSAL", cci_at_signal=wb.cci_14,
                        bar_index=len(self._bar_buffer) - 1, ts=wb.ts,
                        details={"source": "dll_flag", "hfe_direction": wb.hfe_direction,
                                 "hfe_extreme_bars_ago": wb.hfe_extreme_bars_ago},
                    ))

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
                # ζ.H1: reasoning_notes (AP-SY02)
                reasoning_notes = (f"{signal} {direction} size={sizing}: "
                                   f"CCI={studies['cci_14']:.1f}, trend={studies['trend_state']}, "
                                   f"conf={best.confidence:.2f}, group={best.group}")
                self.current_state["last_reasoning_notes"] = reasoning_notes

            fire_setup = None
            if patterns and direction and sizing != "reject":
                # best already set by W-8 dispatcher above
                if best.entry_price and best.stop and best.targets and len(best.targets) >= 2:
                    fire_setup = {
                        "direction": direction,
                        "entry_price": best.entry_price,
                        "stop_price": best.stop,
                        "t1_price": best.targets[0],
                        "t2_price": best.targets[1],
                        "time_stop_minutes": 90,
                        "confidence": int(best.confidence * 100),
                    }

            # P30: Skip sync HTTP touchpoint fetch — it self-deadlocks the
            # event loop (5 requests × 2s timeout to localhost:8000 which
            # can't respond because THIS handler is blocking it).
            # asyncio.to_thread didn't help: the thread's HTTP requests
            # still target the same single-worker uvicorn that's blocked.
            # Touchpoints are advisory-only (A4 stage) — empty dict is safe.
            # TODO: replace with in-process cache populated by a background task.

            dt_ctx = WoodiesDecisionContext(
                bars=list(self._bar_buffer),
                studies=studies,
                patterns=patterns,
                classification=classification,
                direction=direction,
                sizing=sizing,
                current_state=self.current_state,
                fire_setup=fire_setup,
                touchpoints={},
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
                    setup = {
                        "firing_system": 4,
                        "direction": best.direction or "LONG",
                        "classification": best.pattern_id,
                        "confidence": best.confidence,
                        "entry_price": best.entry_price,
                        "stop": best.stop or 0.0,
                        "t1": (best.targets or [0])[0] if best.targets else 0.0,
                        "t2": (best.targets or [0, 0])[1] if best.targets and len(best.targets) > 1 else 0.0,
                        "t3": (best.targets or [0, 0, 0])[2] if best.targets and len(best.targets) > 2 else 0.0,
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
        """Write enriched bar to v9_bars_5min_woodies.

        Uses the bar's actual timestamp (not current time) for UNIQUE dedup.
        INSERT OR REPLACE updates existing bars with newer study values.
        """
        bar_ts = str(ts) if ts else datetime.now(timezone.utc).isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
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
                    False, "NONE",
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("[Woodies] Bar persist failed: %s", e)

    def _persist_pattern(self, bar_ts, event, studies, pattern: PatternResult):
        """Write detected pattern to v9_woodies_signals."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
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
            conn.commit()
            conn.close()
            logger.info(
                "[Woodies] Pattern %s %s fired: CCI=%.1f conf=%.2f trend=%s",
                pattern.pattern_id, pattern.direction,
                studies["cci_14"], pattern.confidence, studies["trend_state"],
            )
        except Exception as e:
            logger.warning("[Woodies] Pattern persist failed: %s", e)

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
