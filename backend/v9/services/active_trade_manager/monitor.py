"""W15 Active Trade Monitor — real-time monitoring of open trades.

Watches FILLED and PARTIAL trades on each price tick. Computes
unrealized PnL, checks proximity to targets/stop, detects Smart BE
trigger when T1 fills.

MES futures: $5 per point per contract, tick size 0.25.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.trade_manager.state_machine import TradeState
from backend.v9.services.active_trade_manager.alerts import AlertEmitter

logger = logging.getLogger(__name__)

# MES constants
MES_TICK_SIZE = 0.25
MES_POINT_VALUE = 5.0  # $5 per point per contract

# Proximity threshold: alert when price is within 25% of entry-to-level distance
PROXIMITY_THRESHOLD = 0.25

# LIVE cutoff: 14:30 ET — suggest exit at 14:25 ET
TIME_EXIT_CUTOFF_HOUR = 14
TIME_EXIT_CUTOFF_MINUTE = 25


class ActiveTradeMonitor:
    """Real-time monitor for open (FILLED/PARTIAL) trades.

    Called on each price tick via update(). Does NOT make trading
    decisions — only monitors and emits alerts. Uses W11 TradeManager
    for stop adjustments (Smart BE).
    """

    __slots__ = (
        "_trade_manager",
        "_alert_emitter",
        "_smart_be_applied",
    )

    def __init__(
        self,
        trade_manager: TradeManager,
        alert_emitter: Optional[AlertEmitter] = None,
    ):
        self._trade_manager = trade_manager
        self._alert_emitter = alert_emitter or AlertEmitter()
        # Track which trades have had Smart BE applied — bounded by active trades
        self._smart_be_applied: Dict[int, bool] = {}

    def update(
        self,
        current_price: float,
        ts: float,
        et_hour: Optional[int] = None,
        et_minute: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Called on each price tick. Monitors all open trades.

        Args:
            current_price: current MES price
            ts: unix timestamp of the tick
            et_hour: current hour in ET (for time exit checks)
            et_minute: current minute in ET (for time exit checks)

        Returns:
            List of alert payloads emitted during this tick.
        """
        alerts: List[Dict[str, Any]] = []
        open_trades = self._trade_manager.get_active_trades()

        for trade in open_trades:
            if trade.state not in (TradeState.FILLED.value, TradeState.PARTIAL.value):
                continue

            if trade.entry_price is None:
                continue

            direction = trade.direction
            entry = trade.entry_price

            # Smart BE: when T1 is hit (state=PARTIAL, t1_hit_ts set),
            # move stop to entry_price (breakeven)
            if (
                trade.state == TradeState.PARTIAL.value
                and trade.t1_hit_ts is not None
                and not self._smart_be_applied.get(trade.id, False)
            ):
                alert = self.apply_smart_be(trade.id)
                if alert is not None:
                    alerts.append(alert)

            # Proximity to targets (only unhit targets)
            targets = []
            if trade.t1 is not None and trade.t1_hit_ts is None:
                targets.append(("T1", trade.t1))
            if trade.t2 is not None and trade.t2_hit_ts is None:
                targets.append(("T2", trade.t2))
            if trade.t3 is not None and trade.t3_hit_ts is None:
                targets.append(("T3", trade.t3))

            for target_name, target_price in targets:
                entry_to_target = abs(target_price - entry)
                if entry_to_target == 0:
                    continue
                price_to_target = abs(target_price - current_price)
                distance_pct = price_to_target / entry_to_target

                if distance_pct <= PROXIMITY_THRESHOLD:
                    alert = self._alert_emitter.emit_approaching_target(
                        trade.id, target_name, distance_pct,
                    )
                    alerts.append(alert)

            # Proximity to stop
            if trade.stop is not None:
                entry_to_stop = abs(trade.stop - entry)
                if entry_to_stop > 0:
                    price_to_stop = abs(trade.stop - current_price)
                    distance_pct = price_to_stop / entry_to_stop

                    if distance_pct <= PROXIMITY_THRESHOLD:
                        alert = self._alert_emitter.emit_approaching_stop(
                            trade.id, distance_pct,
                        )
                        alerts.append(alert)

            # Time exit suggestion
            if et_hour is not None and et_minute is not None:
                if (
                    et_hour == TIME_EXIT_CUTOFF_HOUR
                    and et_minute >= TIME_EXIT_CUTOFF_MINUTE
                ) or et_hour > TIME_EXIT_CUTOFF_HOUR:
                    alert = self._alert_emitter.emit_time_exit_suggestion(
                        trade.id,
                        "14:25 ET — consider closing before cutoff",
                    )
                    alerts.append(alert)

        return alerts

    def get_open_trades(
        self,
        current_price: float,
    ) -> List[Dict[str, Any]]:
        """Return open trades with unrealized PnL and proximity info.

        Args:
            current_price: current MES price for PnL calculation

        Returns:
            List of dicts with trade info, unrealized_pnl, proximity data.
        """
        result: List[Dict[str, Any]] = []
        open_trades = self._trade_manager.get_active_trades()

        for trade in open_trades:
            if trade.state not in (TradeState.FILLED.value, TradeState.PARTIAL.value):
                continue

            if trade.entry_price is None:
                continue

            direction = trade.direction
            entry = trade.entry_price

            # Unrealized PnL
            direction_mult = 1.0 if direction == "LONG" else -1.0

            if trade.state == TradeState.PARTIAL.value and trade.t1 is not None:
                # C1 already exited at T1. Remaining contracts (C2, C3)
                # have unrealized PnL based on current_price
                c1_pnl = (trade.t1 - entry) * direction_mult * MES_POINT_VALUE
                remaining_pnl = (current_price - entry) * direction_mult * MES_POINT_VALUE * 2
                unrealized_pnl = round(c1_pnl + remaining_pnl, 2)
            else:
                # All 3 contracts open
                points = (current_price - entry) * direction_mult
                unrealized_pnl = round(points * MES_POINT_VALUE * 3, 2)

            # Proximity info
            proximity: Dict[str, float] = {}

            targets = []
            if trade.t1 is not None and trade.t1_hit_ts is None:
                targets.append(("T1", trade.t1))
            if trade.t2 is not None and trade.t2_hit_ts is None:
                targets.append(("T2", trade.t2))
            if trade.t3 is not None and trade.t3_hit_ts is None:
                targets.append(("T3", trade.t3))

            for target_name, target_price in targets:
                entry_to_target = abs(target_price - entry)
                if entry_to_target > 0:
                    price_to_target = abs(target_price - current_price)
                    proximity[target_name] = round(
                        price_to_target / entry_to_target, 4,
                    )

            if trade.stop is not None:
                entry_to_stop = abs(trade.stop - entry)
                if entry_to_stop > 0:
                    price_to_stop = abs(trade.stop - current_price)
                    proximity["stop"] = round(
                        price_to_stop / entry_to_stop, 4,
                    )

            result.append({
                "trade_id": trade.id,
                "direction": direction,
                "state": trade.state,
                "entry_price": entry,
                "current_price": current_price,
                "stop": trade.stop,
                "t1": trade.t1,
                "t2": trade.t2,
                "t3": trade.t3,
                "unrealized_pnl": unrealized_pnl,
                "proximity": proximity,
                "smart_be_applied": self._smart_be_applied.get(trade.id, False),
            })

        return result

    def apply_smart_be(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """Move stop to entry_price (breakeven) for the given trade.

        Called when T1 is hit (C1 partial fill). Protects remaining
        contracts (C2, C3) from loss.

        Returns the alert payload, or None if not applicable.
        """
        if self._smart_be_applied.get(trade_id, False):
            logger.debug("Smart BE already applied for trade %d", trade_id)
            return None

        # Get the trade via W11 to read entry_price
        trade = self._trade_manager._get_trade(trade_id)

        if trade.entry_price is None:
            return None

        new_stop = trade.entry_price

        # Update stop on the trade record
        trade.stop = new_stop
        self._trade_manager._db.flush()

        self._smart_be_applied[trade_id] = True

        logger.info(
            "Smart BE triggered: trade %d stop moved to %.2f (breakeven)",
            trade_id, new_stop,
        )

        return self._alert_emitter.emit_smart_be_triggered(trade_id, new_stop)

    def cleanup_trade(self, trade_id: int) -> None:
        """Remove tracking state for a closed trade. Prevents unbounded growth."""
        self._smart_be_applied.pop(trade_id, None)
