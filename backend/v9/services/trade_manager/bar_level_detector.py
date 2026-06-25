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

    def __init__(self, trade_manager: TradeManager):
        self._tm = trade_manager
        self._bars_processed = 0
        self._last_bar_ts_processed: str = ""  # dedup across 5min + woodies_5min

    def subscribe(self, bar_router) -> None:
        """Register with BarRouter for 5min + woodies_5min bar events."""
        bar_router.subscribe("5min", self.on_bar)
        bar_router.subscribe("woodies_5min", self.on_bar)
        logger.info("[BarLevelDetector] subscribed to 5min + woodies_5min via BarRouter")

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

                # Pipeline 5 Phase C: bar_level_detector manages SHADOW trades only.
                # DEMO/LIVE trades are managed by Sierra fill poller (no double-management).
                trade_mode = getattr(trade, "mode", "shadow")
                if trade_mode in ("demo", "live"):
                    continue

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

                # Trail runner stop (before stop-check so trailed stop is used)
                import os as _trail_os
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

                # 1. Stop check FIRST (adverse fill priority)
                if stop is not None:
                    if (direction == "LONG" and bar_low <= stop) or \
                       (direction == "SHORT" and bar_high >= stop):
                        self._tm.on_stop_hit(trade.id, fill_ts=bar_ts)
                        logger.info("[BarLevelDetector] STOP HIT: trade %d at %.2f", trade.id, stop)
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
                    if (direction == "LONG" and bar_high >= target_price) or \
                       (direction == "SHORT" and bar_low <= target_price):
                        self._tm.on_target_hit(trade.id, target_name, fill_ts=bar_ts)
                        logger.info("[BarLevelDetector] %s HIT: trade %d at %.2f",
                                    target_name, trade.id, target_price)

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

    def get_stats(self) -> dict:
        return {"bars_processed": self._bars_processed}
