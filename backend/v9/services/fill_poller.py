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

    def __init__(self, trade_manager=None):
        self._tm = trade_manager
        self._running = False
        self._last_mtime: float = 0.0
        self._processed_count = 0
        # Map sierra_order_id → trade_id (set when command is written)
        self._order_map: Dict[int, int] = {}

    def set_trade_manager(self, tm) -> None:
        self._tm = tm

    def register_order(self, sierra_order_id: int, trade_id: int) -> None:
        """Map a Sierra order ID to a MEMS26 trade ID."""
        self._order_map[sierra_order_id] = trade_id
        logger.info("[FillPoller] registered order %d → trade %d", sierra_order_id, trade_id)

    async def run(self) -> None:
        """Main polling loop — run as an asyncio task."""
        self._running = True
        logger.info("[FillPoller] started (polling %s every %.0fms)", FILLS_PATH, POLL_INTERVAL * 1000)
        while self._running:
            try:
                await asyncio.sleep(POLL_INTERVAL)
                self._guard_duplicate_command()
                self._check_fills()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("[FillPoller] poll error (continuing): %s", e)
        logger.info("[FillPoller] stopped")

    def stop(self) -> None:
        self._running = False

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
            # Fallback: try to find the most recent active trade
            active = self._tm.get_active_trades()
            if active:
                trade_id = active[-1].id
            else:
                logger.warning("[FillPoller] no trade found for order_id=%s", order_id)
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

            elif kind in ("T1", "T2", "T3"):
                self._tm.on_target_hit(trade_id, kind, fill_ts=fill_ts)
                logger.info("[FillPoller] %s fill: trade %s", kind, trade_id)

            elif kind == "STOP":
                self._tm.on_stop_hit(trade_id, fill_ts=fill_ts)
                logger.info("[FillPoller] STOP fill: trade %s", trade_id)

            else:
                logger.warning("[FillPoller] unknown fill kind: %s", kind)

        except Exception as e:
            logger.warning("[FillPoller] error processing fill %s: %s", kind, e)

    def get_stats(self) -> dict:
        return {
            "running": self._running,
            "processed": self._processed_count,
            "order_map_size": len(self._order_map),
        }
