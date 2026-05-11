"""Publish helper — convenience wrapper around EventBus.publish."""

import logging
from typing import Optional

from .bus import EventBus
from .schemas.base import BaseEvent
from .channels import CH_PRICE_TICK, CH_PRICE_SNAPSHOT

logger = logging.getLogger("mems26.event_bus")

# Module-level singleton bus instance
_bus: Optional[EventBus] = None


def get_bus() -> EventBus:
    """Get or create the singleton EventBus instance."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def publish_event(event: BaseEvent, channel: Optional[str] = None) -> Optional[str]:
    """Publish an event to the Event Bus.

    If channel is not specified, infers from event_type:
      price.tick -> CH_PRICE_TICK
      price.snapshot -> CH_PRICE_SNAPSHOT
    """
    if channel is None:
        channel = _infer_channel(event.event_type)
    if channel is None:
        logger.warning("[publisher] Cannot infer channel for event_type=%s", event.event_type)
        return None
    return get_bus().publish(channel, event)


def _infer_channel(event_type: str) -> Optional[str]:
    """Map event_type to channel key."""
    from .channels import (
        CH_PRICE_TICK, CH_PRICE_SNAPSHOT, CH_BAR_5MIN,
        CH_BAR_TICK_REVERSAL, CH_SIGNAL_FIRED, CH_SYSTEM_HEALTH,
    )
    mapping = {
        "price.tick": CH_PRICE_TICK,
        "price.snapshot": CH_PRICE_SNAPSHOT,
        "bar.5min": CH_BAR_5MIN,
        "bar.tick_reversal": CH_BAR_TICK_REVERSAL,
        "signal.fired": CH_SIGNAL_FIRED,
        "system.health": CH_SYSTEM_HEALTH,
    }
    return mapping.get(event_type)
