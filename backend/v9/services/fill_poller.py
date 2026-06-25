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
                self._check_fills()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("[FillPoller] poll error (continuing): %s", e)
        logger.info("[FillPoller] stopped")

    def stop(self) -> None:
        self._running = False

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
            fill = json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("[FillPoller] parse error: %s", e)
            return

        self._process_fill(fill)

        # Clear the file after processing (same as DLL clears command)
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
                # Entry fill — update trade with Sierra fill price
                trade = self._tm._get_trade(trade_id)
                if trade and price:
                    trade.entry_price = float(price)
                    if fill_ts:
                        trade.entry_ts = fill_ts
                    logger.info("[FillPoller] ENTRY fill: trade %s @ %.2f", trade_id, price)

            elif kind in ("T1", "T2", "T3"):
                self._tm.on_target_hit(trade_id, kind, fill_ts=fill_ts)
                logger.info("[FillPoller] %s fill: trade %s", kind, trade_id)

            elif kind == "STOP":
                self._tm.on_stop_hit(trade_id, fill_ts=fill_ts)
                logger.info("[FillPoller] STOP fill: trade %s", kind, trade_id)

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
