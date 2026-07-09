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


class FillPoller:
    """Async poller that reads trade_fills.json and drives TradeManager."""

    def __init__(self, trade_manager=None, gateway=None):
        self._tm = trade_manager
        self._gateway = gateway
        self._running = False
        self._last_mtime: float = 0.0
        self._last_result_mtime: float = 0.0
        self._processed_count = 0
        # Map sierra_order_id → trade_id (set when command is written)
        self._order_map: Dict[int, int] = {}
        # P1.2 (2026-07-07): orphan fills — a Sierra fill with no trade to attribute.
        # Recorded + surfaced (never silent) for the reconcile / System 6 orphan invariant.
        self._orphan_fills: list = []
        self._orphan_count: int = 0

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
                self._guard_duplicate_command()
                self._check_result()
                self._check_fills()
                self._maybe_reconcile()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("[FillPoller] poll error (continuing): %s", e)
        logger.info("[FillPoller] stopped")

    def stop(self) -> None:
        self._running = False

    def _maybe_reconcile(self) -> None:
        """FIX-6 (SYS-3): compare TM vs Sierra position every ≤30s.

        Flag-gated: SIERRA_RECONCILER_V1 (default OFF — Michael enables at restart).
        Fail-safe: errors never break the fill-poller loop.
        """
        import time as _t
        if _t.time() < getattr(self, "_reconcile_next", 0.0):
            return
        self._reconcile_next = _t.time() + 30.0
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
                        self._tm.close_trade(
                            trade.id,
                            reason=_reason,
                        )
                        # Override state to CANCELLED (close_trade sets CLOSED)
                        trade.state = "CANCELLED"
                        trade.pnl_usd = 0.0
                        trade.outcome = "CANCELLED"
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

                    # Store Sierra order IDs from the ENTRY fill (6 per-contract IDs)
                    sierra_ids = {
                        "sierra_order_id": fill.get("order_id"),
                        "c1_target_id": fill.get("c1_target_id"),
                        "c1_stop_id": fill.get("c1_stop_id"),
                        "c2_target_id": fill.get("c2_target_id"),
                        "c2_stop_id": fill.get("c2_stop_id"),
                        "c3_target_id": fill.get("c3_target_id"),
                        "c3_stop_id": fill.get("c3_stop_id"),
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

            elif kind in ("T1", "T2", "T3"):
                # Pass Sierra fill price so PnL uses real execution, not intended level
                _fill_px = float(price) if price is not None else None
                self._tm.on_target_hit(trade_id, kind, fill_ts=fill_ts, fill_price=_fill_px)
                logger.info("[FillPoller] %s fill: trade %s @ %s", kind, trade_id, price)
                if kind == "T3":
                    # All contracts out → full close: free slot + count outcome (I-57)
                    self._notify_gateway_close(trade_id, "T3")
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
