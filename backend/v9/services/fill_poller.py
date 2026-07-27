"""Fill poller — reads trade_fills.json from Sierra DLL and drives TradeManager.

Pipeline 5 Phase B: when MEMS26_MODE=demo, polls trade_fills.json for fill events
(ENTRY, T1, T2, T3, STOP) written by the DLL on order fills. Maps sierra_order_id
↔ trade_id and calls TradeManager.on_fill/on_target_hit/on_stop_hit with Sierra
prices (not bar prices).

Does NOT run in SHADOW mode (SHADOW uses bar_level_detector for management).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("fill_poller")

FILLS_PATH = Path(os.getenv(
    "TRADE_FILLS_PATH",
    "/Users/michael/SierraChart_Data/v9_export/trade_fills.json",
))
POLL_INTERVAL = 0.25  # seconds

# Anti-duplicate guard: Wine can fail to truncate trade_command.json (same root as the
# 06-25 feed-freeze) → the DLL re-reads the command and re-places (observed 06-26: one
# command → 2 orders, 6s apart). Defense: once a RESULT ack exists for the current command
# (result mtime >= command mtime), clear the command NATIVELY (fast, no Wine). Polled at
# 0.25s; the DLL's re-read is ~bars/seconds → the native clear wins the race.
_SIGNALS_DIR = Path(os.getenv("MEMS26_SIGNALS_DIR", "/Users/michael/SierraChart_Data/v9_export"))
COMMAND_PATH = _SIGNALS_DIR / "trade_command.json"
RESULT_PATH = _SIGNALS_DIR / "trade_result.json"
ACTIVITY_EVENTS_PATH = _SIGNALS_DIR / "trade_activity_events.jsonl"
STATE_PATH = _SIGNALS_DIR / "sierra_state.json"

# MES point value — shared with trade_manager for exit_price back-computation
_MES_POINT_VALUE = 5.0  # $5 per point per contract


class FillPoller:
    """Async poller that reads trade_fills.json and drives TradeManager."""

    def __init__(self, trade_manager=None, gateway=None):
        self._tm = trade_manager
        self._gateway = gateway
        self._running = False
        self._last_mtime: float = 0.0
        self._last_result_mtime: float = 0.0
        self._processed_count = 0
        # P3 heartbeat: wall-time of the last loop iteration. The loop already
        # continues-on-exception, but if the whole task dies (cancel, event-loop
        # death) fills stop silently. post_restart_verify / feed liveness reads
        # this to detect a dead poller.
        self._last_poll_ts: float = 0.0
        # Map sierra_order_id → trade_id (set when command is written)
        self._order_map: Dict[int, int] = {}
        # P1.2 (2026-07-07): orphan fills — a Sierra fill with no trade to attribute.
        # Recorded + surfaced (never silent) for the reconcile / System 6 orphan invariant.
        self._orphan_fills: list = []
        self._orphan_count: int = 0
        # W2 (2026-07-25): activity-exit tracker — incremental read position in
        # trade_activity_events.jsonl for CLOSED_TRADE_PNL detection.
        self._activity_exit_pos: Optional[int] = None
        # POSITION_TRUTH_SYNC_V1: when Sierra first reported flat (grace timer)
        self._flat_since: Optional[float] = None

    def last_poll_age(self) -> float:
        """Seconds since the loop last iterated (P3 heartbeat). -1 if never run.
        A large value during RTH means the poller task died → fills stop silently."""
        return (time.time() - self._last_poll_ts) if self._last_poll_ts > 0 else -1.0

    def set_trade_manager(self, tm) -> None:
        self._tm = tm

    def set_gateway(self, gw) -> None:
        """Wire the TradingGateway so Sierra-driven closes free slots + feed
        cooldown/SSV counters (I-57: FillPoller closes bypassed on_trade_close —
        trades 271/272 left the demo slot stuck + stops uncounted)."""
        self._gateway = gw

    def _notify_gateway_close(self, trade_id, outcome: str) -> None:
        """Tell the gateway a trade fully closed (STOP / T3). Fail-safe, never raises."""
        if self._gateway is None:
            return
        try:
            trade = self._tm._get_trade(trade_id) if self._tm is not None else None
            self._gateway.on_trade_close({
                "trade_id": trade_id,
                "mode": getattr(trade, "mode", "demo") if trade else "demo",
                "pnl_usd": (getattr(trade, "pnl_usd", 0.0) or 0.0) if trade else 0.0,
                "outcome": outcome,
                "direction": getattr(trade, "direction", "") if trade else "",
            })
            logger.info("[FillPoller] notified gateway: trade %s closed (%s)", trade_id, outcome)
        except Exception as e:
            logger.warning("[FillPoller] gateway notify failed (non-fatal): %s", e)

    def register_order(self, sierra_order_id: int, trade_id: int) -> None:
        """Map a Sierra order ID to a MEMS26 trade ID."""
        self._order_map[sierra_order_id] = trade_id
        logger.info("[FillPoller] registered order %d → trade %d", sierra_order_id, trade_id)

    async def run(self) -> None:
        """Main polling loop — run as an asyncio task."""
        self._running = True
        self._reconcile_next = 0.0  # epoch: next reconcile check
        logger.info("[FillPoller] started (polling %s every %.0fms)", FILLS_PATH, POLL_INTERVAL * 1000)
        while self._running:
            try:
                await asyncio.sleep(POLL_INTERVAL)
                self._last_poll_ts = time.time()  # P3 heartbeat
                self._guard_duplicate_command()
                self._check_result()
                self._check_fills()
                self._check_activity_exits()
                self._sync_position_truth()
                self._maybe_reconcile()
                self._check_rejections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("[FillPoller] poll error (continuing): %s", e)
        logger.info("[FillPoller] stopped")

    def stop(self) -> None:
        self._running = False

    def _sync_position_truth(self) -> None:
        """POSITION_TRUTH_SYNC_V1 (2026-07-27, Michael: "המערכת לא מסמנת מתי יש
        עסקה ומתי אין"). Sierra's own net position is the truth; our bookkeeping
        must follow it, in BOTH directions:

          • Sierra HOLDS a position + our trade is PENDING  → mark it FILLED
            (a MARKET entry Sierra ACKed is open; the entry-fill line that would
            normally flip the state never arrives — the deployed DLL leaves
            trade_fills.json empty).
          • Sierra is FLAT + we still believe a trade is open (PENDING/FILLED)
            past a grace window → close it as SIERRA_FLAT and free the slot.

        Why a grace window: an entry ACKed a second ago can legitimately show
        position 0 for one poll. Grace (default 20s) prevents closing a trade
        that is still filling.

        Fail-safe: needs a FRESH state file (≤10s) — stale/unknown does nothing
        (never invent a fill, never invent a close; Rule 1). Never raises.
        """
        if not os.getenv("POSITION_TRUTH_SYNC_V1", "0").lower() in ("1", "true", "yes"):
            return
        if self._tm is None:
            return
        try:
            from backend.v9.services.sierra_position_reconciler import (
                _sierra_state_avg_price as _sq_avg, _sierra_state_qty as _sq_qty,
            )
            qty = _sq_qty()
            if qty is None:
                return  # stale/missing → honest no-op
            grace = float(os.getenv("POSITION_TRUTH_GRACE_S", "20"))
            now = time.time()
            open_trades = [t for t in self._tm.get_active_trades()
                           if getattr(t, "state", "") in ("PENDING", "FILLED")
                           and getattr(t, "mode", "shadow") in ("demo", "live", "SIM")]
            if not open_trades:
                return

            if qty != 0:
                # Sierra holds a position → any PENDING trade of ours is open.
                avg = _sq_avg()
                for t in open_trades:
                    if getattr(t, "state", "") != "PENDING":
                        continue
                    px = avg or getattr(t, "entry_price", None)
                    if px is None:
                        continue
                    try:
                        self._tm.on_fill(t.id, float(px))
                        try:
                            self._tm._db.commit()
                        except Exception:
                            pass
                        logger.warning(
                            "[FillPoller] POSITION_TRUTH: Sierra holds %sc → trade %s "
                            "PENDING→FILLED @%.2f (entry-fill line never arrived)",
                            qty, t.id, float(px))
                    except Exception as e:
                        logger.warning("[FillPoller] POSITION_TRUTH on_fill(%s) failed: %s",
                                       t.id, e)
                self._flat_since = None
                return

            # Sierra is FLAT — start/continue the grace timer, then close.
            if self._flat_since is None:
                self._flat_since = now
                return
            if (now - self._flat_since) < grace:
                return
            for t in open_trades:
                age = None
                try:
                    _ct = getattr(t, "created_at", None)
                    if _ct is not None:
                        age = (time.time() - _ct.timestamp())
                except Exception:
                    age = None
                if age is None or age < grace:
                    # Just created (or age unknown) — let it fill. Unknown age is
                    # treated as "too young to close": closing a trade we cannot
                    # date is the dangerous direction (Rule 1 / fail-safe).
                    continue
                _state_before = getattr(t, "state", "?")
                try:
                    self._tm.close_trade(t.id, "SIERRA_FLAT")
                    # TradeManager does NOT auto-commit (the gateway commits
                    # explicitly after accept_setup). Without this the close
                    # lived only in memory: the DB row stayed FILLED and the
                    # sync re-closed the same trade every poll, forever.
                    try:
                        self._tm._db.commit()
                    except Exception as _ce:
                        logger.warning("[FillPoller] POSITION_TRUTH commit failed for %s: %s",
                                       t.id, _ce)
                    self._notify_gateway_close(t.id, "SIERRA_FLAT")
                    logger.warning(
                        "[FillPoller] POSITION_TRUTH: Sierra FLAT for %.0fs → closed "
                        "trade %s (was %s) + freed slot", now - self._flat_since,
                        t.id, _state_before)
                except Exception as e:
                    logger.warning("[FillPoller] POSITION_TRUTH close(%s) failed: %s", t.id, e)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("[FillPoller] POSITION_TRUTH sync errored (non-fatal): %s", e)

    def _check_activity_exits(self) -> None:
        """W2 (trade 513, 2026-07-25): detect bracket exits via CLOSED_TRADE_PNL
        events in trade_activity_events.jsonl.

        The deployed DLL (v8.2.0) does NOT write exit fills (T1/T2/T3/STOP) to
        trade_fills.json — only the undeployed _merged.cpp has Pipeline 5 fill
        monitor. Until that DLL is deployed, bracket exits are invisible to
        _check_fills(). This fallback reads CLOSED_TRADE_PNL events from the
        activity journal (which the DLL DOES write) and closes the matching
        trade with Sierra's authoritative PnL.

        Flag-gated: EXIT_TRACK_ACTIVITY_V1 (default OFF). When OFF, this method
        is a no-op (byte-identical to pre-W2).

        Correlation: CLOSED_TRADE_PNL carries pnl + ts but NO order_id →
        attributed to the most recent FILLED non-shadow trade (same single-slot
        heuristic as ORDER_FAILED). Confirmed via sierra_state.json position_qty=0
        before acting (double-check: Sierra is actually flat).
        """
        if not os.getenv("EXIT_TRACK_ACTIVITY_V1", "0").lower() in ("1", "true", "yes"):
            return
        if self._tm is None:
            return
        if not ACTIVITY_EVENTS_PATH.exists():
            return
        try:
            size = ACTIVITY_EVENTS_PATH.stat().st_size
            if self._activity_exit_pos is None:
                # First run: start at EOF — never act on historical events
                self._activity_exit_pos = size
                return
            if size <= self._activity_exit_pos:
                if size < self._activity_exit_pos:
                    self._activity_exit_pos = 0  # file rotated/truncated
                return
            with open(ACTIVITY_EVENTS_PATH, "r", encoding="utf-8") as f:
                f.seek(self._activity_exit_pos)
                new_lines = f.read().splitlines()
            self._activity_exit_pos = size

            # Collect CLOSED_TRADE_PNL events from new lines
            pnl_events = []
            for ln in new_lines:
                try:
                    ev = json.loads(ln)
                except (ValueError, TypeError):
                    continue
                if ev.get("type") == "CLOSED_TRADE_PNL":
                    pnl_events.append(ev)
            if not pnl_events:
                return

            # POSITION_TRUTH_SYNC_V1 (2026-07-27, Michael: "המערכת לא מסמנת
            # מתי יש עסקה ומתי אין"): accept PENDING too. A MARKET entry that
            # Sierra ACKed is de-facto open — but the entry-fill line that would
            # flip PENDING→FILLED never arrives (trade_fills.json stays empty on
            # the deployed DLL). Requiring FILLED meant every close was ignored,
            # trades piled up as phantoms, the slot stuck, and the reconcile then
            # screamed NAKED_STOP at a flat account. Sierra-flat is verified
            # below before anything is closed, so accepting PENDING cannot close
            # a live position.
            # Find active FILLED non-shadow trade
            filled = [t for t in self._tm.get_active_trades()
                      if getattr(t, "state", "") in ("FILLED", "PENDING")
                      and getattr(t, "mode", "shadow") in ("demo", "live", "SIM")]
            if not filled:
                logger.warning(
                    "[FillPoller] W2 CLOSED_TRADE_PNL seen (%d events) but no open "
                    "demo/live trade — manual close or already processed",
                    len(pnl_events))
                return

            # Double-check: sierra_state.json says position is flat
            try:
                if STATE_PATH.exists():
                    import re as _re
                    _raw = STATE_PATH.read_text().strip() or "{}"
                    state_data = json.loads(_re.sub(r':\s*-?inf\b', ':null', _raw))
                    sq = state_data.get("position_qty")
                    if sq is not None and int(sq) != 0:
                        logger.warning(
                            "[FillPoller] W2 CLOSED_TRADE_PNL but Sierra position_qty=%s "
                            "(not flat) — waiting for full exit", sq)
                        return
                else:
                    logger.warning("[FillPoller] W2 sierra_state.json missing — skipping")
                    return
            except (OSError, json.JSONDecodeError, ValueError):
                return

            # SUM all PnL events in this batch — the DLL writes one
            # CLOSED_TRADE_PNL per contract, so a 2-contract exit produces
            # two events (e.g. [-198.75, -607.5] → total -806.25). Taking
            # only the last event (the pre-fix bug) under-counts multi-contract
            # exits and breaks RISK_HALT accounting.
            sierra_pnl = sum(
                float(ev.get("pnl", 0)) for ev in pnl_events
                if ev.get("pnl") is not None
            )
            # Use the last event's timestamp (all events in a bracket exit
            # share the same ts, but last is safest)
            exit_ts_str = pnl_events[-1].get("ts")
            exit_ts = None
            if exit_ts_str:
                try:
                    exit_ts = datetime.fromisoformat(exit_ts_str)
                    if exit_ts.tzinfo is None:
                        exit_ts = exit_ts.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    exit_ts = datetime.now(timezone.utc)
            else:
                exit_ts = datetime.now(timezone.utc)

            trade = filled[-1]
            trade_id = trade.id
            entry_price = getattr(trade, "entry_price", None)
            direction = str(getattr(trade, "direction", "")).upper()

            # Back-compute exit_price from Sierra PnL when possible (Rule 1:
            # honest None when data insufficient — never synthesize a lie)
            exit_price = None
            if sierra_pnl is not None and entry_price is not None:
                from backend.v9.services.trade_manager.manager import trade_contract_count
                n_contracts = trade_contract_count(trade)
                if n_contracts > 0:
                    pnl_per_contract = float(sierra_pnl) / n_contracts
                    pts = pnl_per_contract / _MES_POINT_VALUE
                    if direction == "LONG":
                        exit_price = round(float(entry_price) + pts, 2)
                    elif direction == "SHORT":
                        exit_price = round(float(entry_price) - pts, 2)

            logger.warning(
                "[FillPoller] W2 EXIT-TRACK: CLOSED_TRADE_PNL detected — closing "
                "trade %d (%s %s) with Sierra PnL=$%s, exit_price=%s, ts=%s",
                trade_id, getattr(trade, "mode", "?"), direction,
                sierra_pnl, exit_price, exit_ts,
            )

            # Close the trade via on_stop_hit (which sets all exit fields correctly)
            # If we have a computed exit_price, use it; Sierra PnL overrides
            # the manager's calculated PnL afterward.
            try:
                self._tm.on_stop_hit(trade_id, fill_ts=exit_ts, fill_price=exit_price)
                # Override PnL with Sierra's authoritative value (the manager
                # computes PnL from exit_price which may have rounding; Sierra's
                # is ground truth per Rule 2).
                if sierra_pnl is not None:
                    trade.pnl_usd = float(sierra_pnl)
                    trade.pnl_sierra = float(sierra_pnl)
                    trade.exit_reason = "BRACKET_EXIT_ACTIVITY"
                    self._tm._set_outcome(trade)
                    try:
                        self._tm._db.flush()
                    except Exception:
                        pass
            except Exception as e:
                # Fallback: if on_stop_hit fails (e.g. state machine won't
                # transition), use close_trade which is more permissive.
                logger.warning(
                    "[FillPoller] W2 on_stop_hit failed for %d: %s — trying close_trade",
                    trade_id, e)
                try:
                    self._tm.close_trade(
                        trade_id,
                        reason="BRACKET_EXIT_ACTIVITY",
                        exit_price=exit_price,
                    )
                    if sierra_pnl is not None:
                        trade.pnl_usd = float(sierra_pnl)
                        trade.pnl_sierra = float(sierra_pnl)
                        try:
                            self._tm._db.flush()
                        except Exception:
                            pass
                except Exception as e2:
                    logger.error(
                        "[FillPoller] W2 close_trade also failed for %d: %s", trade_id, e2)
                    return

            # Free the gateway slot
            self._notify_gateway_close(trade_id, "BRACKET_EXIT_ACTIVITY")

            logger.warning(
                "[FillPoller] W2 EXIT-TRACK: trade %d CLOSED via activity fallback — "
                "PnL=$%s outcome=%s exit_price=%s",
                trade_id, trade.pnl_usd, trade.outcome, trade.exit_price,
            )
            # OPS_LOG
            try:
                from scripts.ops_log import log_event
                log_event("fill_poller", "WARNING",
                          f"W2 EXIT-TRACK: trade {trade_id} closed via CLOSED_TRADE_PNL "
                          f"fallback — PnL=${sierra_pnl}, exit={exit_price}")
            except Exception:
                pass

        except Exception as e:
            logger.debug("[FillPoller] _check_activity_exits error (fail-safe): %s", e)

    def _maybe_reconcile(self) -> None:
        """FIX-6 (SYS-3): compare TM vs Sierra position every ≤30s.

        Flag-gated: SIERRA_RECONCILER_V1 (default OFF — Michael enables at restart).
        Fail-safe: errors never break the fill-poller loop.
        """
        if time.time() < getattr(self, "_reconcile_next", 0.0):
            return
        self._reconcile_next = time.time() + 30.0
        if not os.getenv("SIERRA_RECONCILER_V1", "0").lower() in ("1", "true", "yes"):
            return
        if self._tm is None:
            return
        try:
            from backend.v9.services.sierra_position_reconciler import reconcile_position
            ok, msg = reconcile_position(self._tm)
            if not ok:
                logger.warning("[FillPoller] SYS-3 RECONCILER: %s", msg)
            else:
                logger.debug("[FillPoller] reconciler: %s", msg)
        except Exception as e:
            logger.debug("[FillPoller] reconciler error (fail-safe): %s", e)

    def _check_rejections(self) -> None:
        """FIX-10 (ORDER_REJECT_DETECT_V1, default OFF — trade 337, 2026-07-10):
        an ASYNC broker rejection (margin etc.) arrives AFTER the submit-ack, so
        _check_result's ORDER_FAILED path never sees it — 337 was recorded
        CLOSED/BE despite Sierra rejecting order 8700. The activity feeder now
        emits ORDER_REJECT events; here we correlate one to the submit-acked
        PENDING demo/live trade that has NO entry fill → honest REJECTED:
        state=CANCELLED, outcome=REJECTED, pnl 0, slot released, CRITICAL log.
        FILLED trades are never touched (that's the 308 naked-bracket family).
        """
        if not os.getenv("ORDER_REJECT_DETECT_V1", "0").lower() in ("1", "true", "yes"):
            return
        if self._tm is None:
            return
        events_path = _SIGNALS_DIR / "trade_activity_events.jsonl"
        if not events_path.exists():
            return
        try:
            size = events_path.stat().st_size
            last_pos = getattr(self, "_rej_events_pos", None)
            if last_pos is None:
                # first run: start at EOF — never act on historical rejections
                self._rej_events_pos = size
                return
            if size <= last_pos:
                if size < last_pos:
                    self._rej_events_pos = 0  # file rotated/truncated
                return
            with open(events_path, "r", encoding="utf-8") as f:
                f.seek(last_pos)
                new_lines = f.read().splitlines()
            self._rej_events_pos = size
            rejects = []
            for ln in new_lines:
                try:
                    ev = json.loads(ln)
                except (ValueError, TypeError):
                    continue
                if ev.get("type") == "ORDER_REJECT":
                    rejects.append(ev)
            if not rejects:
                return
            reason = (rejects[-1].get("reason") or "")[:80]
            pending = [t for t in self._tm.get_active_trades()
                       if getattr(t, "state", "") == "PENDING"
                       and getattr(t, "mode", "shadow") in ("demo", "live")]
            if not pending:
                logger.warning(
                    "[FillPoller] FIX-10 ORDER_REJECT seen (%s) but no PENDING "
                    "demo/live trade to correlate — manual order? logged only.", reason)
                return
            trade = pending[-1]
            logger.critical(
                "[FillPoller] FIX-10 BROKER REJECTION: trade %d (%s) rejected by "
                "Sierra AFTER submit-ack — reason: %s → state=CANCELLED, "
                "outcome=REJECTED, slot released, zero P&L impact.",
                trade.id, getattr(trade, "mode", "?"), reason)
            try:
                self._tm.close_trade(trade.id, reason=f"REJECTED:{reason}"[:30])
                trade.state = "CANCELLED"
                trade.pnl_usd = 0.0
                trade.outcome = "REJECTED"
                q = dict(trade.quality) if isinstance(getattr(trade, "quality", None), dict) else {}
                q["reject_reason"] = reason
                trade.quality = q
                try:
                    self._tm._db.flush()
                except Exception:
                    pass
            except Exception as e:
                logger.warning("[FillPoller] FIX-10 reject-close failed for %d: %s", trade.id, e)
            self._notify_gateway_close(trade.id, "REJECTED")
        except Exception as e:
            logger.debug("[FillPoller] _check_rejections error (fail-safe): %s", e)

    def _check_result(self) -> None:
        """Check trade_result.json for ORDER_FAILED → cancel trade + release slot.

        When Sierra rejects an order (error -1 etc.), the gateway already created a
        PENDING trade and occupied the live_slot (or demo_slot). Without this handler,
        the phantom trade blocks all future fires until manual cleanup.
        """
        if not RESULT_PATH.exists():
            return
        try:
            mtime = RESULT_PATH.stat().st_mtime
            if mtime <= self._last_result_mtime:
                return
            self._last_result_mtime = mtime

            content = RESULT_PATH.read_text().strip()
            if not content:
                return
            result = json.loads(content)
            status = result.get("status")

            # L2-residual/L4 (2026-07-08): register the order-id map at SUBMIT
            # time — do NOT wait for the ENTRY fill (which resolves via the
            # I-58 "most recent active" fallback when unmapped).
            if status == "ORDER_SUBMITTED":
                self._register_submitted_order(result)
                return

            # W3 (2026-07-25): MODIFY_STOP_NONE → retry the stop modification.
            # The DLL returns MODIFY_STOP_NONE when stop_ids are stale/empty or the
            # bracket stop isn't in working state yet. This overwrites ORDER_SUBMITTED
            # in trade_result.json, causing NAKED_STOP_SUSPECT for the trade's entire
            # life. Fix: when flagged ON, re-send MODIFY_STOP with fresh stop IDs.
            # Flag-gated: STOP_RETRY_ON_NONE_V1 (default OFF).
            if status == "MODIFY_STOP_NONE":
                self._handle_modify_stop_none()
                return

            if status != "ORDER_FAILED":
                return

            err_code = result.get("error", "?")
            err_text = result.get("error_text", "unknown")
            logger.warning(
                "[FillPoller] ORDER_FAILED from Sierra: error=%s (%s) — cancelling pending trade + releasing slot",
                err_code, err_text,
            )

            # Find the most recent PENDING trade (demo or live) and cancel it
            if self._tm is not None:
                active = self._tm.get_active_trades()
                pending = [t for t in active
                           if getattr(t, "state", "") == "PENDING"
                           and getattr(t, "mode", "shadow") in ("demo", "live")]
                if pending:
                    trade = pending[-1]  # most recent
                    # SYS-3 guard (2026-07-08 live incident, trade 308/310): if the
                    # trade ALREADY has a Sierra parent id (ORDER_SUBMITTED was
                    # acked), a later bare ORDER_FAILED is most likely a CHILD
                    # (stop/target) failure — cancelling the trade row here
                    # ORPHANED a real Sierra position (backend cancelled 308 while
                    # Sierra held it; Michael had to flatten manually). Do NOT
                    # cancel a submitted trade: scream NAKED-BRACKET instead and
                    # let reconcile/System-6/Michael act on the position.
                    _q = trade.quality if isinstance(getattr(trade, "quality", None), dict) else {}
                    if _q.get("sierra_order_id"):
                        logger.critical(
                            "[FillPoller] ORDER_FAILED after SUBMIT-ack for trade %d "
                            "(parent %s) — likely a CHILD order failure. NOT cancelling "
                            "the trade. NAKED-BRACKET SUSPECT: verify the Sierra stop NOW.",
                            trade.id, _q.get("sierra_order_id"),
                        )
                        RESULT_PATH.write_text("")
                        return
                    try:
                        # Truncate reason to fit varchar(30)
                        _reason = f"ORDER_FAILED:{err_code}"[:30]
                        # P8 fix (2026-07-22): use outcome_override="CANCELLED" so
                        # close_trade persists the correct outcome in one flush (not
                        # the PnL-based "BE" that _set_outcome would compute on pnl=0).
                        # Also set state to CANCELLED for honest display.
                        self._tm.close_trade(
                            trade.id,
                            reason=_reason,
                            outcome_override="CANCELLED",
                        )
                        trade.state = "CANCELLED"
                        try:
                            self._tm._db.flush()
                        except Exception:
                            pass
                        logger.warning(
                            "[FillPoller] CANCELLED trade %d (mode=%s) due to ORDER_FAILED",
                            trade.id, getattr(trade, "mode", "?"),
                        )
                    except Exception as e:
                        logger.warning("[FillPoller] failed to cancel trade %d: %s", trade.id, e)

                    # Release the gateway slot
                    if self._gateway is not None:
                        self._notify_gateway_close(trade.id, f"ORDER_FAILED:{err_code}")
                else:
                    logger.warning("[FillPoller] ORDER_FAILED but no PENDING trade found to cancel")

            # Clear the result file so we don't re-process
            RESULT_PATH.write_text("")

        except (OSError, json.JSONDecodeError) as e:
            logger.debug("[FillPoller] _check_result error: %s", e)

    def _register_submitted_order(self, result: Dict[str, Any]) -> None:
        """Map Sierra order ids the moment the DLL acks ORDER_SUBMITTED (L2-residual/L4, 2026-07-08).

        The DLL writes parent_id/target_id/stop_id into trade_result.json on
        submit. Registering here means: (a) the ENTRY fill resolves via the map,
        not the I-58 fallback; (b) sierra_order_id persists on the trade
        (quality → DB) immediately, so _emit_modify_stop has its order_id even
        if the ENTRY fill line is delayed/lost — the MODIFY no longer drops
        silently. The ack carries no trade_id (DLL doesn't echo it) → attribute
        to the most recent PENDING non-shadow trade, the same single-slot
        heuristic ORDER_FAILED already uses. The file is NOT cleared here
        (reconcile + /trade_result API also read it; only ORDER_FAILED clears).
        """
        parent_id = result.get("parent_id")
        if not parent_id or self._tm is None:
            return
        if int(parent_id) in self._order_map:
            return  # same ack re-read — already registered
        pending = [t for t in self._tm.get_active_trades()
                   if getattr(t, "state", "") == "PENDING"
                   and getattr(t, "mode", "shadow") in ("demo", "live", "SIM")]
        if not pending:
            logger.warning(
                "[FillPoller] ORDER_SUBMITTED parent_id=%s but no PENDING demo/live trade "
                "to map — the ENTRY fill will need the I-58 fallback", parent_id)
            return
        trade = pending[-1]
        self.register_order(int(parent_id), trade.id)
        for _oid in (result.get("target_id"), result.get("stop_id")):
            if _oid:
                self._order_map[int(_oid)] = trade.id
        try:
            self._tm.set_sierra_order_ids(trade.id, {
                "sierra_order_id": parent_id,
                "c1_target_id": result.get("target_id"),
                "c1_stop_id": result.get("stop_id"),
            })
        except Exception as e:
            logger.warning("[FillPoller] set_sierra_order_ids at submit failed: %s", e)

    def _handle_modify_stop_none(self) -> None:
        """W3 (2026-07-25): MODIFY_STOP_NONE received — the DLL couldn't find/modify
        the stop order(s). This is dangerous: the position may be naked (no stop
        protection). Two responses:

        1. ESCALATION (always): CRITICAL log + phone push so Michael knows immediately.
        2. RETRY (flag-gated STOP_RETRY_ON_NONE_V1): re-send MODIFY_STOP with the
           trade's current stop value and fresh stop IDs from quality JSON. The retry
           uses a 2s delay to let the bracket order settle in Sierra.

        This method is fail-safe — errors never break the fill-poller loop.
        """
        if self._tm is None:
            return
        # Find the active FILLED non-shadow trade
        filled = [t for t in self._tm.get_active_trades()
                  if getattr(t, "state", "") == "FILLED"
                  and getattr(t, "mode", "shadow") in ("demo", "live", "SIM")]
        if not filled:
            logger.warning(
                "[FillPoller] W3 MODIFY_STOP_NONE but no FILLED demo/live trade — "
                "stale result or manual order")
            return

        trade = filled[-1]
        stop_val = getattr(trade, "stop", None)

        # ESCALATION (always — not flag-gated): CRITICAL log + phone push
        logger.critical(
            "[FillPoller] W3 NAKED_STOP: MODIFY_STOP_NONE for trade %d (%s %s) — "
            "stop modification failed, position may be unprotected. stop=%s",
            trade.id, getattr(trade, "mode", "?"),
            getattr(trade, "direction", "?"), stop_val,
        )
        try:
            from backend.v9.services.phone_alert import push as _phone_push
            _phone_push(
                "naked_stop_modify",
                "\U0001f534 MEMS26: NAKED STOP",
                f"MODIFY_STOP_NONE for trade {trade.id} — stop not confirmed. "
                f"Verify Sierra stop manually.",
                priority=1,
            )
        except Exception:
            pass
        try:
            from scripts.ops_log import log_event
            log_event("fill_poller", "CRITICAL",
                      f"W3 MODIFY_STOP_NONE: trade {trade.id} stop={stop_val} — "
                      f"position may be naked")
        except Exception:
            pass

        # RETRY (flag-gated)
        if not os.getenv("STOP_RETRY_ON_NONE_V1", "0").lower() in ("1", "true", "yes"):
            return
        if stop_val is None:
            logger.warning("[FillPoller] W3 retry skipped: trade %d has no stop value", trade.id)
            return

        # Throttle: max 1 retry per trade per 10s
        _retry_key = f"stop_retry_{trade.id}"
        _last = getattr(self, "_stop_retry_ts", {}).get(_retry_key, 0)
        if time.time() - _last < 10.0:
            return
        if not hasattr(self, "_stop_retry_ts"):
            self._stop_retry_ts = {}
        self._stop_retry_ts[_retry_key] = time.time()

        try:
            self._tm._emit_modify_stop(trade, float(stop_val))
            logger.warning(
                "[FillPoller] W3 RETRY: re-sent MODIFY_STOP for trade %d stop=%s",
                trade.id, stop_val,
            )
        except Exception as e:
            logger.warning("[FillPoller] W3 MODIFY_STOP retry failed: %s", e)

    def _guard_duplicate_command(self) -> None:
        """Clear trade_command.json natively once the DLL has acked it (result mtime >=
        command mtime), so the DLL cannot re-read + re-place the same command. Wine-safe
        defense against the observed double-placement (see module header)."""
        try:
            if not COMMAND_PATH.exists():
                return
            cstat = COMMAND_PATH.stat()
            if cstat.st_size <= 10:
                return  # already empty / cleared
            if not RESULT_PATH.exists():
                return
            if RESULT_PATH.stat().st_mtime >= cstat.st_mtime:
                # a result ack exists for this command → the DLL placed it → clear now
                COMMAND_PATH.write_text("")
                logger.info("[FillPoller] trade_command.json cleared after ack (anti-duplicate guard)")
        except OSError:
            pass

    def _check_fills(self) -> None:
        """Check for new fill events in trade_fills.json."""
        if not FILLS_PATH.exists():
            return

        try:
            mtime = FILLS_PATH.stat().st_mtime
        except OSError:
            return
        if mtime <= self._last_mtime:
            return
        self._last_mtime = mtime

        try:
            content = FILLS_PATH.read_text().strip()
            if not content:
                return
        except OSError:
            return

        # DLL appends one JSON per line — read ALL lines, process each
        fills = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                fills.append(json.loads(line))
            except json.JSONDecodeError:
                logger.debug("[FillPoller] bad line (skipped): %s", line[:80])

        for fill in fills:
            self._process_fill(fill)

        # L8 journal (2026-07-08): persist every fill line BEFORE clearing — the
        # ledger reads the same file and lost every fill the poller consumed
        # (live ledger showed 0 trades while a live trade was open). Append-only
        # journal = the ledger's durable source. Fail-safe: journal errors never
        # block fill processing.
        try:
            _journal = FILLS_PATH.with_name("trade_fills_journal.jsonl")
            with open(_journal, "a", encoding="utf-8") as jf:
                for line in content.split("\n"):
                    if line.strip():
                        jf.write(line.strip() + "\n")
        except OSError as e:
            logger.warning("[FillPoller] fills journal append failed: %s", e)

        # Clear the file after processing all fills
        try:
            FILLS_PATH.write_text("")
        except OSError:
            pass

    def _process_fill(self, fill: Dict[str, Any]) -> None:
        """Process a single fill event from trade_fills.json."""
        if self._tm is None:
            logger.warning("[FillPoller] no TradeManager set — skipping fill")
            return

        kind = fill.get("kind", "").upper()
        order_id = fill.get("order_id")
        price = fill.get("price")
        ts_epoch = fill.get("ts")
        fill_ts = datetime.fromtimestamp(ts_epoch, tz=timezone.utc) if ts_epoch else None

        # Find the trade_id from the order map
        trade_id = self._order_map.get(order_id)
        if trade_id is None:
            # Fallback (I-58 hardened): Sierra fills can ONLY belong to demo/live
            # trades — never attribute them to a SHADOW twin. Pick the most recent
            # active NON-shadow trade; if none, drop loudly.
            active = [t for t in self._tm.get_active_trades()
                      if getattr(t, "mode", "shadow") in ("demo", "live", "SIM")]
            if active:
                trade_id = active[-1].id
                logger.warning(
                    "[FillPoller] unmapped order_id=%s → fallback to most recent %s trade %s "
                    "(I-58: map should have had it — investigate)",
                    order_id, getattr(active[-1], "mode", "?"), trade_id,
                )
            else:
                # P1.2 (Michael 2026-07-07): a Sierra fill with NO trade to attribute is a
                # possible NAKED live position (the I-62 orphan class — 07-03 trade 290).
                # NEVER silent: raise to CRITICAL so Michael sees it + record it so the
                # reconcile-live / System 6 orphan invariant can act. We deliberately do NOT
                # fabricate a trade from a bare fill (guessing direction/size wrong is worse
                # than a loud alert) — alert, and let reconcile / a human flatten it.
                self._orphan_count += 1
                self._orphan_fills.append({
                    "order_id": order_id, "kind": kind, "price": price, "ts": ts_epoch,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })
                if len(self._orphan_fills) > 50:
                    self._orphan_fills = self._orphan_fills[-50:]
                logger.critical(
                    "[FillPoller] ORPHAN FILL — no trade for order_id=%s kind=%s price=%s. "
                    "POSSIBLE UNTRACKED SIERRA POSITION — reconcile/flatten NOW. (orphans=%d)",
                    order_id, kind, price, self._orphan_count,
                )
                return

        self._processed_count += 1
        logger.info("[FillPoller] fill: kind=%s order=%s trade=%s price=%s",
                     kind, order_id, trade_id, price)

        try:
            if kind == "ENTRY":
                # Entry fill — transition PENDING→FILLED via on_fill
                if price is not None:
                    self._tm.on_fill(trade_id, float(price))
                    logger.info("[FillPoller] ENTRY fill: trade %s @ %s", trade_id, price)

                    # Store Sierra order IDs from the ENTRY fill (up to 8 per-contract IDs)
                    sierra_ids = {
                        "sierra_order_id": fill.get("order_id"),
                        "c1_target_id": fill.get("c1_target_id"),
                        "c1_stop_id": fill.get("c1_stop_id"),
                        "c2_target_id": fill.get("c2_target_id"),
                        "c2_stop_id": fill.get("c2_stop_id"),
                        "c3_target_id": fill.get("c3_target_id"),
                        "c3_stop_id": fill.get("c3_stop_id"),
                        "c4_target_id": fill.get("c4_target_id"),
                        "c4_stop_id": fill.get("c4_stop_id"),
                    }
                    try:
                        self._tm.set_sierra_order_ids(trade_id, sierra_ids)
                    except Exception as e:
                        logger.warning("[FillPoller] set_sierra_order_ids failed: %s", e)
                    # I-58 (2026-07-02, trades 275/276): map ALL per-contract order IDs so
                    # later T1/T2/T3/STOP fills resolve to THIS trade — without this, an
                    # unmapped target/stop fill fell to the "most recent active" fallback
                    # and got attributed to the SHADOW twin: demo stayed blind (no T1 →
                    # no smart-BE → stuck open until manual close).
                    for _oid in sierra_ids.values():
                        if _oid is not None and _oid != fill.get("order_id"):
                            self._order_map[int(_oid)] = trade_id
                    # L2-residual (2026-07-08): map the ENTRY order id itself too —
                    # a fallback-resolved ENTRY left the parent id unmapped, so any
                    # later event referencing it re-entered the fallback.
                    if order_id is not None:
                        self._order_map[int(order_id)] = trade_id
                    logger.info("[FillPoller] mapped %d per-contract order ids → trade %s",
                                sum(1 for v in sierra_ids.values() if v is not None), trade_id)

            elif kind in ("T1", "T2", "T3", "T4"):
                # Pass Sierra fill price so PnL uses real execution, not intended level
                _fill_px = float(price) if price is not None else None
                self._tm.on_target_hit(trade_id, kind, fill_ts=fill_ts, fill_price=_fill_px)
                logger.info("[FillPoller] %s fill: trade %s @ %s", kind, trade_id, price)
                if kind in ("T3", "T4"):
                    # All contracts out → full close: free slot + count outcome (I-57)
                    # T4 is the last runner with 4 contracts (Michael 07-15)
                    self._notify_gateway_close(trade_id, kind)
                else:
                    # L7 (2026-07-08): with <3 contracts the LAST target is T1/T2 —
                    # the manager closes the trade there; free the slot too (the
                    # T3-only check left a 2c trade's slot stuck after its runner
                    # target filled).
                    _get = getattr(self._tm, "_get_trade", None)
                    _t = _get(trade_id) if callable(_get) else None
                    if _t is not None and getattr(_t, "state", "") == "CLOSED":
                        self._notify_gateway_close(trade_id, kind)

            elif kind == "STOP":
                # Pass Sierra fill price so exit_price = real fill (may differ from trade.stop due to slippage)
                _fill_px = float(price) if price is not None else None
                self._tm.on_stop_hit(trade_id, fill_ts=fill_ts, fill_price=_fill_px)
                logger.info("[FillPoller] STOP fill: trade %s @ %s", trade_id, price)
                # Full close via Sierra stop → free slot + count the stop (I-57:
                # this path previously bypassed on_trade_close → stuck demo slot
                # + cooldown blind to stops. Trades 271/272, 2026-07-02.)
                self._notify_gateway_close(trade_id, "STOP")

            else:
                logger.warning("[FillPoller] unknown fill kind: %s", kind)

        except Exception as e:
            logger.warning("[FillPoller] error processing fill %s: %s", kind, e)

        # L8+ (2026-07-14): real-time Google-Sheets LIVE-trade log — Sierra-truth
        # only, flag-gated (GSHEETS_TRADE_LOG, default OFF) + LIVE-only. The push
        # is fire-and-forget on a daemon thread INSIDE the logger, so a slow or
        # broken Sheets endpoint can NEVER stall or crash this fill loop.
        self._maybe_log_gsheet(fill, trade_id)

    def _maybe_log_gsheet(self, fill: Dict[str, Any], trade_id) -> None:
        """Push the current Sierra-reconstructed trade row to Google Sheets on
        each LIVE fill (real-time). Guarded + fail-soft: gated to mode=='live' and
        the GSHEETS_TRADE_LOG flag (default OFF → no-op), and every error is
        swallowed here AND inside the logger. Never touches fill booking, never
        raises, never blocks (the HTTP POST runs on a daemon thread)."""
        try:
            from backend.v9.services import gsheets_trade_logger as gs
            if not gs.is_enabled():
                return
            trade = self._tm._get_trade(trade_id) if self._tm is not None else None
            mode = getattr(trade, "mode", "shadow") if trade is not None else "shadow"
            if str(mode).lower() != "live":
                return
            # entry parent order id == LedgerTrade.entry_order_id (Sierra chain key)
            entry_oid = None
            q = getattr(trade, "quality", None)
            if isinstance(q, dict):
                entry_oid = q.get("sierra_order_id")
            if entry_oid is None:
                entry_oid = fill.get("order_id")
            gs.log_live_fill(fill=fill, mode="live", entry_order_id=entry_oid)
        except Exception as e:
            logger.debug("[FillPoller] gsheet log skipped (fail-safe): %s", e)

    def get_stats(self) -> dict:
        return {
            "running": self._running,
            "processed": self._processed_count,
            "order_map_size": len(self._order_map),
            "orphan_fills": self._orphan_count,
        }

    def get_orphan_fills(self) -> list:
        """Recent orphan fills (Sierra fill with no trade to attribute) — consumed by the
        reconcile-live pass / System 6 orphan invariant. Empty = no untracked positions seen."""
        return list(self._orphan_fills)
