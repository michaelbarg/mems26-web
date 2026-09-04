"""BarLevelDetector — glue between BarRouter and W11 TradeManager.

Subscribes to 5min bars via BarRouter. On each bar, iterates all active
(FILLED/PARTIAL) trades and checks if bar.high/low crossed any target or stop.
Calls existing TradeManager.on_target_hit() / on_stop_hit().

TIME_STOP exits are handled by W-10 (WoodiesSystem._check_time_stops),
not here. Layer 4 time stop code removed 2026-05-28 evening per Michael's
directive (Option B REVERSED — W-10 is sole TIME_STOP authority).

This is the CRITICAL missing piece that makes SHADOW trades close automatically.
"""

import logging
import time as _perf
from datetime import datetime, timezone
from typing import Optional

from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.trade_manager.state_machine import TradeState

logger = logging.getLogger(__name__)


class BarLevelDetector:
    """Per-bar hit detection for active trades.

    Subscribes to BarRouter '5min' channel. On each bar:
      1. Check stop (adverse fill priority)
      2. Check T1 → T2 → T3 sequentially
    """


    def __init__(self, trade_manager: TradeManager, gateway=None):
        self._tm = trade_manager
        self._gateway = gateway
        self._bars_processed = 0
        self._last_bar_ts_processed: str = ""  # dedup across 5min + woodies_5min
        self._eod_flatten_requested: set = set()  # trade ids already sent an EOD CANCEL
        # F5: one-shot honesty log — RUNNER_TRAIL_V1 is shadowed by DYNAMIC_STRUCT_TRAIL
        self._runner_trail_v1_shadow_warned: bool = False
        # T-252: in-code cost accounting, split shadow vs demo/live. The
        # BarRouter's SLOW-handler line only prints above 100ms and reports the
        # handler as a whole, so the log can neither give a real mean (the
        # distribution it shows is truncated) nor say which mode paid. Read via
        # get_stats() / GET /api/v9/system6/diagnose.
        self._mode_secs = {"shadow": 0.0, "live": 0.0}
        self._mode_trades = {"shadow": 0, "live": 0}
        self._loop_ms_total: float = 0.0
        self._loop_ms_max: float = 0.0
        self._loop_bars: int = 0
        self._open_by_mode: dict = {"shadow": 0, "live": 0}
        # T-255: corrections whose op has no executor here — announced once per
        # (trade, op, target), counted always, so suppression is not silence.
        self._unexec_ops: set = set()
        self._unexec_count: int = 0

    def _trade_still_open(self, trade_id: int) -> bool:
        """T4 helper: is this trade still active in the books?

        Used by the exit verifier so a close that arrives from another correct
        path (POSITION_TRUTH_SYNC 'SIERRA_FLAT', a Sierra stop fill, a manual
        close) retires the pending instead of being closed a second time.
        """
        try:
            return any(int(getattr(t, "id", -1)) == int(trade_id)
                       for t in self._tm.get_active_trades())
        except Exception:
            return True  # unknown -> keep verifying (safe side)

    def set_gateway(self, gateway) -> None:
        """Inject gateway for demo slot release on trade close."""
        self._gateway = gateway

    def subscribe(self, bar_router) -> None:
        """Register with BarRouter for 5min + woodies_5min bar events."""
        bar_router.subscribe("5min", self.on_bar)
        bar_router.subscribe("woodies_5min", self.on_bar)
        logger.info("[BarLevelDetector] subscribed to 5min + woodies_5min via BarRouter")

    def _system6_scan(self, trade, reconcile_verdict=None) -> None:
        """System 6 advisory supervision on the active demo/live trade.

        Runs every bar (Michael 2026-07-05: "scan every cycle, diagnose, correct").
        Flag-gated by SYSTEM6_SUPERVISOR (default OFF) → fully inert until enabled,
        so it adds one env check when off and cannot touch today's trade. When ON it
        LOGS the 9-invariant diagnosis (naked/wrong-side/BE-after-T1/target-side/band/
        T1-worth/size/EOD/reconcile) and only APPLIES fixes when SYSTEM6_AUTOCORRECT=1
        (never today). Fail-safe: any error is swallowed so trade management continues.
        Spec: docs/handoff/CC_POSTTRADE_SYSTEM6_2026-07-07.md (P2.4).
        """
        import os as _s6_os
        if _s6_os.getenv("SYSTEM6_SUPERVISOR", "0").lower() not in ("1", "true", "yes"):
            return
        try:
            from backend.v9.systems.system6_supervisor import scan_active_trade

            # expected contract count — mirror the sizing choke-point precedence
            # One resolver (2026-08-16) — a stale ladder here made System 6
            # raise a false "contracts != expected" on every scan of a
            # correctly-sized trade.
            from backend.v9.services.contract_size import ruled_contracts as _ruled
            _exp = _ruled()

            # current Chicago-time minute drives the EOD-flatten invariant (14:15 CT)
            _now_ct = None
            try:
                from zoneinfo import ZoneInfo
                _ct = datetime.now(ZoneInfo("America/Chicago"))
                _now_ct = _ct.hour * 60 + _ct.minute
            except Exception:
                _now_ct = None

            _t = {
                "direction": getattr(trade, "direction", None),
                "entry_price": getattr(trade, "entry_price", None),
                "stop": getattr(trade, "stop", None),
                "t1": getattr(trade, "t1", None),
                "t2": getattr(trade, "t2", None),
                "t3": getattr(trade, "t3", None),
                "contracts": getattr(trade, "contracts", None),
            }

            def _exec(correction) -> bool:
                # Only invoked when SYSTEM6_AUTOCORRECT=1 (off today). Reuses the
                # existing MODIFY plumbing — System 6 never writes to Sierra directly.
                op = (correction or {}).get("op")
                if op == "MODIFY_STOP":
                    self._tm._emit_modify_stop(trade, float(correction["price"]))
                    return True
                if op == "DROP_TARGET":
                    # N4 (2026-07-17): was advisory-only (CLAUDE.md: "not wired") even
                    # though protective mode already covers it — completes the wiring.
                    return self._tm._emit_drop_target(trade, correction.get("target"))
                # T-255 (2026-09-04): this ran on every scan of every bar and
                # produced 47,772 identical WARNINGs. "This correction class has
                # no executor" is a fact about the CODE, not an event — it needs
                # saying once per (trade, op, target), not once per bar. Second
                # line of defence: the AUTO/ALERT tier at the source is what
                # decides whether _exec sees this op at all (see
                # system6_supervisor invariant-10).
                _k = (getattr(trade, "id", None), op,
                      (correction or {}).get("target"))
                if _k not in self._unexec_ops:
                    self._unexec_ops.add(_k)
                    logger.warning(
                        "[System6] correction %s has no executor here — advisory "
                        "only (trade %s, target %s). Further identical "
                        "corrections on this trade are not repeated.",
                        op, _k[0], _k[2])
                self._unexec_count += 1
                return False

            # Feed the live reconcile truth in — this is what makes System 6 catch a
            # phantom (DB open / Sierra flat, e.g. the SIM_TEST trade 297): reconcile says
            # MISMATCH → System 6 raises a CRITICAL reconcile_mismatch on the "active" trade.
            _rv = reconcile_verdict
            _mismatch = bool(getattr(_rv, "mismatch", False)) if _rv is not None else False
            _verdict_str = getattr(_rv, "verdict", None) if _rv is not None else None

            # 2026-08-16 — was `atr=0.0` with a TODO. That zero is not neutral:
            # diagnose_trade falls back to floor=1.0 / cap=25.0, and on 08-14's
            # real RTH ATR of 3.78 the correct band is 1.89 / 5.66. So
            # `stop_too_wide` could effectively never fire (25pt), and
            # `stop_too_tight` + `t1_too_close` — Michael's own "a T1 this close
            # to entry is worth nothing" rule — were filtered against a floor
            # 47% too low. The /s6/diagnose endpoint already computed a real ATR,
            # so the panel and the live loop were diagnosing the same trade
            # differently. Same 14-bar TR average, read from the canonical table.
            _atr_live = 0.0
            try:
                from backend.v9.db.read import read_all as _s6_read
                _ab = _s6_read(
                    "SELECT high, low, close FROM v9_bars_5min_woodies "
                    "WHERE symbol='MES' ORDER BY ts DESC LIMIT 14", {}) or []
                _ab = list(reversed(_ab))
                _trs, _prev = [], None
                for _b in _ab:
                    _h, _l, _c = float(_b["high"]), float(_b["low"]), float(_b["close"])
                    _trs.append(_h - _l if _prev is None
                                else max(_h - _l, abs(_h - _prev), abs(_l - _prev)))
                    _prev = _c
                _atr_live = (sum(_trs) / len(_trs)) if _trs else 0.0
            except Exception:
                _atr_live = 0.0   # honest zero → the documented safe fallback

            # ── B1 (2026-08-17): wire rescue-tier inputs for invariants 9-13 ──
            # All ALERT-only — supplying data so dormant invariants can fire
            # and generate evidence. No execution behavior changes.
            _s6_bars_since = None
            _s6_progress = None
            _s6_counter_pre_t1 = False
            _s6_runner_rev = False
            _s6_cvd_rev = False

            _s6_entry_ts = getattr(trade, "entry_ts", None)
            _s6_t1_hit = getattr(trade, "t1_hit_ts", None) is not None
            _s6_dir = str(getattr(trade, "direction", "")).upper()
            _s6_ep = getattr(trade, "entry_price", None)

            try:
                if _s6_entry_ts and _s6_ep:
                    # inv-10: bars_since_entry — completed bars after entry
                    _cnt = _s6_read(
                        "SELECT COUNT(*) as cnt FROM v9_bars_5min_woodies "
                        "WHERE ts > :ets AND symbol = 'MES'",
                        {"ets": str(_s6_entry_ts)})
                    if _cnt:
                        _s6_bars_since = int(_cnt[0]["cnt"])

                    # inv-10: progress_pts — favorable move (last close vs entry)
                    _lc_row = _s6_read(
                        "SELECT close FROM v9_bars_5min_woodies "
                        "WHERE symbol = 'MES' ORDER BY ts DESC LIMIT 1", {})
                    if _lc_row:
                        _lc = float(_lc_row[0]["close"])
                        _s6_progress = ((_lc - float(_s6_ep)) if _s6_dir == "LONG"
                                        else (float(_s6_ep) - _lc))
            except Exception:
                pass

            # inv-9: counter_signal_pre_t1 — opposite S2 fire since entry
            try:
                if _s6_entry_ts and not _s6_t1_hit:
                    _opp_dir = "SHORT" if _s6_dir == "LONG" else "LONG"
                    _opp = _s6_read(
                        "SELECT direction FROM v9_five_min_setups "
                        "WHERE created_at > :ets "
                        "ORDER BY created_at DESC LIMIT 5",
                        {"ets": str(_s6_entry_ts)})
                    if _opp:
                        _s6_counter_pre_t1 = any(
                            str(r.get("direction", "")).upper() == _opp_dir
                            for r in _opp)
            except Exception:
                pass

            # inv-11: runner_reversal — ≥2 consecutive adverse closes after T1
            try:
                if _s6_t1_hit:
                    _rc = _s6_read(
                        "SELECT close FROM v9_bars_5min_woodies "
                        "WHERE symbol = 'MES' ORDER BY ts DESC LIMIT 4", {})
                    _closes = [float(r["close"]) for r in _rc][::-1]
                    if len(_closes) >= 3:
                        _adv = 0
                        for _ci in range(1, len(_closes)):
                            if ((_s6_dir == "LONG" and _closes[_ci] < _closes[_ci - 1])
                                    or (_s6_dir == "SHORT" and _closes[_ci] > _closes[_ci - 1])):
                                _adv += 1
                            else:
                                _adv = 0
                        _s6_runner_rev = _adv >= 2
            except Exception:
                pass

            # inv-12: cvd_reversal — CVD flip + ≥2 adverse closes after T1
            try:
                if _s6_t1_hit:
                    _cvd_rows = _s6_read(
                        "SELECT cumulative FROM v9_bars_cumulative_delta "
                        "ORDER BY ts::timestamptz DESC LIMIT 6", {})
                    _cvd_vals = [float(r["cumulative"]) for r in _cvd_rows
                                 if r.get("cumulative") is not None][::-1]
                    if len(_cvd_vals) >= 3:
                        _slope = _cvd_vals[-1] - _cvd_vals[-3]
                        _against = ((_s6_dir == "LONG" and _slope < 0)
                                    or (_s6_dir == "SHORT" and _slope > 0))
                        _s6_cvd_rev = _against and _s6_runner_rev
            except Exception:
                pass

            # inv-13: sierra_targets — from in-memory PLACE cache (honest None
            # on restart per Rule 1; persistent tracking is B3/DLL territory)
            try:
                _s6_tid = getattr(trade, "id", None)
                if _s6_tid:
                    from backend.v9.services.sierra_command import get_last_place_command
                    _place = get_last_place_command(_s6_tid)
                    if _place:
                        _st = {}
                        if _place.get("target_price") is not None:
                            _st["t1"] = float(_place["target_price"])
                        _ctx = _place.get("context") or {}
                        for _tk in ("t2", "t3", "t4"):
                            if _ctx.get(_tk) is not None:
                                _st[_tk] = float(_ctx[_tk])
                        if _st:
                            _t["sierra_targets"] = _st
            except Exception:
                pass

            scan_active_trade(
                trade=_t,
                atr=_atr_live,
                t1_hit=getattr(trade, "t1_hit_ts", None) is not None,
                expected_contracts=_exp,
                now_ct_min=_now_ct,
                reconcile_verdict=_verdict_str,
                reconcile_mismatch=_mismatch,
                executor=_exec,
                # B1 rescue-tier inputs (2026-08-17)
                counter_signal_pre_t1=_s6_counter_pre_t1,
                bars_since_entry=_s6_bars_since,
                progress_pts=_s6_progress,
                runner_reversal=_s6_runner_rev,
                cvd_reversal=_s6_cvd_rev,
            )
        except Exception as _s6_err:  # never let supervision break trade management
            logger.warning("[BarLevelDetector] System6 scan error (fail-safe skip): %s", _s6_err)

    def _system6_journal_autoloop(self, trade, bar_ts_key: str) -> None:
        """W9 (2026-07-25): background journal of S6 exit/hold signals per bar.

        On every 5-min bar, for each open demo/live trade, evaluate all 8
        exit/hold signals and write each to v9_exit_decisions. This fills the
        journal that was empty (0 rows) because writes only happened when a
        user opened the S6 panel in the browser.

        Advisory only — ZERO impact on trading. Never calls write_exit or
        MODIFY. Flag-gated: SYSTEM6_JOURNAL_AUTOLOOP_V1 (default OFF).
        Dedup: one row per (trade_id, signal_kind) per bar_ts_key.
        Fail-safe: any error swallowed.
        """
        import os as _jl_os
        if _jl_os.getenv("SYSTEM6_JOURNAL_AUTOLOOP_V1", "0").lower() not in (
            "1", "true", "yes",
        ):
            return
        # Dedup: skip if we already journalled this trade×bar
        _dedup_key = f"{getattr(trade, 'id', 0)}_{bar_ts_key}"
        if not hasattr(self, "_journal_seen"):
            self._journal_seen: set = set()
        if _dedup_key in self._journal_seen:
            return
        self._journal_seen.add(_dedup_key)
        # Cap the seen-set to prevent unbounded growth
        if len(self._journal_seen) > 500:
            self._journal_seen = set(list(self._journal_seen)[-200:])

        try:
            from backend.v9.systems.system6_journal import (
                record, build_record, enabled as _journal_enabled,
            )
            if not _journal_enabled():
                return

            from backend.v9.systems.system6_exit_signals import (
                hold_confirmation, price_stall, opposite_patterns,
                counter_flow_wins, cvd_divergence,
                failed_reaction_volume, pattern_intact, trend_continues,
            )

            trade_id = getattr(trade, "id", None)
            if trade_id is None:
                return
            direction = str(getattr(trade, "direction", "LONG")).upper()
            entry = getattr(trade, "entry_price", None)
            stop = getattr(trade, "stop", None)
            t1 = getattr(trade, "t1", None)

            # Fetch recent bars for signals
            try:
                from backend.v9.db.read import read_all
                _rows = read_all(
                    "SELECT high, low, close FROM v9_bars_5min_woodies "
                    "ORDER BY ts DESC LIMIT 12", {},
                )
                bars = [{"high": float(r["high"]), "low": float(r["low"]),
                         "close": float(r["close"])} for r in _rows][::-1]
            except Exception:
                bars = []

            if not bars or entry is None:
                return

            # Evaluate all signals
            signals = []

            # 1. price_stall
            signals.append(price_stall(direction=direction, bars=bars))

            # 2. opposite_patterns
            try:
                _fr = read_all(
                    "SELECT direction FROM v9_trades WHERE entry_ts >= "
                    "(now() - interval '30 minutes') ORDER BY entry_ts", {},
                )
                _dirs = [str(r["direction"]) for r in _fr]
            except Exception:
                _dirs = []
            signals.append(opposite_patterns(
                trade_direction=direction, recent_fire_directions=_dirs))

            # 3. counter_flow_wins + 4. cvd_divergence (CVD-based)
            try:
                _cv = read_all(
                    "SELECT cumulative FROM v9_bars_cumulative_delta "
                    "ORDER BY ts::timestamptz DESC LIMIT 6", {},
                )
                _cvd = [float(r["cumulative"]) for r in _cv
                        if r["cumulative"] is not None][::-1]
            except Exception:
                _cvd = []
            if len(_cvd) >= 3:
                signals.append(counter_flow_wins(
                    direction=direction, cvd_series=_cvd))
                signals.append(cvd_divergence(
                    direction=direction, bars=bars[-len(_cvd):], cvd_series=_cvd))

            # 5. failed_reaction_volume (use T1 as the expected level)
            _last_price = bars[-1].get("close") if bars else None
            signals.append(failed_reaction_volume(
                direction=direction,
                price=float(_last_price) if _last_price else 0.0,
                level=float(t1) if t1 else None,
                level_tol=5.0,
                flow_aligned=None,  # no live flow data outside the CVD path
            ))

            # 6. hold_confirmation (includes pattern_intact + trend_continues)
            _hold = hold_confirmation(
                direction=direction,
                invalidation_level=float(stop) if stop else None,
                bars=bars,
            )
            # Decompose hold into individual signal records
            _last_close = bars[-1].get("close") if bars else None
            _intact = pattern_intact(
                direction=direction,
                invalidation_level=float(stop) if stop else None,
                last_close=float(_last_close) if _last_close else None,
            )
            _tc = trend_continues(direction=direction, bars=bars)

            # Determine recommendation from hold gate
            fired = [s for s in signals if s.fired]
            if _hold.broke:
                rec = "exit"
            elif _hold.continuing:
                rec = "hold"
            elif fired:
                rec = "consider_exit"
            else:
                rec = "hold"

            # Write exit signal rows
            _ctx_base = {
                "entry": entry, "stop": stop,
                "hold_intact": _hold.intact, "hold_continuing": _hold.continuing,
                "bar_ts": bar_ts_key,
            }
            for s in signals:
                record(build_record(
                    trade_id=int(trade_id),
                    signal_kind=s.kind,
                    score=s.score,
                    fired=s.fired,
                    recommendation=rec,
                    context={"reason": s.reason, **_ctx_base},
                    decision="OBSERVED",
                    decided_by="auto_loop",
                ))

            # Write hold-side records
            record(build_record(
                trade_id=int(trade_id),
                signal_kind="pattern_intact",
                score=1.0 if _intact else 0.0,
                fired=not _intact,
                recommendation=rec,
                context={"intact": _intact, **_ctx_base},
                decision="OBSERVED",
                decided_by="auto_loop",
            ))
            record(build_record(
                trade_id=int(trade_id),
                signal_kind="trend_continues",
                score=_tc.score,
                fired=_tc.broke,
                recommendation=rec,
                context={"continuing": _tc.continuing, "reason": _tc.reason,
                         **_ctx_base},
                decision="OBSERVED",
                decided_by="auto_loop",
            ))
            record(build_record(
                trade_id=int(trade_id),
                signal_kind="hold_confirmation",
                score=_hold.score,
                fired=_hold.broke,
                recommendation=rec,
                context={"intact": _hold.intact, "continuing": _hold.continuing,
                         "reason": _hold.reason, **_ctx_base},
                decision="OBSERVED",
                decided_by="auto_loop",
            ))

            logger.debug(
                "[BarLevelDetector] W9 journal: trade %d, %d signals written (bar=%s)",
                trade_id, len(signals) + 3, bar_ts_key,
            )
        except Exception as _jl_err:
            logger.warning(
                "[BarLevelDetector] W9 journal autoloop error (fail-safe): %s", _jl_err)

    def _system0_shadow_log(self, bar_ts_key: str) -> None:
        """System 0 Phase A3: shadow direction authority log (2026-07-29).

        Compares what MarketContext.day_bias would say as the SINGLE direction
        authority vs what the current scattered getters produce. Shadow only —
        ZERO live behavior change. Logs the comparison for calibration.

        Flag: MARKET_CONTEXT_V1 (must be ON to have a context to compare).
        Rate-limited: once per 5 bars (~25 min) to avoid log flood.
        """
        import os as _s0_os
        if _s0_os.getenv("MARKET_CONTEXT_V1", "0").lower() not in ("1", "true", "yes"):
            return
        # Rate-limit: once per 5 bars
        _count = getattr(self, "_s0_bar_count", 0) + 1
        self._s0_bar_count = _count
        if _count % 5 != 1:
            return
        try:
            from backend.v9.services.market_context import get_market_context
            ctx = get_market_context()

            # Compare to scattered getters
            _scatter = {}
            try:
                from backend.v9.services.trade_context import get_live_expansion
                _exp = get_live_expansion()
                _scatter["expansion"] = _exp.get("dir") if _exp else None
            except Exception:
                _scatter["expansion"] = None
            try:
                from backend.v9.services.trade_context import get_live_dir_bias
                _scatter["dir_bias"] = get_live_dir_bias()
            except Exception:
                _scatter["dir_bias"] = None
            try:
                from backend.v9.services.trade_context import get_opening_type_seed
                _scatter["opening_seed"] = get_opening_type_seed()
            except Exception:
                _scatter["opening_seed"] = None

            _agree = ctx.day_bias == (_scatter.get("expansion") or
                                      _scatter.get("dir_bias") or
                                      _scatter.get("opening_seed") or "NONE")

            logger.info(
                "[System0] SHADOW DIR: context.day_bias=%s | scattered: "
                "expansion=%s dir_bias=%s seed=%s | agree=%s | "
                "opening=%s(%s,%.2f) day_type=%s balance=%s bar=%s",
                ctx.day_bias,
                _scatter.get("expansion"), _scatter.get("dir_bias"),
                _scatter.get("opening_seed"),
                _agree,
                ctx.opening_type, ctx.opening_dir, ctx.opening_conf,
                ctx.day_type, ctx.balance_state, bar_ts_key,
            )
        except Exception as _s0_err:
            logger.debug("[System0] shadow log error (fail-safe): %s", _s0_err)

    def _eod_close_t10(self, active) -> None:
        """T-10: close open positions 10 min before RTH close (+$3.28/day measured).

        EOD_CLOSE_T10_V1 (default OFF). Uses FLATTEN_ACCOUNT (not op=EXIT which
        is broken). Fires at 15:50 ET (10 min before 16:00 close).
        """
        import os as _t10_os
        if _t10_os.getenv("EOD_CLOSE_T10_V1", "0").lower() not in ("1", "true", "yes"):
            return
        try:
            from zoneinfo import ZoneInfo
            et_now = datetime.now(ZoneInfo("America/New_York"))
            et_time = et_now.time()
            # 15:50 ET = 10 min before RTH close
            from datetime import time as _t
            if et_time < _t(15, 50) or et_time >= _t(16, 0):
                return
            # Only flatten if there are active demo/live trades
            live_active = [t for t in (active or [])
                          if getattr(t, "mode", "shadow") in ("demo", "live")]
            if not live_active:
                return
            from backend.v9.services.sierra_command import write_flatten_account
            for trade in live_active:
                if trade.id in self._eod_flatten_requested:
                    continue
                write_flatten_account(
                    trade_id=str(trade.id),
                    source="eod_close_t10",
                    reason=f"T-10: 10 min before RTH close ({et_time.strftime('%H:%M')} ET)")
                self._eod_flatten_requested.add(trade.id)
                logger.warning(
                    "[T-10] EOD CLOSE at %s ET: FLATTEN for %s trade %d",
                    et_time.strftime("%H:%M"), getattr(trade, "mode", "?"), trade.id)
        except Exception as _t10_err:
            logger.warning("[T-10] EOD close error (fail-safe): %s", _t10_err)

    def _eod_flatten(self, active) -> None:
        """Auto-flatten open demo/live positions at RTH close (Michael 2026-07-07).

        Closes the gap where `B2EodCheck` evaluates CLOSE_ALL at ≥15:59 ET but NOTHING
        consumes it (verified: only tests reference B2). Wires B2 → the existing CANCEL op
        (DLL FlattenAndCancelAllOrders). Flag-gated EOD_FLATTEN_V1 (default OFF) → build now,
        enable after the ground-truth test (force clock past 15:59 ET → Sierra flat + close).

        I-62 SAFETY: for demo/live we send CANCEL and let FillPoller close the TM trade on the
        Sierra flat FILL — we do NOT mark CLOSED here (marking flat before Sierra confirms is the
        exact 07-03 orphan I-62 forbids). Idempotent: one CANCEL per trade (tracked). Fail-safe.
        Spec: docs/handoff/CC_POSTTRADE_SYSTEM6_2026-07-07.md (P1.1).
        """
        import os as _eod_os
        if _eod_os.getenv("EOD_FLATTEN_V1", "0").lower() not in ("1", "true", "yes"):
            return
        try:
            from zoneinfo import ZoneInfo
            from backend.v9.systems.woodies.stages.b2_eod_check import B2EodCheck

            et = datetime.now(ZoneInfo("America/New_York")).strftime("%H:%M")
            if B2EodCheck().evaluate(et).action != "CLOSE_ALL":
                return

            from backend.v9.services.sierra_command import write_cancel
            for trade in active or []:
                mode = getattr(trade, "mode", "shadow")
                if mode not in ("demo", "live"):
                    continue  # shadow has no Sierra position to flatten
                if trade.id in self._eod_flatten_requested:
                    continue  # already sent — don't spam CANCEL every bar
                oid = None
                if hasattr(self._tm, "_get_sierra_order_id"):
                    try:
                        oid = self._tm._get_sierra_order_id(trade)
                    except Exception:
                        oid = None
                write_cancel(trade_id=str(trade.id), order_id=oid, mode=mode)
                self._eod_flatten_requested.add(trade.id)
                logger.warning(
                    "[BarLevelDetector] EOD FLATTEN (RTH close, %s ET): CANCEL sent for %s "
                    "trade %d — awaiting Sierra flat fill (I-62: FillPoller closes it)",
                    et, mode, trade.id,
                )
        except Exception as _eod_err:  # never let flatten break trade management
            logger.warning("[BarLevelDetector] EOD flatten error (fail-safe skip): %s", _eod_err)

    def _trend_runner_flatten(self, active) -> None:
        """C4 ruling-6 (Michael 2026-07-21): on Trend days, flatten runners at 15:45 ET.

        "ביום טרנדי ממשיך עד 15 דק' לפני סגירת השוק" → 16:00 close − 15min = 15:45.
        Same pattern as _eod_flatten: send CANCEL, let FillPoller close on Sierra fill.
        Only for Trend days (Trend_Normal / Trend_DD). Flag: C4_TREND_FLATTEN_V1 (default OFF).
        """
        import os as _tf_os
        if _tf_os.getenv("C4_TREND_FLATTEN_V1", "0").lower() not in ("1", "true", "yes"):
            return
        try:
            from zoneinfo import ZoneInfo
            _now = datetime.now(ZoneInfo("America/New_York"))
            _h, _m = _now.hour, _now.minute
            # 15:45 ET = flatten time for Trend runners
            if _h < 15 or (_h == 15 and _m < 45):
                return  # before 15:45

            # Check day-type: only on Trend days
            try:
                from backend.v9.services.trade_context import get_live_day_type
                _dt = get_live_day_type() or ""
            except Exception:
                _dt = ""
            if not _dt.startswith("Trend"):
                return

            from backend.v9.services.sierra_command import write_cancel
            for trade in active or []:
                mode = getattr(trade, "mode", "shadow")
                if mode not in ("demo", "live"):
                    continue
                if trade.id in self._eod_flatten_requested:
                    continue  # already handled by EOD or prior trend-flatten
                oid = None
                if hasattr(self._tm, "_get_sierra_order_id"):
                    try:
                        oid = self._tm._get_sierra_order_id(trade)
                    except Exception:
                        oid = None
                write_cancel(trade_id=str(trade.id), order_id=oid, mode=mode)
                self._eod_flatten_requested.add(trade.id)
                logger.warning(
                    "[BarLevelDetector] TREND FLATTEN (15:45 ET, %s): CANCEL sent for %s "
                    "trade %d — Trend runner cutoff per ruling-6",
                    _now.strftime("%H:%M"), mode, trade.id,
                )
        except Exception as _tf_err:
            logger.warning("[BarLevelDetector] Trend flatten error (fail-safe skip): %s", _tf_err)

    def _reconcile_live(self):
        """P1.3 — run the item-20 reconcile every bar while a slot is active, so a
        slot↔DB↔Sierra/TM disagreement (orphan / naked-stop / phantom-slot) surfaces LIVE
        instead of post-mortem (the 06-25 + 07-03 incidents). The reconcile verdict function
        already handles live_slot; the gap was that NOTHING called it — this wires it in.

        Flag-gated RECONCILE_LIVE_V1 (default OFF) → build now, enable after the ground-truth
        MATCH test. Fail-safe. Only runs when we believe we hold a position (slot occupied),
        and escalates a real mismatch to CRITICAL so Michael sees it. Returns the verdict so
        System 6 can fold the DB↔Sierra truth into its per-bar diagnosis (else None).
        Spec: docs/handoff/CC_POSTTRADE_SYSTEM6_2026-07-07.md (P1.3).
        """
        import os as _rc_os
        if _rc_os.getenv("RECONCILE_LIVE_V1", "0").lower() not in ("1", "true", "yes"):
            return None
        gw = self._gateway
        if gw is None:
            return None
        if not (getattr(gw, "demo_slot", None) or getattr(gw, "live_slot", None)):
            return None  # flat by belief — nothing to reconcile
        try:
            from backend.v9.services.reconcile import gather_and_reconcile
            v = gather_and_reconcile(gateway=gw)
            # 2026-08-19 (false-alarm fix): require 2 CONSECUTIVE naked verdicts
            # before CRITICAL + phone (same discipline as PROTECTED_QTY_GUARD_V1).
            # A single-check naked verdict during a transient (scratch-flatten
            # race, ACK rollover) alarmed Michael on protected trades all evening.
            _naked = bool(getattr(v, "naked_stop_suspect", False))
            self._naked_streak = (getattr(self, "_naked_streak", 0) + 1) if _naked else 0
            _naked_confirmed = _naked and self._naked_streak >= 2
            if getattr(v, "mismatch", False) or _naked_confirmed:
                logger.critical("[Reconcile-live] %s — %s", v.verdict, getattr(v, "detail", ""))
                # W3 (2026-07-25): immediate phone escalation — not just a log line.
                # A naked stop is a live-risk event (position without protection).
                if _naked_confirmed:
                    try:
                        from backend.v9.services.phone_alert import push as _pp
                        _pp("naked_stop_reconcile",
                            "\U0001f534 MEMS26: NAKED STOP SUSPECT",
                            f"Reconcile-live: {getattr(v, 'detail', 'stop not confirmed')}",
                            priority=1)
                    except Exception:
                        pass
            elif _naked:
                logger.warning("[Reconcile-live] NAKED_STOP_SUSPECT 1/2 — pending "
                               "second consecutive check before alarm (%s)",
                               getattr(v, "detail", ""))
            return v
        except Exception as _rc_err:  # never let reconcile break trade management
            logger.warning("[BarLevelDetector] reconcile-live error (fail-safe skip): %s", _rc_err)
            return None

    def _check_stuck_live_slot(self):
        """T-183 — alarm when the live slot blocks fires while holding nothing.

        Root-cause-INDEPENDENT: it does not care WHY the slot was not released
        (I-57 cockpit-exit path, T-178 books-closed-in-DB path, or the next
        variant). It asks only whether the slot is held by a trade that is not
        among the open live/demo trades, for longer than the threshold.

        Why this is not covered by _reconcile_live: MISMATCH_PHANTOM_SLOT needs
        `db_open` false, but its query has no mode filter — the shadow trades
        firing all evening on 08-31 kept it True, so the phantom branch never
        ran and 403 CRITICAL "NAKED_STOP_SUSPECT — in position" lines were
        emitted instead, claiming the opposite of the truth.

        ALERT-ONLY: logs, never releases the slot, never writes, never touches
        the execution path. Rate-limited so a stuck slot does not spam the log
        the way the naked-stop check did (403 lines in one evening).
        """
        import os as _ss_os
        if _ss_os.getenv("STUCK_SLOT_ALARM_V1", "1").lower() not in ("1", "true", "yes"):
            return None
        try:
            import time as _ss_t
            from backend.v9.services.reconcile import gather_stuck_slot

            st = gather_stuck_slot(self._gateway, getattr(self, "_stuck_slot_since", None))
            self._stuck_slot_since = st.stuck_since  # None when healthy → auto-reset
            self._last_stuck_slot = st

            if not st.alarm:
                return st
            # rate-limit: one line per 5 min while the condition persists
            _last = getattr(self, "_stuck_slot_logged_at", 0.0)
            if _ss_t.time() - _last >= 300.0:
                self._stuck_slot_logged_at = _ss_t.time()
                logger.warning("[StuckSlot] %s", st.detail)
            return st
        except Exception as _ss_err:  # never let an alarm break trade management
            logger.warning("[BarLevelDetector] stuck-slot check error (fail-safe skip): %s",
                           _ss_err)
            return None

    async def on_bar(self, event) -> None:
        """Process a 5-min bar: check all active trades for hits."""
        try:
            bar = event.payload if hasattr(event, "payload") else event
            if isinstance(bar, dict):
                bar_data = bar
            else:
                bar_data = dict(bar)

            bar_high = float(bar_data.get("high", bar_data.get("h", 0)))
            bar_low = float(bar_data.get("low", bar_data.get("l", 0)))
            bar_ts_raw = bar_data.get("ts", "")

            # Parse bar timestamp
            bar_ts = self._parse_ts(bar_ts_raw)

            # Dedup: same bar_ts from both 5min and woodies_5min channels
            _ts_key = str(bar_ts_raw)[:16]  # floor to minute
            if _ts_key == self._last_bar_ts_processed and _ts_key:
                return
            self._last_bar_ts_processed = _ts_key

            mode = getattr(event, "mode", "LIVE")
            if mode != "LIVE":
                return

            self._bars_processed += 1
            active = self._tm.get_active_trades()

            # T-10: EOD close 10 min before RTH close (flag-gated, default OFF).
            # +$3.28/day measured. FLATTEN only (op=EXIT broken).
            self._eod_close_t10(active)
            # Trend runner flatten at 15:45 ET (flag-gated C4_TREND_FLATTEN_V1, OFF).
            self._trend_runner_flatten(active)
            # EOD auto-flatten at RTH close (flag-gated EOD_FLATTEN_V1, default OFF).
            self._eod_flatten(active)
            # Reconcile slot↔DB↔Sierra while in a position (flag-gated RECONCILE_LIVE_V1, OFF).
            # Capture the verdict so System 6 folds the DB↔Sierra truth into its diagnosis.
            _recon_v = self._reconcile_live()
            # T-183: stuck live slot = live path blocked SILENTLY. Runs
            # unconditionally (not behind RECONCILE_LIVE_V1) and independently of
            # the reconcile verdict, because the 08-31 blackout happened WITH
            # reconcile on — it just answered the wrong question. Alert-only.
            self._check_stuck_live_slot()

            # System 0 A3: shadow direction authority log (flag-gated, advisory)
            self._system0_shadow_log(_ts_key)

            # Day-type writer watchdog (2026-08-05 incident: 2h15m gap)
            try:
                from backend.v9.services.daytype_watchdog import check_daytype_staleness
                # Pass app_state for self-heal (resets _last_dts_sig on staleness)
                _app_st = getattr(self, "_app_state", None)
                if _app_st is None and self._gateway:
                    _app_st = getattr(self._gateway, "_app_state", None)
                check_daytype_staleness(app_state=_app_st)
            except Exception:
                pass

            # T-252 (2026-09-04) — MEASURE the per-trade cost in code.
            #
            # The evening's log-derived attempt ("open shadow trades inflate
            # on_bar") was refuted by its own data: 19:00 and 20:00 both had 70
            # open trades and differed 2x (2,579ms vs 1,217ms mean), and 22:00
            # with 47 open was CHEAPER than 21:00 with 22. The log cannot settle
            # it, for two reasons: BarRouter only prints a handler's time when
            # it crosses 100ms (a truncated distribution — the mean of what got
            # printed is not the mean), and it reports ONE number for the whole
            # handler, so shadow work and live work are indistinguishable.
            # This timer splits them, counts every bar rather than the slow
            # tail, and is reported through get_stats().
            # The loop below has a dozen `continue`s, so the cost of iteration
            # k is charged at the TOP of iteration k+1 (and the last one after
            # the loop). No reindentation of the hot path, no try/finally.
            _t_loop = _perf.perf_counter()
            _t_prev, _prev_bucket = _t_loop, None

            for trade in active:
                _t_now = _perf.perf_counter()
                if _prev_bucket is not None:
                    self._mode_secs[_prev_bucket] += _t_now - _t_prev
                    self._mode_trades[_prev_bucket] += 1
                _t_prev = _t_now
                _prev_bucket = ("live"
                                if getattr(trade, "mode", "shadow") in ("demo", "live")
                                else "shadow")
                # Legacy DB rows may use state="OPEN" (cockpit alias for FILLED)
                if trade.state not in (
                    TradeState.FILLED.value,
                    TradeState.PARTIAL.value,
                    "OPEN",
                ):
                    continue
                if trade.entry_price is None:
                    continue

                # I-62 fix: BarLevelDetector TRAILS all trades but only CLOSES
                # shadow trades. Demo/live trades close via FillPoller (Sierra
                # fill events) — bar-price inference must NOT close them because
                # Sierra may still hold the position → orphan (trade 290, 07-03).
                # Trail (stop update) still runs for all modes.
                trade_mode = getattr(trade, "mode", "shadow")
                _is_demo_live = trade_mode in ("demo", "live")

                # Skip bars that started before the trade was opened.
                # Without this guard, a bar pushed after its close-time can be
                # applied to a trade that was opened during or after that bar —
                # recording a fill_ts (stop/target) that precedes entry_ts.
                if bar_ts is not None and trade.entry_ts is not None:
                    trade_entry = trade.entry_ts
                    # SQLite strips tzinfo on read — normalize to aware UTC (Pattern A)
                    if trade_entry.tzinfo is None:
                        trade_entry = trade_entry.replace(tzinfo=timezone.utc)
                    if bar_ts.tzinfo is None:
                        bar_ts = bar_ts.replace(tzinfo=timezone.utc)
                    if bar_ts < trade_entry:
                        continue

                direction = trade.direction

                # SCALE_IN_V1 (Michael 2026-08-13): reinforce a proven winner with
                # extra contracts. ADDITIVE only — a post-entry management add-on that
                # cannot block or alter any entry. Flag OFF → no-op; fail-safe.
                if _is_demo_live:
                    try:
                        self._maybe_scale_in(trade, bar_high, bar_low)
                    except Exception as _si_e:
                        logger.warning("[ScaleIn] hook error (no add): %s", _si_e)
                    # TREND_UPGRADE_ADD_V1 (ruling 27.08 19:55 §12) — built
                    # 28.08 night, default OFF, NO enablement without
                    # cowork+Michael. Additive-only, same fail-safe contract.
                    try:
                        self._maybe_trend_upgrade_add(trade, bar_high, bar_low)
                    except Exception as _tu_e:
                        logger.warning(
                            "[TrendUpgrade] hook error (no add): %s", _tu_e)

                # FIX-16 (TARGET_REALISM_V1): per-bar realism re-check on the
                # pending front target — runs for ALL open bars (pre-T1 too;
                # trade 350's T1 sat 2 ticks beyond the day-high for an hour).
                import os as _trail_os
                if _trail_os.getenv("TARGET_REALISM_V1", "0").lower() in ("1", "true", "yes"):
                    try:
                        self._tm.apply_target_realism_perbar(trade)
                    except Exception as _tr_err:
                        logger.warning("[BarLevelDetector] target-realism error (fail-safe skip): %s", _tr_err)

                # Trail runner stop (before stop-check so trailed stop is used)
                if trade.t1_hit_ts is not None and trade.state != "CLOSED":
                    # F5 · RUNNER_TRAIL_V2 (Michael 2026-08-20, ORACLE §5 R-A):
                    # structural swing trail on the runner — takes precedence over
                    # both older trails when ON. Returns None when it cannot
                    # evaluate (feed gap / no confirmed swing yet) and ONLY then do
                    # we fall through, so a runner is never left un-trailed by a
                    # data gap; a deliberate "hold" (False) does NOT fall through —
                    # holding is the entire point of F5.
                    _f5 = None
                    if _trail_os.getenv("RUNNER_TRAIL_V2", "0").lower() in ("1", "true", "yes"):
                        try:
                            _f5 = self._tm.apply_structural_swing_trail(trade)
                        except Exception as _f5_err:
                            logger.warning(
                                "[BarLevelDetector] F5 swing-trail error (fail-safe "
                                "fallback to legacy trail): %s", _f5_err)
                            _f5 = None
                    # Dynamic structure-trail (DYNAMIC_STRUCT_TRAIL) — runs INSTEAD of
                    # the simple hwm trail when ON; falls back to hwm trail when OFF.
                    if _f5 is not None:
                        pass  # F5 owns the stop this bar (moved or deliberately held)
                    elif _trail_os.getenv("DYNAMIC_STRUCT_TRAIL", "0").lower() in ("1", "true", "yes"):
                        # AUDIT 2026-08-17 §L1 / verified 2026-08-20: with
                        # DYNAMIC_STRUCT_TRAIL=1 the RUNNER_TRAIL_V1 `elif` below is
                        # unreachable, so RUNNER_TRAIL_V1=1 is INERT. Proof from the
                        # books: action='TRAIL' has 127 rows, all shadow, all
                        # 2026-06-18..06-24 — zero on any live trade. Say it out loud
                        # once per process instead of letting the flag index claim a
                        # lever that does not exist (SYS-2: no silent failures).
                        if (not self._runner_trail_v1_shadow_warned
                                and _trail_os.getenv("RUNNER_TRAIL_V1", "0").lower()
                                in ("1", "true", "yes")):
                            self._runner_trail_v1_shadow_warned = True
                            logger.warning(
                                "[BarLevelDetector] RUNNER_TRAIL_V1=1 is INERT: "
                                "DYNAMIC_STRUCT_TRAIL=1 takes the branch. The hwm-k*risk "
                                "trail never runs. (F5/RUNNER_TRAIL_V2 is the live lever.)")
                        try:
                            bar_close = float(bar_data.get("close", bar_data.get("c", 0)))
                            self._tm.apply_dynamic_struct_trail(trade, bar_high, bar_low, bar_close)
                        except Exception as _dst_err:
                            logger.warning("[BarLevelDetector] struct trail error (fail-safe skip): %s", _dst_err)
                    elif _trail_os.getenv("RUNNER_TRAIL_V1", "0").lower() in ("1", "true", "yes"):
                        try:
                            self._tm.apply_trail_after_t1(trade, bar_high, bar_low)
                        except Exception as _trail_err:
                            logger.warning("[BarLevelDetector] trail error (fail-safe skip): %s", _trail_err)

                stop = trade.stop  # refresh after potential trail update

                # System 6 advisory supervision — every bar on the demo/live trade
                # (flag-gated SYSTEM6_SUPERVISOR, default OFF → inert; fail-safe).
                if _is_demo_live:
                    self._system6_scan(trade, reconcile_verdict=_recon_v)
                    # W9: journal all exit/hold signals per bar (advisory, flag-gated)
                    self._system6_journal_autoloop(trade, _ts_key)

                # ── STRUCTURE_EXIT (Michael 30.08, T-142): exit on structural
                # failure. Three grades (A: failed break · B: double top · C:
                # reversal), each behind its own flag. The pure functions in
                # structure_exit.py return an action dict; the execution here
                # uses the same MODIFY_STOP/MODIFY_TARGET/FLATTEN plumbing.
                if _is_demo_live:
                    try:
                        self._maybe_structure_exit(
                            trade, direction, bar_high, bar_low,
                            float(bar_data.get("close", bar_data.get("c", 0))),
                        )
                    except Exception as _se_err:
                        logger.debug("[StructureExit] error (fail-safe): %s", _se_err)

                # S6 Target Approach Realize (2026-08-06): price within 1pt of
                # target for 2+ bars + rejection → realize via FLATTEN. Flag-gated
                # S6_TARGET_APPROACH_REALIZE_V1 (OFF). Never op=EXIT. Fail-safe.
                if _is_demo_live:
                    try:
                        from backend.v9.systems.target_approach_realize import should_realize as _tar_should
                        _tar_state_key = f"_tar_state_{trade.id}"
                        _tar_prev_state = getattr(self, _tar_state_key, None)
                        bar_close = float(bar_data.get("close", bar_data.get("c", 0)))
                        # K5 fix (2026-08-12): feed extremes dict to should_realize.
                        # Without this, EXTREMES_AWARE_REALIZE_V1 was dead — the
                        # EXCESS/POOR consumer never received its input.
                        _tar_extremes = None
                        try:
                            from backend.v9.systems.extremes_quality import classify_extremes_live
                            from backend.v9.db.read import read_all as _k5_read
                            _k5_bars = _k5_read(
                                "SELECT high AS h, low AS l, close AS c, open AS o "
                                "FROM v9_bars_5min_woodies "
                                "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
                                "(now() AT TIME ZONE 'America/New_York')::date "
                                "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
                                "ORDER BY ts ASC", {})
                            if _k5_bars and len(_k5_bars) >= 5:
                                _tar_extremes = classify_extremes_live(_k5_bars) or None
                        except Exception:
                            pass  # fail-open: no extremes = NEUTRAL behavior
                        _tar_ok, _tar_reason, _tar_new_state = _tar_should(
                            trade={
                                "direction": direction,
                                "entry_price": float(trade.entry_price),
                                "t1": float(trade.t1) if trade.t1 else None,
                                "t2": float(trade.t2) if trade.t2 else None,
                                "t3": float(trade.t3) if trade.t3 else None,
                                "t1_hit_ts": trade.t1_hit_ts,
                                "t2_hit_ts": trade.t2_hit_ts,
                            },
                            bar_high=bar_high, bar_low=bar_low, bar_close=bar_close,
                            approach_state=_tar_prev_state,
                            extremes=_tar_extremes,
                        )
                        setattr(self, _tar_state_key, _tar_new_state)
                        if _tar_ok:
                            logger.warning(
                                "[BarLevelDetector] S6 TARGET APPROACH REALIZE: trade %d — %s",
                                trade.id, _tar_reason)
                            # ROOT-FIX 2026-08-15 (same defect as MAE_SCRATCH):
                            # this call passed trade_id inside `context` while
                            # write_trade_command requires it as a keyword →
                            # TypeError, swallowed by the logger.debug below, so
                            # TARGET_APPROACH_REALIZE has NEVER executed once
                            # (proof: it announced twice on trade 670, 21 min
                            # apart — impossible if the first had closed it).
                            # Books close only after the command is written; a
                            # failed write leaves the trade open and shouts.
                            # 🔴 2026-08-17 — FLATTEN_ACCOUNT is ACCOUNT-WIDE.
                            # The DLL handler closes the NET position on the
                            # symbol and cancels every working order. Michael
                            # trades this account by hand alongside the system
                            # (5 contracts open right now, with a stop). A
                            # scratch of OUR trade would have taken HIS position
                            # out and cancelled its stop. Scratching is an
                            # optimisation; the trade is already protected by
                            # its own attached bracket, so skipping it costs a
                            # little edge — flattening his position costs money
                            # and breaks the 12:20 ownership ruling.
                            from backend.v9.services.trade_manager.manager import (
                                trade_contract_count as _tar_n)
                            from backend.v9.services.sierra_command import (
                                account_has_foreign_contracts as _foreign)
                            _fc = _foreign(_tar_n(trade))
                            if _fc is not False:
                                # Michael ruling 2026-08-21: no manual trading →
                                # foreign contracts = anomaly, not "Michael's trade".
                                logger.critical(
                                    "[TARGET-APPROACH] SKIPPED for trade %d — UNMANAGED "
                                    "contracts on the account (foreign=%s). No manual "
                                    "trading (ruling 2026-08-21) → anomaly. Investigate. "
                                    "The trade keeps its own bracket.", trade.id, _fc)
                                try:
                                    from backend.v9.services.phone_alert import push as _fp
                                    _fp("target_realize_skipped_foreign",
                                        "\U0001f534 MEMS26: מימוש-S6 דולג — חוזים-זרים",
                                        f"trade {trade.id}: חוזים לא-מנוהלים בחשבון "
                                        f"(אורפן/fill-שאבד). FLATTEN דולג. לחקור.")
                                except Exception:
                                    pass
                                continue

                            from backend.v9.services.sierra_command import write_flatten_account
                            try:
                                write_flatten_account(
                                    trade_id=str(trade.id),
                                    source="target_approach_realize",
                                    reason=_tar_reason)
                            except Exception as _tar_cmd_err:
                                logger.critical(
                                    "[BarLevelDetector] TARGET-APPROACH: FLATTEN command "
                                    "FAILED for trade %d (%s) — books NOT closed",
                                    trade.id, _tar_cmd_err)
                                try:
                                    from backend.v9.services.phone_alert import push as _tar_push
                                    _tar_push("target_realize_flatten_failed",
                                              "\U0001f534 MEMS26: מימוש לא בוצע",
                                              f"trade {trade.id}: פקודת-הסגירה נכשלה — "
                                              f"הפוזיציה עדיין פתוחה בסיירה", priority=1)
                                except Exception:
                                    pass
                                continue
                            # T4 (Michael 08-14): a written command is not an
                            # exit. Defer the close until sierra_state proves
                            # flat; verify_pending() runs it from the poller.
                            def _tar_close(_tid=trade.id):
                                self._tm.close_trade(_tid, reason="TARGET_APPROACH_REALIZE")
                            from backend.v9.services import exit_verifier as _tar_ev
                            from backend.v9.services.trade_manager.manager import (
                                trade_contract_count as _tar_n)
                            if not _tar_ev.register(trade.id,
                                                    source="target_approach_realize",
                                                    reason=_tar_reason,
                                                    contracts=_tar_n(trade),
                                                    on_confirmed=_tar_close,
                                                    still_open=lambda _t=trade.id:
                                                        self._trade_still_open(_t)):
                                _tar_close()
                    except Exception as _tar_err:
                        logger.warning("[BarLevelDetector] target-approach error: %s", _tar_err)

                # S6 MAE scratch (DEV_PLAN 02.08 §P3.1): adverse excursion ≥
                # per-pattern threshold before T1 → FLATTEN. Flag-gated
                # S6_MAE_SCRATCH_V1 (OFF). Never op=EXIT. Fail-safe.
                if _is_demo_live:
                    try:
                        from backend.v9.systems.mae_scratch import (
                            should_scratch, current_atr14 as _mae_atr)
                        _q = trade.quality if isinstance(getattr(trade, "quality", None), dict) else {}
                        _pat = _q.get("pattern_name", _q.get("setup_type", ""))
                        # T-43a: use position reference price for MAE calc
                        from backend.v9.services.trade_manager.manager import (
                            _position_reference_price)
                        try:
                            _mae_entry = _position_reference_price(
                                trade, self._tm._db)
                        except Exception:
                            _mae_entry = float(trade.entry_price)
                        _scratch, _scratch_reason = should_scratch(
                            pattern_name=_pat,
                            entry_price=_mae_entry,
                            direction=direction,
                            bar_low=bar_low,
                            bar_high=bar_high,
                            t1_hit=trade.t1_hit_ts is not None,
                            stop_price=float(trade.stop) if trade.stop else None,
                            # S6_MAE_SCRATCH_ATR_V1: same 14-bar TR average the
                            # System-6 scan uses. Returns 0.0 without touching
                            # the DB when the ATR flag is OFF, and should_scratch
                            # then ignores it entirely (fixed-threshold path).
                            atr=_mae_atr(),
                        )
                        if _scratch:
                            logger.warning(
                                "[BarLevelDetector] S6 MAE SCRATCH: trade %d — %s",
                                trade.id, _scratch_reason)
                            # ROOT-FIX 2026-08-14 (Michael, live: "the system
                            # reported the trade closed but the order never
                            # reached Sierra"). This path closed the BOOKS and
                            # never sent an exit — on 08-14 trade #682 was
                            # marked CLOSED/$0 at 20:00 while Sierra still held
                            # SHORT 4 @7799.25 for 62 minutes, the LIVE slot was
                            # freed (so the engine could stack another fire on
                            # top), and the loss was reported as $0 so the daily
                            # risk counter under-counted.
                            # TARGET_APPROACH_REALIZE 34 lines above already
                            # does this correctly: FLATTEN first, then close the
                            # books. Same order here — and if the command cannot
                            # be written we do NOT close the books (an unclosed
                            # book with a live position is recoverable; a closed
                            # book with a live position is a ghost).
                            # 🔴 2026-08-17 — FLATTEN_ACCOUNT is ACCOUNT-WIDE.
                            # The DLL handler closes the NET position on the
                            # symbol and cancels every working order. Michael
                            # trades this account by hand alongside the system
                            # (5 contracts open right now, with a stop). A
                            # scratch of OUR trade would have taken HIS position
                            # out and cancelled its stop. Scratching is an
                            # optimisation; the trade is already protected by
                            # its own attached bracket, so skipping it costs a
                            # little edge — flattening his position costs money
                            # and breaks the 12:20 ownership ruling.
                            from backend.v9.services.trade_manager.manager import (
                                trade_contract_count as _mae_n)
                            from backend.v9.services.sierra_command import (
                                account_has_foreign_contracts as _foreign)
                            _fc = _foreign(_mae_n(trade))
                            if _fc is not False:
                                logger.critical(
                                    "[MAE-SCRATCH] SKIPPED for trade %d — UNMANAGED "
                                    "contracts on the account (foreign=%s). No manual "
                                    "trading (ruling 2026-08-21) → anomaly. Investigate. "
                                    "The trade keeps its own bracket.", trade.id, _fc)
                                try:
                                    from backend.v9.services.phone_alert import push as _fp
                                    _fp("mae_scratch_skipped_foreign",
                                        "\U0001f534 MEMS26: SCRATCH דולג — חוזים-זרים",
                                        f"trade {trade.id}: חוזים לא-מנוהלים בחשבון "
                                        f"(אורפן/fill-שאבד). FLATTEN דולג. לחקור.")
                                except Exception:
                                    pass
                                continue

                            try:
                                from backend.v9.services.sierra_command import (
                                    write_flatten_account as _mae_write,
                                )
                                _mae_write(trade_id=str(trade.id),
                                           source="mae_scratch",
                                           reason=_scratch_reason)
                            except Exception as _mae_cmd_err:
                                logger.critical(
                                    "[BarLevelDetector] MAE SCRATCH: FLATTEN command "
                                    "FAILED for trade %d (%s) — books NOT closed, "
                                    "position stays owned", trade.id, _mae_cmd_err)
                                try:
                                    from backend.v9.services.phone_alert import push as _mae_push
                                    _mae_push("mae_scratch_flatten_failed",
                                              "\U0001f534 MEMS26: SCRATCH לא בוצע",
                                              f"trade {trade.id}: פקודת-הסגירה נכשלה — "
                                              f"הפוזיציה עדיין פתוחה בסיירה",
                                              priority=1)
                                except Exception:
                                    pass
                                continue  # do NOT close the books

                            # T4 (Michael 08-14, trade #682): books close only
                            # once sierra_state proves flat. Everything that
                            # used to run inline after close_trade moves into
                            # the callback so the LIVE slot, the gateway and
                            # the ops-log all stay consistent with reality.
                            def _mae_close(_tid=trade.id, _dir=direction,
                                           _mode=getattr(trade, "mode", "demo"),
                                           _why=_scratch_reason):
                                self._tm.close_trade(_tid, reason="MAE_SCRATCH")
                                if self._gateway:
                                    try:
                                        self._gateway.on_trade_close({
                                            "trade_id": _tid,
                                            "mode": _mode,
                                            "pnl_usd": 0.0,
                                            "outcome": "SCRATCH",
                                            "direction": _dir,
                                        })
                                    except Exception:
                                        pass
                                try:
                                    from scripts.ops_log import log_event
                                    log_event("mae_scratch", "WARNING", _why)
                                except Exception:
                                    pass

                            from backend.v9.services import exit_verifier as _mae_ev
                            from backend.v9.services.trade_manager.manager import (
                                trade_contract_count as _mae_n)
                            if not _mae_ev.register(trade.id, source="mae_scratch",
                                                    reason=_scratch_reason,
                                                    contracts=_mae_n(trade),
                                                    on_confirmed=_mae_close,
                                                    still_open=lambda _t=trade.id:
                                                        self._trade_still_open(_t)):
                                _mae_close()
                            continue  # trade scratched — skip further checks
                    except Exception as _mae_err:
                        logger.debug("[BarLevelDetector] MAE scratch error (fail-safe): %s", _mae_err)

                # 1. Stop check FIRST (adverse fill priority)
                if stop is not None:
                    if (direction == "LONG" and bar_low <= stop) or \
                       (direction == "SHORT" and bar_high >= stop):
                        if _is_demo_live:
                            # I-62: demo/live → log but do NOT close (wait for Sierra fill)
                            logger.info("[BarLevelDetector] STOP INFERRED (demo/live): trade %d at %.2f — awaiting Sierra fill",
                                        trade.id, stop)
                            continue
                        self._tm.on_stop_hit(trade.id, fill_ts=bar_ts)
                        logger.info("[BarLevelDetector] STOP HIT: trade %d at %.2f", trade.id, stop)
                        self._notify_trade_close(trade, "STOP")
                        continue  # trade closed, skip target checks

                # 2. Target checks: T1 → T2 → T3 (sequential)
                targets = [
                    ("T1", trade.t1, trade.t1_hit_ts),
                    ("T2", trade.t2, trade.t2_hit_ts),
                    ("T3", trade.t3, trade.t3_hit_ts),
                ]
                for target_name, target_price, hit_ts in targets:
                    if target_price is None or hit_ts is not None:
                        continue  # skip if no target or already hit
                    try:
                        if float(target_price) <= 0:
                            continue  # Sierra unused T2/T3 slot
                    except (TypeError, ValueError):
                        continue
                    # FIX-3 (incident 333): sanity — target must be on the correct
                    # side of entry. A LONG target below entry = poisoned geometry
                    # (e.g. TP-1 clamp set targets to IB-H below entry).
                    _entry = getattr(trade, "entry_price", None)
                    if _entry is not None:
                        try:
                            _ep = float(_entry)
                            if (direction == "LONG" and float(target_price) < _ep) or \
                               (direction == "SHORT" and float(target_price) > _ep):
                                logger.critical(
                                    "[BarLevelDetector] INSANE TARGET GEOMETRY trade=%d %s "
                                    "target=%s=%.2f entry=%.2f — inference disabled",
                                    trade.id, direction, target_name, float(target_price), _ep)
                                continue
                        except (TypeError, ValueError):
                            pass

                    if (direction == "LONG" and bar_high >= target_price) or \
                       (direction == "SHORT" and bar_low <= target_price):
                        if _is_demo_live:
                            # I-62 FULL (incident 350, 2026-07-10 22:03): bar-price
                            # inference must NEVER drive T-hits on demo/live — only
                            # Sierra fills (fill_poller) may. The old guard covered
                            # T3 only; a phantom "T2 HIT at 7622" (no bar reached
                            # 7622; Sierra had already STOPPED the runner at ~7610)
                            # closed live 350 as a fictional +$112.5 WIN while
                            # reality was +$52.5. Same rule as the stop path above.
                            logger.info("[BarLevelDetector] %s INFERRED (demo/live): trade %d at %.2f — awaiting Sierra fill",
                                        target_name, trade.id, target_price)
                            continue
                        self._tm.on_target_hit(trade.id, target_name, fill_ts=bar_ts)
                        logger.info("[BarLevelDetector] %s HIT: trade %d at %.2f",
                                    target_name, trade.id, target_price)
                        # After T3 (all contracts out): notify gateway to free demo slot
                        if target_name == "T3":
                            self._notify_trade_close(trade, "T3")

            # close out the final iteration + record this bar's totals
            if _prev_bucket is not None:
                self._mode_secs[_prev_bucket] += _perf.perf_counter() - _t_prev
                self._mode_trades[_prev_bucket] += 1
            _loop_ms = (_perf.perf_counter() - _t_loop) * 1000.0
            self._loop_ms_total += _loop_ms
            self._loop_ms_max = max(self._loop_ms_max, _loop_ms)
            self._loop_bars += 1
            self._open_by_mode = {
                "shadow": sum(1 for t in active
                              if getattr(t, "mode", "shadow") not in ("demo", "live")),
                "live": sum(1 for t in active
                            if getattr(t, "mode", "shadow") in ("demo", "live")),
            }

            self._tm._db.commit()

        except Exception as e:
            logger.error("[BarLevelDetector] on_bar error: %s", e, exc_info=True)

    def _maybe_scale_in(self, trade, bar_high: float, bar_low: float) -> None:
        """SCALE_IN_V1 (Michael ruling 2026-08-13 "אם הכיוון ממשיך אפשר לחזק בעוד
        חוזים"): reinforce a WINNING, with-trend, T1-banked trade with extra contracts
        — a linked CHILD add-on trade with its own stop at the parent entry (BE). Purely
        additive: never touches the entry path. Flag OFF → no-op. Any error → no add.
        Idempotent: marks the parent `scaled_in` BEFORE placing so a retry can't double-add."""
        import os as _si_os
        if _si_os.getenv("SCALE_IN_V1", "0").lower() not in ("1", "true", "yes"):
            return
        q = trade.quality if isinstance(getattr(trade, "quality", None), dict) else {}
        if q.get("scaled_in"):
            return
        if trade.t1_hit_ts is None or trade.entry_price is None:
            return
        from backend.v9.services.trade_manager.scale_in import should_scale_in, ScaleInCfg
        _p3_on = _si_os.getenv("SCALE_IN_P3_V1", "0").lower() in ("1", "true", "yes")
        cfg = ScaleInCfg(
            min_profit_pts=float(_si_os.getenv("SCALE_IN_MIN_PROFIT_PTS", "6") or 6),
            add_contracts=int(_si_os.getenv("SCALE_IN_ADD_CONTRACTS", "2") or 2),
            max_total_contracts=int(_si_os.getenv("SCALE_IN_MAX_TOTAL", "8") or 8),
            # P3: computed spacing — only when flag ON; OFF = byte-identical to today
            atr_spacing_mult=1.5 if _p3_on else 0.0,
            min_rr_spacing=1.5 if _p3_on else 0.0,
            avg_stop=_p3_on,
            edge_ban=_p3_on,
        )
        dir_bias = None
        try:
            from backend.v9.services.trade_context import get_live_dir_bias
            dir_bias = get_live_dir_bias()
        except Exception:
            pass
        # ── two blockers found 2026-08-17, both fixed by asking SIERRA ──────
        # (1) The reinforcement was decided against the BOOKS. On 13.08 the
        #     reconciler logged "TM says 4 contracts, Sierra says 1" at the
        #     moment child 662 was placed — 0 divergences in the 5.5 minutes
        #     before, 18 in the ten minutes after. We were adding contracts on
        #     top of a position the broker may no longer have held.
        # (2) `max_total_contracts` compared the PARENT's size (2 or 4) against
        #     the cap, so a CHAIN 660 -> 661 -> 662 never hit it: every link saw
        #     "2 + 2 <= 8". A replay reached 20 contracts. Michael's 8-contract
        #     ceiling was written down and never enforced.
        # Both close with the same fact: the account's real net position. It is
        # also the honest denominator for the cap, because margin is charged on
        # the account, not on our books.
        _acct = None
        try:
            from backend.v9.services.sierra_position_reconciler import _sierra_state_qty
            _acct = _sierra_state_qty()
        except Exception:
            _acct = None
        if _acct is None:
            logger.warning("[ScaleIn] no fresh Sierra position — not reinforcing "
                           "(unknown is never a reason to add contracts)")
            return
        _want_long = (trade.direction or "").upper() == "LONG"
        if (_want_long and _acct <= 0) or ((not _want_long) and _acct >= 0):
            logger.warning("[ScaleIn] Sierra holds %s but the trade is %s — the "
                           "position to reinforce is not there. Not reinforcing.",
                           _acct, trade.direction)
            return
        n_open = abs(int(_acct))
        # P3: gather ATR, initial risk, session extremes for computed spacing
        _p3_atr = _p3_risk = _p3_sh = _p3_sl = _p3_stop = None
        try:
            # FLAG_AUDIT fix: V9Trade uses `stop`, not `stop_price`
            _p3_stop = float(trade.stop) if trade.stop else None
            _p3_risk = abs(float(trade.entry_price) - _p3_stop) if _p3_stop else None
        except (TypeError, ValueError):
            pass
        try:
            from backend.v9.db.read import read_all as _p3_read
            _p3_rows = _p3_read(
                "SELECT high, low FROM v9_bars_5min_woodies "
                "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
                "(now() AT TIME ZONE 'America/New_York')::date "
                "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
                "ORDER BY ts", {})
            if _p3_rows:
                _p3_sh = max(float(r["high"]) for r in _p3_rows)
                _p3_sl = min(float(r["low"]) for r in _p3_rows)
                if len(_p3_rows) >= 15:
                    import statistics as _p3_stats
                    _trs = []
                    for _ri in range(max(1, len(_p3_rows)-14), len(_p3_rows)):
                        _b, _p = _p3_rows[_ri], _p3_rows[_ri-1]
                        _trs.append(max(float(_b["high"])-float(_b["low"]),
                                        abs(float(_b["high"])-float(_p["low"]))))
                    _p3_atr = _p3_stats.fmean(_trs) if _trs else None
        except Exception:
            pass
        dec = should_scale_in(
            direction=trade.direction, entry_price=float(trade.entry_price),
            t1_hit=True, already_scaled=False, n_contracts_open=n_open,
            bar_high=float(bar_high), bar_low=float(bar_low),
            dir_bias=dir_bias, cfg=cfg,
            atr=_p3_atr, initial_risk_pts=_p3_risk,
            session_high=_p3_sh, session_low=_p3_sl,
            stop_price=_p3_stop,
        )
        if dec is None:
            return
        # ── T-111 margin precheck (night mandate 27-28.08, broker-reject
        # evidence in margin_precheck's docstring). Runs BEFORE the parent is
        # marked, so a margin-skipped add stays eligible on a later bar when
        # funds free up ("אם הכיוון ממשיך אפשר לחזק"). Default ON;
        # SCALE_IN_MARGIN_PRECHECK_V1=0 restores the old blind PLACE.
        if _si_os.getenv("SCALE_IN_MARGIN_PRECHECK_V1", "1").lower() in (
                "1", "true", "yes"):
            from backend.v9.services.trade_manager.scale_in import (
                margin_precheck)
            _mp_avail = None
            try:
                import json as _mp_json
                _mp_path = _si_os.path.join(
                    _si_os.getenv("V9_EXPORT_DIR", _si_os.path.expanduser(
                        "~/SierraChart_Data/v9_export")),
                    "sierra_state.json")
                with open(_mp_path) as _mp_fh:
                    _mp_raw = _mp_json.load(_mp_fh).get("acct_available_funds")
                _mp_avail = float(_mp_raw) if _mp_raw is not None else None
            except Exception:
                _mp_avail = None
            _mp_per = float(_si_os.getenv(
                "SCALE_IN_MARGIN_PER_CONTRACT", "398.75") or 398.75)
            _mp_ok, _mp_reason = margin_precheck(
                dec.add_contracts, _mp_avail, _mp_per)
            if not _mp_ok:
                logger.warning("[ScaleIn] SKIP child (parent=%s): %s",
                               getattr(trade, "id", "?"), _mp_reason)
                return
        # mark parent FIRST (idempotent) — even if the PLACE below errors, we never re-add
        q2 = dict(q); q2["scaled_in"] = True; q2["scale_in_child_pending"] = True
        trade.quality = q2
        try:
            self._tm._db.commit()
        except Exception:
            pass
        # child add-on: own bracket, stop = parent entry (BE), modest 1.5R first target
        risk = abs(dec.entry - dec.stop) or 1.0
        _t1 = (dec.entry + 1.5 * risk) if dec.direction == "LONG" else (dec.entry - 1.5 * risk)
        child = {
            "firing_system": getattr(trade, "firing_system", 2) or 2,
            "direction": dec.direction, "entry_price": dec.entry, "stop": dec.stop,
            "t1": round(_t1, 2), "t2": None, "t3": None, "contracts": dec.add_contracts,
            "classification": "SCALE_IN",
            "metadata": {"scale_in_parent": getattr(trade, "id", None), "reason": dec.reason},
        }
        _mode = getattr(trade, "mode", "live")
        child_id = self._tm.accept_setup(child, _mode)
        # Write the link back onto the PARENT too (2026-08-18). Until now only
        # the child knew who its parent was, so anything looking at the parent —
        # the trade card, a post-mortem — could not tell that the position had
        # grown. Also clears `scale_in_child_pending`, which was set and never
        # cleared.
        try:
            _q = dict(trade.quality) if isinstance(trade.quality, dict) else {}
            _q["scale_in_child_id"] = child_id
            _q["scale_in_added"] = dec.add_contracts
            _q.pop("scale_in_child_pending", None)
            trade.quality = _q
            self._tm._db.commit()
        except Exception:
            pass
        from backend.v9.services.sierra_command import command_from_setup
        _res = command_from_setup(
            child, trade_id=str(child_id),
            account=_si_os.environ.get("SIERRA_LIVE_ACCOUNT", "37138283"), mode=_mode,
        )
        # T-226 ROOT-FIX (2026-09-02): the PLACE result was DISCARDED. When a
        # pre-send guard refuses the order the books keep a live trade that
        # never reached the market — a ghost. Measured twice today, the same
        # chain word for word (#955 17:30, #979 21:18:53):
        #   Trade 979 created: mode=live sys=4 dir=LONG
        #   T-214: PLACE rejected — t3=None invalid on 4 contracts.
        #   [Reconciler] SYS-3 DIVERGENCE: TM says 8 contracts
        #       ['#971(live,LONG,4c)', '#979(live,LONG,4c)'], Sierra says 2
        # — then DIVERGENCE every 30s until a containment guard cleaned up.
        # A refused PLACE must unwind its own row.
        if not self._rollback_if_place_refused(_res, child_id, trade, "ScaleIn"):
            return
        logger.warning(
            "[ScaleIn] +%dc %s parent=%s child=%s @%.2f stop@%.2f (BE) — %s",
            dec.add_contracts, dec.direction, getattr(trade, "id", "?"),
            child_id, dec.entry, dec.stop, dec.reason,
        )

    def _rollback_if_place_refused(self, result, child_id, parent, tag: str) -> bool:
        """T-226: unwind an add-on child whose PLACE never reached the broker.

        Returns True when the PLACE went out (caller continues), False when the
        child was rolled back. Fail-safe: any error here leaves the row alone
        and screams — a botched rollback must never touch a real position.

        Only ever acts on an explicit ``{"rejected": True}`` from
        ``command_from_setup``. A None/absent result is treated as "sent", which
        is the pre-fix behaviour, so no path that currently places is changed.
        """
        if not isinstance(result, dict) or not result.get("rejected"):
            return True
        reason = result.get("reason", "unknown")
        detail = result.get("detail", "")
        logger.error(
            "[%s] T-226: PLACE REFUSED (%s: %s) for child %s of parent %s — "
            "rolling the child back; it never reached the market",
            tag, reason, detail, child_id, getattr(parent, "id", "?"))
        try:
            self._tm.close_trade(int(child_id),
                                 reason=f"PLACE_REFUSED:{reason}"[:30],
                                 outcome_override="CANCELLED")
            _child = self._tm._get_trade(int(child_id))
            if _child is not None:
                _child.state = "CANCELLED"
                self._notify_trade_close(_child, f"PLACE_REFUSED:{reason}")
            # The parent was told it had grown — untell it, or the trade card
            # and every post-mortem keep claiming contracts that do not exist.
            _q = dict(parent.quality) if isinstance(
                getattr(parent, "quality", None), dict) else {}
            if _q.pop("scale_in_child_id", None) is not None:
                _q.pop("scale_in_added", None)
                _q["scale_in_last_refused"] = {"child_id": child_id,
                                               "reason": reason}
                parent.quality = _q
            self._tm._db.commit()
        except Exception as e:
            logger.error(
                "[%s] T-226: rollback of child %s FAILED (%s) — the ghost row "
                "is still open, expect SYS-3 DIVERGENCE", tag, child_id, e)
        try:
            from scripts.ops_log import log_event as _ops
            _ops("scale_in", "ERROR",
                 f"T-226 {tag} PLACE refused ({reason}) — child {child_id} "
                 f"rolled back, parent {getattr(parent, 'id', '?')} unlinked")
        except Exception:
            pass
        return False

    def _maybe_structure_exit(self, trade, direction, bar_high, bar_low,
                              bar_close) -> None:
        """STRUCTURE_EXIT (Michael 30.08, T-142): exit on structural failure.

        Three grades, each behind its own env flag (OFF = byte-identical).
        The pure functions in structure_exit.py decide; this method executes
        via the trade_manager's verified MODIFY/FLATTEN plumbing.
        op=EXIT is never used (broken, ruling 07-13).
        """
        import os as _se_os

        # ── Grade-A: failed break in position direction ──
        _se_a_mode = _se_os.getenv(
            "STRUCTURE_EXIT_FAILBREAK_V1", "0").lower()
        if _se_a_mode in ("1", "true", "live", "shadow"):
            try:
                from backend.v9.services.trade_manager.structure_exit import (
                    should_exit_on_failbreak)
                from backend.v9.systems.failed_break import detect_failed_break

                # Run the SAME detector the entry system uses
                _se_bars = []
                try:
                    from backend.v9.db.read import read_all as _se_read
                    _se_rows = _se_read(
                        "SELECT high h, low l, close c, open o "
                        "FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT 14", {})
                    _se_bars = [dict(r) for r in reversed(list(_se_rows or []))]
                except Exception:
                    pass

                if len(_se_bars) >= 3:
                    # Get levels for the failed break detector
                    _se_tpo = {}
                    try:
                        from backend.v9.systems.five_min.five_min_system import (
                            _load_sierra_tpo)
                        _se_tpo = _load_sierra_tpo() or {}
                    except Exception:
                        pass
                    _se_vah = float(_se_tpo.get("vah") or 0) or None
                    _se_val = float(_se_tpo.get("val") or 0) or None

                    _se_fb = None
                    if _se_vah and _se_val:
                        _se_fb = detect_failed_break(
                            _se_bars, _se_vah, _se_val,
                            edge_label="VA",
                            already_fired=getattr(self, "_se_fired", None),
                        )

                    if _se_fb:
                        from backend.v9.shared.atr import atr_5min as _se_atr
                        _se_atr_val = _se_atr(_se_bars, period=14)
                        _se_result = should_exit_on_failbreak(
                            trade_direction=direction,
                            trade_entry_price=float(trade.entry_price),
                            trade_stop=float(trade.stop) if trade.stop else None,
                            trade_t1_hit=trade.t1_hit_ts is not None,
                            bar_high=bar_high,
                            bar_low=bar_low,
                            bar_close=bar_close,
                            failed_break=_se_fb,
                            atr=_se_atr_val,
                        )
                        if _se_result:
                            _se_key = f"SE_A_{trade.id}_{_se_fb.get('type', '')}"
                            if not hasattr(self, "_se_fired"):
                                self._se_fired = set()
                            if _se_key not in self._se_fired:
                                self._se_fired.add(_se_key)
                                logger.warning(
                                    "[StructureExit] GRADE-A: trade %d %s — %s",
                                    trade.id, direction, _se_result["reason"])
                                # STRUCTURE_EXIT_REALIZE_V1 (Michael 02.09 13:40):
                                # כפולה-שנכשלת ⇒ מימוש. After T1 hit, tighten
                                # stops on ALL open legs to lock profit, don't FLATTEN.
                                # Before T1 → no action (don't realize a loss).
                                # Consumer file:line: THIS block.
                                _realize_on = _se_os.getenv(
                                    "STRUCTURE_EXIT_REALIZE_V1", "0").lower() in (
                                    "1", "true", "live")
                                if _realize_on and trade.t1_hit_ts is not None:
                                    # After T1 — lock profit on all open legs
                                    _rlz_dir = direction
                                    if _rlz_dir == "LONG":
                                        _rlz_stop = round(bar_close - 0.25, 2)
                                    else:
                                        _rlz_stop = round(bar_close + 0.25, 2)
                                    # Per-leg MODIFY_STOP using T0-aware mapping
                                    q = trade.quality if isinstance(
                                        trade.quality, dict) else {}
                                    _rlz_emitted = 0
                                    for _tgt_f in ("t1", "t2", "t3"):
                                        _hit = getattr(trade, f"{_tgt_f}_hit_ts", None)
                                        if _hit is not None:
                                            continue  # already banked
                                        _okey = self._tm._target_order_key(trade, _tgt_f)
                                        # Get the STOP order for this leg's group
                                        _grp = self._tm._ladder_group_for(trade,
                                            _tgt_f.upper())
                                        _skey = f"c{(_grp or 0) + 1}_stop_id"
                                        _sid = q.get(_skey)
                                        if _sid:
                                            self._tm._emit_modify_stop(
                                                trade, _rlz_stop)
                                            _rlz_emitted += 1
                                    logger.warning(
                                        "[StructureExit] REALIZE: trade %d %s — "
                                        "locked %d open legs to %.2f (failed break "
                                        "after T1)", trade.id, direction,
                                        _rlz_emitted, _rlz_stop)
                                elif _realize_on and trade.t1_hit_ts is None:
                                    logger.info(
                                        "[StructureExit] REALIZE skip: trade %d "
                                        "pre-T1 — no action on failed break signal",
                                        trade.id)
                                elif _se_a_mode != "shadow":
                                    # EXECUTE the action
                                    if _se_result.get("flatten"):
                                        # Foreign-contract guard: compare our
                                        # contracts vs Sierra position. If Sierra
                                        # holds more → someone else's position is
                                        # in the account. FLATTEN would kill it.
                                        _flatten_ok = True
                                        try:
                                            from backend.v9.services.sierra_position_reconciler import (
                                                _sierra_state_qty)
                                            from backend.v9.services.trade_manager.manager import (
                                                trade_contract_count)
                                            _our = trade_contract_count(trade)
                                            _sq = _sierra_state_qty()
                                            if _sq is not None and abs(_sq) > _our:
                                                _flatten_ok = False
                                                logger.critical(
                                                    "[StructureExit] FLATTEN BLOCKED: "
                                                    "foreign contracts — Sierra %d vs "
                                                    "ours %d. Not flattening.",
                                                    _sq, _our)
                                                try:
                                                    from backend.v9.services.phone_alert import push as _fg_push
                                                    _fg_push("foreign_flatten_block",
                                                        "\u26a0 MEMS26: FLATTEN חסום — חוזים זרים",
                                                        f"Sierra {_sq} vs ours {_our}")
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass  # fail-open: can't check → allow
                                        if _flatten_ok:
                                            try:
                                                from backend.v9.services.sierra_command import (
                                                    write_flatten_account)
                                                write_flatten_account(
                                                    trade_id=str(trade.id),
                                                    source="structure_exit_failbreak",
                                                    reason=_se_result["reason"])
                                            except Exception as _fl_err:
                                                logger.critical(
                                                    "[StructureExit] FLATTEN FAILED: %s",
                                                    _fl_err)
                                    else:
                                        # Tighten stop
                                        new_stop = _se_result["new_stop"]
                                        self._tm._emit_modify_stop(
                                            trade, new_stop)
                                        # Pull target
                                        new_target = _se_result.get("new_target")
                                        if new_target is not None:
                                            self._tm._emit_modify_target(
                                                trade, new_target)
            except Exception as _se_a_err:
                logger.debug("[StructureExit] grade-A error: %s", _se_a_err)

        # ── Grade-B: double ceiling/floor → FLATTEN ──
        _se_b_mode = _se_os.getenv(
            "STRUCTURE_EXIT_DOUBLE_V1", "0").lower()
        if _se_b_mode in ("1", "true", "live", "shadow"):
            try:
                from backend.v9.services.trade_manager.structure_exit import (
                    should_exit_on_double_top)
                # Read the ceiling/floor state from the five_min_system instance
                _se_cfs = None
                try:
                    from backend.v9.services.trade_context import (
                        get_ceiling_floor_state)
                    _se_cfs = get_ceiling_floor_state()
                except Exception:
                    pass
                _se_b_result = should_exit_on_double_top(
                    trade_direction=direction,
                    ceiling_floor_state=_se_cfs,
                    grade_a_fired=bool(
                        getattr(self, "_se_fired", set()) &
                        {f"SE_A_{trade.id}_{t}"
                         for t in ("FB_HIGH_VA", "FB_LOW_VA",
                                   "FB_HIGH_SESSION", "FB_LOW_SESSION")}),
                )
                if _se_b_result:
                    _se_b_key = f"SE_B_{trade.id}"
                    if not hasattr(self, "_se_fired"):
                        self._se_fired = set()
                    if _se_b_key not in self._se_fired:
                        self._se_fired.add(_se_b_key)
                        logger.warning(
                            "[StructureExit] GRADE-B: trade %d %s — %s",
                            trade.id, direction, _se_b_result["reason"])
                        if _se_b_mode != "shadow":
                            try:
                                from backend.v9.services.sierra_command import (
                                    write_flatten_account)
                                write_flatten_account(
                                    trade_id=str(trade.id),
                                    source="structure_exit_double",
                                    reason=_se_b_result["reason"])
                            except Exception as _fl_err:
                                logger.critical(
                                    "[StructureExit] FLATTEN (grade-B) FAILED: %s",
                                    _fl_err)
            except Exception as _se_b_err:
                logger.debug("[StructureExit] grade-B error: %s", _se_b_err)

    def _maybe_trend_upgrade_add(self, trade, bar_high, bar_low) -> None:
        """TREND_UPGRADE_ADD_V1 (Michael ruling 27.08 19:55 §12; doctrine
        ~19:10 "כל תווית חדשה = סט-הזדמנויות חדש שנפתח מיד"). When the
        PUBLISHED day-type label upgrades INTO Trend_* while this live trade
        rides WITH the trend direction — reinforce through the SCALE_IN child
        mechanism: independent bracket, child stop at parent BE, T-111 margin
        precheck, physical OCO ceiling 6. Built 28.08 night, **default OFF —
        enabling requires cowork+Michael sign-off**. Additive-only; fail-safe;
        the no-position branch (next-entry size bonus) is NOT built yet.
        """
        import os as _tu_os
        import time as _tu_time
        if _tu_os.getenv("TREND_UPGRADE_ADD_V1", "0").lower() not in (
                "1", "true", "yes"):
            return
        try:
            from backend.v9.services.trade_context import get_live_day_type
            label_now = get_live_day_type()
        except Exception:
            return
        # Edge detection is PROCESS-level (one edge serves every open trade on
        # that bar): remember the last label; a change records an edge that
        # stays consumable for 240s. First observation after boot sets prev
        # without firing (a restart is not an upgrade).
        _now = _tu_time.time()
        _last = getattr(self, "_tu_last_label", None)
        if label_now != _last:
            self._tu_last_label = label_now
            if _last is not None:
                self._tu_edge = {"prev": _last, "now": label_now, "at": _now}
        edge = getattr(self, "_tu_edge", None)
        if (not edge or edge.get("now") != label_now
                or _now - float(edge.get("at", 0)) > 240):
            return
        q = trade.quality if isinstance(getattr(trade, "quality", None), dict) else {}
        dir_bias = None
        try:
            from backend.v9.services.trade_context import get_live_dir_bias
            dir_bias = get_live_dir_bias()
        except Exception:
            pass
        from backend.v9.services.trade_manager.scale_in import (
            margin_precheck, trend_upgrade_add)
        dec = trend_upgrade_add(
            label_now=edge["now"], label_prev=edge["prev"],
            position_direction=trade.direction, dir_bias=dir_bias,
            already_added=bool(q.get("trend_upgrade_added")),
            add_contracts=int(_tu_os.getenv(
                "TREND_UPGRADE_ADD_CONTRACTS", "2") or 2),
        )
        if dec is None:
            return
        # Same "unknown is never a reason to add" contract as SCALE_IN.
        _acct = None
        try:
            from backend.v9.services.sierra_position_reconciler import (
                _sierra_state_qty)
            _acct = _sierra_state_qty()
        except Exception:
            _acct = None
        if _acct is None:
            logger.warning("[TrendUpgrade] no fresh Sierra position — not adding")
            return
        _want_long = (trade.direction or "").upper() == "LONG"
        if (_want_long and _acct <= 0) or ((not _want_long) and _acct >= 0):
            return
        if abs(int(_acct)) + int(dec["add_contracts"]) > 6:
            logger.warning("[TrendUpgrade] OCO ceiling: |%s|+%s > 6 — not adding",
                           _acct, dec["add_contracts"])
            return
        # T-111 margin precheck — identical contract to SCALE_IN's.
        if _tu_os.getenv("SCALE_IN_MARGIN_PRECHECK_V1", "1").lower() in (
                "1", "true", "yes"):
            _mp_avail = None
            try:
                import json as _mp_json
                _mp_path = _tu_os.path.join(
                    _tu_os.getenv("V9_EXPORT_DIR", _tu_os.path.expanduser(
                        "~/SierraChart_Data/v9_export")),
                    "sierra_state.json")
                with open(_mp_path) as _mp_fh:
                    _mp_raw = _mp_json.load(_mp_fh).get("acct_available_funds")
                _mp_avail = float(_mp_raw) if _mp_raw is not None else None
            except Exception:
                _mp_avail = None
            _mp_ok, _mp_reason = margin_precheck(
                int(dec["add_contracts"]), _mp_avail,
                float(_tu_os.getenv("SCALE_IN_MARGIN_PER_CONTRACT",
                                    "398.75") or 398.75))
            if not _mp_ok:
                logger.warning("[TrendUpgrade] SKIP child (parent=%s): %s",
                               getattr(trade, "id", "?"), _mp_reason)
                return
        # mark parent FIRST (idempotent — a retry can never double-add)
        q2 = dict(q)
        q2["trend_upgrade_added"] = True
        trade.quality = q2
        try:
            self._tm._db.commit()
        except Exception:
            pass
        entry = round(round(((float(bar_high) + float(bar_low)) / 2.0) / 0.25)
                      * 0.25, 2)
        stop = float(trade.entry_price)          # child stop at parent BE
        risk = abs(entry - stop) or 1.0
        _t1 = (entry + 1.5 * risk) if _want_long else (entry - 1.5 * risk)
        child = {
            "firing_system": getattr(trade, "firing_system", 2) or 2,
            "direction": trade.direction, "entry_price": entry, "stop": stop,
            "t1": round(_t1, 2), "t2": None, "t3": None,
            "contracts": int(dec["add_contracts"]),
            "classification": "TREND_UPGRADE_ADD",
            "metadata": {"trend_upgrade_parent": getattr(trade, "id", None),
                         "reason": dec["reason"]},
        }
        _mode = getattr(trade, "mode", "live")
        child_id = self._tm.accept_setup(child, _mode)
        try:
            _q = dict(trade.quality) if isinstance(trade.quality, dict) else {}
            _q["trend_upgrade_child_id"] = child_id
            trade.quality = _q
            self._tm._db.commit()
        except Exception:
            pass
        from backend.v9.services.sierra_command import command_from_setup
        _res = command_from_setup(
            child, trade_id=str(child_id),
            account=_tu_os.environ.get("SIERRA_LIVE_ACCOUNT", "37138283"),
            mode=_mode,
        )
        # T-226: same ghost class as ScaleIn — this path is flag-OFF today
        # (TREND_UPGRADE_ADD_V1), so fix it before it can ever ship one.
        if not self._rollback_if_place_refused(_res, child_id, trade,
                                               "TrendUpgrade"):
            return
        logger.warning(
            "[TrendUpgrade] +%dc %s parent=%s child=%s @%.2f stop@%.2f (BE) — %s",
            dec["add_contracts"], trade.direction, getattr(trade, "id", "?"),
            child_id, entry, stop, dec["reason"],
        )

    def _parse_ts(self, ts_raw) -> Optional[datetime]:
        """Parse timestamp from bar data."""
        if isinstance(ts_raw, datetime):
            return ts_raw
        if isinstance(ts_raw, (int, float)):
            return datetime.fromtimestamp(ts_raw, tz=timezone.utc)
        if isinstance(ts_raw, str) and ts_raw:
            try:
                return datetime.fromisoformat(ts_raw)
            except ValueError:
                pass
        return None

    def _notify_trade_close(self, trade, outcome: str) -> None:
        """Notify the gateway that a trade closed → free demo/live slot."""
        if self._gateway is None:
            return
        try:
            trade_id = trade.id
            mode = getattr(trade, "mode", "shadow")
            pnl = getattr(trade, "pnl_usd", 0.0) or 0.0
            direction = getattr(trade, "direction", "")
            self._gateway.on_trade_close({
                "trade_id": trade_id,
                "mode": mode,
                "pnl_usd": pnl,
                "outcome": outcome,
                "direction": direction,
            })
            logger.info("[BarLevelDetector] notified gateway: trade %d closed (%s, mode=%s)",
                        trade_id, outcome, mode)
        except Exception as e:
            logger.warning("[BarLevelDetector] gateway notify failed (non-fatal): %s", e)

    def get_stats(self) -> dict:
        """T-252: cost of the per-bar loop, measured in code and split by mode.

        `us_per_trade` is the number that settles "does the shadow book slow
        the bar processor" — the log could not, because BarRouter prints a
        handler's time only above 100ms (truncated distribution) and reports
        one number for shadow and live together.
        """
        def _per(mode):
            n = self._mode_trades[mode]
            return round(self._mode_secs[mode] / n * 1e6, 1) if n else None
        return {
            "bars_processed": self._bars_processed,
            "loop_bars": self._loop_bars,
            "loop_ms_mean": (round(self._loop_ms_total / self._loop_bars, 2)
                             if self._loop_bars else None),
            "loop_ms_max": round(self._loop_ms_max, 2),
            "open_by_mode": dict(self._open_by_mode),
            "trade_visits": dict(self._mode_trades),
            "us_per_trade": {"shadow": _per("shadow"), "live": _per("live")},
            "secs_by_mode": {k: round(v, 4) for k, v in self._mode_secs.items()},
            "unexecutable_corrections": self._unexec_count,
            "unexecutable_ops": sorted({k[1] for k in self._unexec_ops}),
        }
