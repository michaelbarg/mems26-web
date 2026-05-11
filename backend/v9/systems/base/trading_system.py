"""BaseV9TradingSystem — abstract base for all 6 V9 trading systems.

AP-SY01: Every system MUST extend this class.
AP-A01: Architecture consistency enforced here.

Per D-041 (Per-System Independence):
  Each system owns its own analysis, events, and persistence.
Per D-073 (Decision vs Context Flow):
  FIRING systems publish entry decisions.
  OBSERVING systems publish context that FIRING systems may read.
  NOTE: Day Type is FIRING in that it "fires" its classification
  (publishes own decision output), even though it doesn't generate
  trade entries. Its output is consumed as context by other systems.
"""

import abc
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mems26.systems")


class SystemType(str, Enum):
    FIRING = "FIRING"
    OBSERVING = "OBSERVING"


class BaseV9TradingSystem(abc.ABC):
    """Abstract base for all V9 trading systems.

    Subclasses must define:
      - system_id: int (1-6)
      - name: str
      - color: str (hex color from design system)
      - system_type: SystemType
      - subscribed_channels: list of Event Bus channels to consume

    Subclasses must implement:
      - process(event): handle an incoming event
      - publish(event_data): publish output event to Event Bus
    """

    system_id: int = 0
    name: str = ""
    color: str = "#888888"
    system_type: SystemType = SystemType.OBSERVING
    subscribed_channels: List[str] = []

    @abc.abstractmethod
    def process(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an incoming event from subscribed channels.

        Args:
            event: Deserialized event dict from the Event Bus.

        Returns:
            Output event dict to publish, or None if no output.
        """
        ...

    def publish(self, event_data: Dict[str, Any]) -> Optional[str]:
        """Publish an output event to the Event Bus.

        Default implementation uses the event_bus publisher.
        Override for custom publishing behavior.
        """
        from backend.v9.event_bus.publisher import get_bus
        from backend.v9.event_bus.schemas.base import BaseEvent

        event = BaseEvent(
            event_type=event_data.get("event_type", f"system.{self.name}"),
            source=f"system.{self.name}",
            payload=event_data,
        )
        channel = event_data.get("channel", f"mems26:events:system.{self.name}")
        return get_bus().publish(channel, event)

    def persist(self, data: Dict[str, Any]) -> None:
        """Persist system output to its dedicated DB table.

        Override in subclass to write to system-specific table.
        Default: no-op (logging only).
        """
        logger.debug("[%s] persist called (no-op base)", self.name)

    def subscribe(self) -> List[str]:
        """Return list of Event Bus channels this system subscribes to."""
        return self.subscribed_channels

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.system_id} name={self.name} type={self.system_type.value}>"
