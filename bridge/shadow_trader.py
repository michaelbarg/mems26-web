"""ShadowTrader — paper trading tracker for SHADOW mode analysis.

Tracks hypothetical trades without real execution. Records entry, exit, PnL,
and timing for post-session analysis. All trades exist only in memory and
an optional JSON log file.

MES tick value: $1.25 per tick (0.25 points), $5 per point.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("v9_bridge")

MES_POINT_VALUE = 5.0  # $5 per point for MES
SHADOW_LOG_PATH = Path("/tmp/mems26_shadow_trades.json")


class TradeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass
class ShadowTrade:
    """A single shadow (paper) trade."""
    trade_id: str
    system_id: int
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    entry_ts: float
    contracts: int = 1
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    exit_price: Optional[float] = None
    exit_ts: Optional[float] = None
    exit_reason: Optional[str] = None
    status: str = TradeStatus.OPEN
    pnl_usd: float = 0.0
    pnl_points: float = 0.0

    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "system_id": self.system_id,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "entry_ts": self.entry_ts,
            "contracts": self.contracts,
            "stop_price": self.stop_price,
            "target_price": self.target_price,
            "exit_price": self.exit_price,
            "exit_ts": self.exit_ts,
            "exit_reason": self.exit_reason,
            "status": self.status,
            "pnl_usd": self.pnl_usd,
            "pnl_points": self.pnl_points,
        }


class ShadowTrader:
    """Paper trading tracker for SHADOW mode.

    Records hypothetical trades for analysis without real execution.
    Persists trade log to /tmp/mems26_shadow_trades.json.
    """

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or SHADOW_LOG_PATH
        self._trades: List[ShadowTrade] = []
        self._trade_counter = 0
        self._load_existing()

    def _load_existing(self):
        """Load existing shadow trades from disk on startup."""
        if self.log_path.exists():
            try:
                with open(self.log_path, "r") as f:
                    data = json.load(f)
                for td in data:
                    trade = ShadowTrade(**td)
                    self._trades.append(trade)
                    self._trade_counter += 1
                logger.info(f"[shadow_trader] Loaded {len(self._trades)} existing trades")
            except (json.JSONDecodeError, IOError, TypeError) as e:
                logger.warning(f"[shadow_trader] Could not load existing trades: {e}")

    def _save(self):
        """Persist all trades to disk."""
        try:
            with open(self.log_path, "w") as f:
                json.dump([t.to_dict() for t in self._trades], f, indent=2)
        except IOError as e:
            logger.warning(f"[shadow_trader] Could not save trades: {e}")

    def open_trade(
        self,
        system_id: int,
        direction: str,
        entry_price: float,
        contracts: int = 1,
        stop_price: Optional[float] = None,
        target_price: Optional[float] = None,
        entry_ts: Optional[float] = None,
    ) -> ShadowTrade:
        """Open a new shadow trade.

        Args:
            system_id: System that generated the signal (1-6).
            direction: "LONG" or "SHORT".
            entry_price: Entry price.
            contracts: Number of contracts.
            stop_price: Initial stop loss price.
            target_price: Target price (T1).
            entry_ts: Entry timestamp. Uses current time if None.

        Returns:
            The created ShadowTrade.
        """
        self._trade_counter += 1
        trade_id = f"SHADOW-{self._trade_counter:05d}"

        trade = ShadowTrade(
            trade_id=trade_id,
            system_id=system_id,
            direction=direction,
            entry_price=entry_price,
            entry_ts=entry_ts or time.time(),
            contracts=contracts,
            stop_price=stop_price,
            target_price=target_price,
        )
        self._trades.append(trade)
        self._save()
        logger.info(
            f"[shadow_trader] Opened {trade_id}: {direction} {contracts}x @ {entry_price} "
            f"(system {system_id})"
        )
        return trade

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str = "manual",
        exit_ts: Optional[float] = None,
    ) -> Optional[ShadowTrade]:
        """Close an open shadow trade.

        Args:
            trade_id: Trade ID to close.
            exit_price: Exit price.
            exit_reason: Reason for exit (e.g., "stop", "target", "manual", "eod").
            exit_ts: Exit timestamp. Uses current time if None.

        Returns:
            The closed ShadowTrade, or None if not found.
        """
        trade = self.get_trade(trade_id)
        if trade is None or trade.status == TradeStatus.CLOSED:
            return None

        trade.exit_price = exit_price
        trade.exit_ts = exit_ts or time.time()
        trade.exit_reason = exit_reason
        trade.status = TradeStatus.CLOSED

        # Calculate PnL
        if trade.direction == TradeDirection.LONG:
            trade.pnl_points = (exit_price - trade.entry_price) * trade.contracts
        else:
            trade.pnl_points = (trade.entry_price - exit_price) * trade.contracts
        trade.pnl_usd = trade.pnl_points * MES_POINT_VALUE

        self._save()
        logger.info(
            f"[shadow_trader] Closed {trade_id}: {exit_reason} @ {exit_price}, "
            f"PnL={trade.pnl_usd:+.2f} USD ({trade.pnl_points:+.2f} pts)"
        )
        return trade

    def check_stops_and_targets(self, current_price: float) -> List[ShadowTrade]:
        """Check all open trades against current price for stop/target hits.

        Args:
            current_price: Current market price.

        Returns:
            List of trades that were closed by stop or target.
        """
        closed = []
        for trade in self.get_open_trades():
            # Check stop
            if trade.stop_price is not None:
                if (trade.direction == TradeDirection.LONG and current_price <= trade.stop_price) or \
                   (trade.direction == TradeDirection.SHORT and current_price >= trade.stop_price):
                    self.close_trade(trade.trade_id, current_price, "stop")
                    closed.append(trade)
                    continue

            # Check target
            if trade.target_price is not None:
                if (trade.direction == TradeDirection.LONG and current_price >= trade.target_price) or \
                   (trade.direction == TradeDirection.SHORT and current_price <= trade.target_price):
                    self.close_trade(trade.trade_id, current_price, "target")
                    closed.append(trade)
                    continue

        return closed

    def get_trade(self, trade_id: str) -> Optional[ShadowTrade]:
        """Get a trade by ID."""
        for t in self._trades:
            if t.trade_id == trade_id:
                return t
        return None

    def get_open_trades(self) -> List[ShadowTrade]:
        """Return all currently open trades."""
        return [t for t in self._trades if t.status == TradeStatus.OPEN]

    def get_all_trades(self) -> List[ShadowTrade]:
        """Return all trades (open and closed)."""
        return list(self._trades)

    def get_session_pnl(self) -> float:
        """Return total PnL in USD for all closed trades."""
        return sum(t.pnl_usd for t in self._trades if t.status == TradeStatus.CLOSED)

    def get_session_stats(self) -> dict:
        """Return session statistics."""
        closed = [t for t in self._trades if t.status == TradeStatus.CLOSED]
        winners = [t for t in closed if t.pnl_usd > 0]
        losers = [t for t in closed if t.pnl_usd < 0]
        return {
            "total_trades": len(self._trades),
            "open_trades": len(self.get_open_trades()),
            "closed_trades": len(closed),
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": len(winners) / len(closed) if closed else 0.0,
            "total_pnl_usd": self.get_session_pnl(),
            "avg_winner_usd": sum(t.pnl_usd for t in winners) / len(winners) if winners else 0.0,
            "avg_loser_usd": sum(t.pnl_usd for t in losers) / len(losers) if losers else 0.0,
        }
