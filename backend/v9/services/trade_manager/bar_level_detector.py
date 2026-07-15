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

            # EOD auto-flatten at RTH close (flag-gated EOD_FLATTEN_V1, default OFF).
            self._eod_flatten(active)
            # Reconcile slot↔DB↔Sierra while in a position (flag-gated RECONCILE_LIVE_V1, OFF).
            # Capture the verdict so System 6 folds the DB↔Sierra truth into its diagnosis.
            _recon_v = self._reconcile_live()

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
