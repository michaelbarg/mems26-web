"""Price-related event models."""

import time
from typing import Optional

from pydantic import Field

from .base import BaseEvent


class PriceTick(BaseEvent):
    """Live price tick from Sierra Chart DLL (~200ms interval)."""

    event_type: str = "price.tick"
    source: str = "bridge.live_price"

    # Price fields live in payload, but we expose top-level accessors
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    last_size: Optional[float] = None

    @property
    def spread(self) -> Optional[float]:
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None

    def to_stream_dict(self):
        """Override to include price fields in the data blob."""
        d = super().to_stream_dict()
        d["price"] = str(self.price)
        return d


class PriceSnapshot(BaseEvent):
    """Periodic price snapshot with derived fields (1s interval)."""

    event_type: str = "price.snapshot"
    source: str = "bridge.live_price"

    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    vwap: Optional[float] = None
    session_high: Optional[float] = None
    session_low: Optional[float] = None
