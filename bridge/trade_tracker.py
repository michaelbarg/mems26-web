"""TradeTracker — tracks active trades across bridge restarts.

Persists state in /tmp/mems26_active_trades.json so that the bridge
can resume tracking after a restart without losing trade state.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("v9_bridge")

ACTIVE_TRADES_PATH = Path("/tmp/mems26_active_trades.json")


@dataclass
class TrackedTrade:
    """A trade being tracked across the bridge lifecycle."""
    trade_id: str
    mode: str  # SHADOW, DEMO, LIVE
    system_id: int
    direction: str  # LONG, SHORT
    entry_price: float
    entry_ts: float
    contracts: int = 1
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    sierra_bracket_id: Optional[str] = None
    status: str = "OPEN"  # OPEN, PENDING_CLOSE, CLOSED
    last_update_ts: float = 0.0

    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "mode": self.mode,
            "system_id": self.system_id,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "entry_ts": self.entry_ts,
            "contracts": self.contracts,
            "stop_price": self.stop_price,
            "target_price": self.target_price,
            "sierra_bracket_id": self.sierra_bracket_id,
            "status": self.status,
            "last_update_ts": self.last_update_ts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TrackedTrade":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class TradeTracker:
    """Tracks active trades across bridge restarts.

    On startup, loads any previously active trades from disk.
    On each state change, persists to disk immediately.
    """

    def __init__(self, state_path: Optional[Path] = None):
        self._path = state_path or ACTIVE_TRADES_PATH
        self._trades: Dict[str, TrackedTrade] = {}
        self._load()

    def _load(self):
        """Load active trades from disk."""
        if not self._path.exists():
            return
        try:
            with open(self._path, "r") as f:
                data = json.load(f)
            for td in data:
                trade = TrackedTrade.from_dict(td)
                self._trades[trade.trade_id] = trade
            logger.info(f"[trade_tracker] Loaded {len(self._trades)} active trades from disk")
        except (json.JSONDecodeError, IOError, TypeError) as e:
            logger.warning(f"[trade_tracker] Could not load state: {e}")

    def _save(self):
        """Persist active trades to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w") as f:
                json.dump([t.to_dict() for t in self._trades.values()], f, indent=2)
        except IOError as e:
            logger.warning(f"[trade_tracker] Could not save state: {e}")

    def add_trade(self, trade: TrackedTrade):
        """Add or update a tracked trade."""
        trade.last_update_ts = time.time()
        self._trades[trade.trade_id] = trade
        self._save()
        logger.info(
            f"[trade_tracker] Tracking {trade.trade_id}: "
            f"{trade.direction} {trade.contracts}x @ {trade.entry_price} ({trade.mode})"
        )

    def update_trade(self, trade_id: str, **kwargs) -> Optional[TrackedTrade]:
        """Update fields on a tracked trade.

        Args:
            trade_id: Trade to update.
            **kwargs: Fields to update (e.g., stop_price=5000.0, status="CLOSED").

        Returns:
            Updated trade, or None if not found.
        """
        trade = self._trades.get(trade_id)
        if trade is None:
            return None
        for k, v in kwargs.items():
            if hasattr(trade, k):
                setattr(trade, k, v)
        trade.last_update_ts = time.time()
        self._save()
        return trade

    def close_trade(self, trade_id: str) -> Optional[TrackedTrade]:
        """Mark a trade as closed and remove from active tracking."""
        trade = self._trades.get(trade_id)
        if trade is None:
            return None
        trade.status = "CLOSED"
        trade.last_update_ts = time.time()
        # Keep in dict for current session but mark closed
        self._save()
        logger.info(f"[trade_tracker] Closed {trade_id}")
        return trade

    def remove_trade(self, trade_id: str) -> bool:
        """Remove a trade from tracking entirely."""
        if trade_id in self._trades:
            del self._trades[trade_id]
            self._save()
            return True
        return False

    def get_trade(self, trade_id: str) -> Optional[TrackedTrade]:
        """Get a tracked trade by ID."""
        return self._trades.get(trade_id)

    def get_open_trades(self) -> List[TrackedTrade]:
        """Return all trades with OPEN status."""
        return [t for t in self._trades.values() if t.status == "OPEN"]

    def get_all_trades(self) -> List[TrackedTrade]:
        """Return all tracked trades."""
        return list(self._trades.values())

    def has_open_trade(self, mode: Optional[str] = None) -> bool:
        """Check if there's any open trade, optionally filtered by mode."""
        for t in self._trades.values():
            if t.status != "OPEN":
                continue
            if mode is None or t.mode == mode:
                return True
        return False

    def clear_all(self):
        """Clear all tracked trades (for testing or EOD reset)."""
        self._trades.clear()
        self._save()
