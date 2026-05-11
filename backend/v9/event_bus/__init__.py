"""MEMS26 Event Bus — Redis Streams-backed pub/sub for real-time events."""

from .bus import EventBus
from .publisher import publish_event, get_bus
from .subscriber import StreamSubscriber
from .channels import (
    CH_PRICE_TICK, CH_PRICE_SNAPSHOT, CH_BAR_5MIN,
    CH_BAR_TICK_REVERSAL, CH_SIGNAL_FIRED, CH_SYSTEM_HEALTH,
)
from .correlation import get_session_id, new_session_id
from .schemas.base import BaseEvent
from .schemas.price import PriceTick, PriceSnapshot
