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
            if _s6_os.getenv("FIXED_CONTRACTS_4", "0").lower() in ("1", "true", "yes"):
                _exp = 4  # Michael 2026-07-15
            elif _s6_os.getenv("FIXED_CONTRACTS_2", "0").lower() in ("1", "true", "yes"):
                _exp = 2
            elif _s6_os.getenv("FIXED_CONTRACTS_3", "0").lower() in ("1", "true", "yes"):
                _exp = 3
            else:
                _exp = None

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
                logger.warning("[System6] correction %s needs manual handling (advisory)", op)
                return False

            # Feed the live reconcile truth in — this is what makes System 6 catch a
            # phantom (DB open / Sierra flat, e.g. the SIM_TEST trade 297): reconcile says
            # MISMATCH → System 6 raises a CRITICAL reconcile_mismatch on the "active" trade.
            _rv = reconcile_verdict
            _mismatch = bool(getattr(_rv, "mismatch", False)) if _rv is not None else False
            _verdict_str = getattr(_rv, "verdict", None) if _rv is not None else None

            scan_active_trade(
                trade=_t,
                atr=0.0,  # TODO wire a real ATR; 0 → diagnose_trade safe floor=1.0 / cap=25pt
                t1_hit=getattr(trade, "t1_hit_ts", None) is not None,
                expected_contracts=_exp,
                now_ct_min=_now_ct,
                reconcile_verdict=_verdict_str,
                reconcile_mismatch=_mismatch,
                executor=_exec,
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
            if getattr(v, "mismatch", False) or getattr(v, "naked_stop_suspect", False):
                logger.critical("[Reconcile-live] %s — %s", v.verdict, getattr(v, "detail", ""))
                # W3 (2026-07-25): immediate phone escalation — not just a log line.
                # A naked stop is a live-risk event (position without protection).
                if getattr(v, "naked_stop_suspect", False):
                    try:
                        from backend.v9.services.phone_alert import push as _pp
                        _pp("naked_stop_reconcile",
                            "\U0001f534 MEMS26: NAKED STOP SUSPECT",
                            f"Reconcile-live: {getattr(v, 'detail', 'stop not confirmed')}",
                            priority=1)
                    except Exception:
                        pass
            return v
        except Exception as _rc_err:  # never let reconcile break trade management
            logger.warning("[BarLevelDetector] reconcile-live error (fail-safe skip): %s", _rc_err)
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

            # Trend runner flatten at 15:45 ET (flag-gated C4_TREND_FLATTEN_V1, OFF).
            self._trend_runner_flatten(active)
            # EOD auto-flatten at RTH close (flag-gated EOD_FLATTEN_V1, default OFF).
            self._eod_flatten(active)
            # Reconcile slot↔DB↔Sierra while in a position (flag-gated RECONCILE_LIVE_V1, OFF).
            # Capture the verdict so System 6 folds the DB↔Sierra truth into its diagnosis.
            _recon_v = self._reconcile_live()

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

            for trade in active:
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
                    # Dynamic structure-trail (DYNAMIC_STRUCT_TRAIL) — runs INSTEAD of
                    # the simple hwm trail when ON; falls back to hwm trail when OFF.
                    if _trail_os.getenv("DYNAMIC_STRUCT_TRAIL", "0").lower() in ("1", "true", "yes"):
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
                            from backend.v9.services.sierra_command import write_trade_command
                            write_trade_command(
                                action="FLATTEN_ACCOUNT",
                                context={"source": "target_approach_realize",
                                         "trade_id": str(trade.id), "reason": _tar_reason})
                            self._tm.close_trade(trade.id, reason="TARGET_APPROACH_REALIZE")
                    except Exception as _tar_err:
                        logger.debug("[BarLevelDetector] target-approach error (fail-safe): %s", _tar_err)

                # S6 MAE scratch (DEV_PLAN 02.08 §P3.1): adverse excursion ≥
                # per-pattern threshold before T1 → FLATTEN. Flag-gated
                # S6_MAE_SCRATCH_V1 (OFF). Never op=EXIT. Fail-safe.
                if _is_demo_live:
                    try:
                        from backend.v9.systems.mae_scratch import should_scratch
                        _q = trade.quality if isinstance(getattr(trade, "quality", None), dict) else {}
                        _pat = _q.get("pattern_name", _q.get("setup_type", ""))
                        _scratch, _scratch_reason = should_scratch(
                            pattern_name=_pat,
                            entry_price=float(trade.entry_price),
                            direction=direction,
                            bar_low=bar_low,
                            bar_high=bar_high,
                            t1_hit=trade.t1_hit_ts is not None,
                            stop_price=float(trade.stop) if trade.stop else None,
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
                            try:
                                from backend.v9.services.sierra_command import (
                                    write_trade_command as _mae_write,
                                )
                                _mae_write(
                                    action="FLATTEN_ACCOUNT",
                                    context={"source": "mae_scratch",
                                             "trade_id": str(trade.id),
                                             "reason": _scratch_reason})
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
                            self._tm.close_trade(trade.id, reason="MAE_SCRATCH")
                            if self._gateway:
                                try:
                                    self._gateway.on_trade_close({
                                        "trade_id": trade.id,
                                        "mode": getattr(trade, "mode", "demo"),
                                        "pnl_usd": 0.0,
                                        "outcome": "SCRATCH",
                                        "direction": direction,
                                    })
                                except Exception:
                                    pass
                            try:
                                from scripts.ops_log import log_event
                                log_event("mae_scratch", "WARNING", _scratch_reason)
                            except Exception:
                                pass
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
        cfg = ScaleInCfg(
            min_profit_pts=float(_si_os.getenv("SCALE_IN_MIN_PROFIT_PTS", "6") or 6),
            add_contracts=int(_si_os.getenv("SCALE_IN_ADD_CONTRACTS", "2") or 2),
            max_total_contracts=int(_si_os.getenv("SCALE_IN_MAX_TOTAL", "8") or 8),
        )
        dir_bias = None
        try:
            from backend.v9.services.trade_context import get_live_dir_bias
            dir_bias = get_live_dir_bias()
        except Exception:
            pass
        try:
            from backend.v9.services.trade_manager.manager import trade_contract_count
            n_open = int(trade_contract_count(trade))
        except Exception:
            n_open = 2
        dec = should_scale_in(
            direction=trade.direction, entry_price=float(trade.entry_price),
            t1_hit=True, already_scaled=False, n_contracts_open=n_open,
            bar_high=float(bar_high), bar_low=float(bar_low),
            dir_bias=dir_bias, cfg=cfg,
        )
        if dec is None:
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
        from backend.v9.services.sierra_command import command_from_setup
        command_from_setup(
            child, trade_id=str(child_id),
            account=_si_os.environ.get("SIERRA_LIVE_ACCOUNT", "37138283"), mode=_mode,
        )
        logger.warning(
            "[ScaleIn] +%dc %s parent=%s child=%s @%.2f stop@%.2f (BE) — %s",
            dec.add_contracts, dec.direction, getattr(trade, "id", "?"),
            child_id, dec.entry, dec.stop, dec.reason,
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
        return {"bars_processed": self._bars_processed}
