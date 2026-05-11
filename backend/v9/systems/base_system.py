"""BaseSystem abstract class + Signal dataclass for V9 system wiring.

Every trading system (firing, observer, gate) implements BaseSystem.
The EventDispatcher reads subscribed_streams to build its routing table,
then calls analyze() on each bar received for a matching stream.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Signal:
    """Actionable signal emitted by a firing system's analyze() method.

    Observers return None (no trade signals).
    Gates return None (they control whether firing systems can execute).
    """
    system_id: int
    classification: str          # e.g. "BREAKOUT", "ZLR", "TREND_DAY"
    direction: str               # "LONG" or "SHORT"
    confidence: float            # 0.0 - 1.0
    entry_price: Optional[float] = None
    stop: Optional[float] = None
    targets: Optional[List[float]] = None  # T1, T2, T3
    metadata: dict = field(default_factory=dict)


class BaseSystem(abc.ABC):
    """Abstract base class that every V9 system must implement.

    Subclasses declare:
        subscribed_streams: list of stream names this system needs
        system_id: integer ID per MASTER_DEV_SKILL
        name: human-readable name

    The EventDispatcher calls analyze() whenever a bar arrives on a
    subscribed stream.
    """

    subscribed_streams: List[str] = []
    system_id: int = 0
    name: str = ""

    @abc.abstractmethod
    def analyze(self, stream_name: str, bar: dict) -> Optional[Signal]:
        """Process a bar from the given stream.

        Args:
            stream_name: Which stream delivered this bar.
            bar: Raw bar dict from the Bridge POST payload.

        Returns:
            Signal if the system wants to fire a trade setup.
            None if no actionable signal (observers always return None).
        """
        ...
