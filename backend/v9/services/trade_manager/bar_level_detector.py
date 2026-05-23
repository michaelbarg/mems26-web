"""BarLevelDetector — glue between BarRouter and W11 TradeManager.

Subscribes to 5min bars via BarRouter. On each bar, iterates all active
(FILLED/PARTIAL) trades and checks if bar.high/low crossed any target or stop.
Calls existing TradeManager.on_target_hit() / on_stop_hit() / close_trade().

Also implements Day Type time-based exits per Constitution V3 Layer 4.

This is the CRITICAL missing piece that makes SHADOW trades close automatically.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.trade_manager.state_machine import TradeState

logger = logging.getLogger(__name__)

# Constitution V3 Layer 4: time-based exit per Day Type (minutes)
TIME_STOP_BY_DAY_TYPE = {
    "TREND_NORMAL": None,   # no time stop
    "VARIATION": 60,
    "NORMAL": 30,
    "TREND_DD": 90,
    "NEUTRAL": 45,
    "NONTREND": 20,
}


class BarLevelDetector:
    """Per-bar hit detection for active trades.

    Subscribes to BarRouter '5min' channel. On each bar:
      1. Check stop (adverse fill priority)
      2. Check T1 → T2 → T3 sequentially
      3. Check time-based exit per Day Type
    """

    def __init__(self, trade_manager: TradeManager):
        self._tm = trade_manager
        self._bars_processed = 0

    def subscribe(self, bar_router) -> None:
        """Register with BarRouter for 5min bar events."""
        bar_router.subscribe("5min", self.on_bar)
        logger.info("[BarLevelDetector] subscribed to 5min via BarRouter")

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
            bar_close = float(bar_data.get("close", bar_data.get("c", 0)))
            bar_ts_raw = bar_data.get("ts", "")

            # Parse bar timestamp
            bar_ts = self._parse_ts(bar_ts_raw)

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

                direction = trade.direction
                stop = trade.stop

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

                # 3. Time-based exit per Day Type
                if self._check_time_stop(trade, bar_ts):
                    # Reload trade state — may have been partially closed above
                    refreshed = self._tm._get_trade(trade.id)
                    if refreshed.state != TradeState.CLOSED.value:
                        refreshed.exit_price = bar_close
                        self._tm.close_trade(trade.id, "TIME_STOP")
                        logger.info("[BarLevelDetector] TIME STOP: trade %d after limit",
                                    trade.id)

            self._tm._db.commit()

        except Exception as e:
            logger.error("[BarLevelDetector] on_bar error: %s", e, exc_info=True)

    def _check_time_stop(self, trade, bar_ts: Optional[datetime]) -> bool:
        """Check if trade exceeded Day Type time limit."""
        if bar_ts is None or trade.entry_ts is None:
            return False

        # Get day_type from cross_context
        day_type = None
        ctx = trade.cross_context
        if isinstance(ctx, list) and ctx:
            entry_ctx = ctx[0] if isinstance(ctx[0], dict) else {}
            day_type = entry_ctx.get("day_type", {}).get("day_type") if isinstance(entry_ctx.get("day_type"), dict) else entry_ctx.get("day_type")
        elif isinstance(ctx, dict):
            day_type = ctx.get("day_type")

        if day_type is None:
            return False

        limit = TIME_STOP_BY_DAY_TYPE.get(day_type)
        if limit is None:
            return False

        entry_ts = trade.entry_ts
        if isinstance(entry_ts, str):
            try:
                entry_ts = datetime.fromisoformat(entry_ts)
            except ValueError:
                return False

        if entry_ts.tzinfo is None:
            entry_ts = entry_ts.replace(tzinfo=timezone.utc)
        if bar_ts.tzinfo is None:
            bar_ts = bar_ts.replace(tzinfo=timezone.utc)

        elapsed_minutes = (bar_ts - entry_ts).total_seconds() / 60
        return elapsed_minutes >= limit

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
