"""Trade event emitter — publishes lifecycle events to Redis pub/sub.

Channel: v9:trades:events
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger(__name__)

# Redis channel for trade lifecycle events
TRADE_EVENTS_CHANNEL = "v9:trades:events"


class RedisLike(Protocol):
    """Minimal Redis interface for publishing."""

    def publish(self, channel: str, message: str) -> Any: ...


class TradeEventEmitter:
    """Publishes trade lifecycle events to Redis pub/sub."""

    __slots__ = ("_redis",)

    def __init__(self, redis_client: Optional[RedisLike] = None):
        self._redis = redis_client

    def emit(
        self,
        event_type: str,
        trade_id: int,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Emit a trade event. Returns the event payload.

        Events are published to TRADE_EVENTS_CHANNEL as JSON.
        If no Redis client is configured, logs at debug level.
        """
        payload = {
            "event": event_type,
            "trade_id": trade_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }
        message = json.dumps(payload)

        if self._redis is not None:
            try:
                self._redis.publish(TRADE_EVENTS_CHANNEL, message)
            except Exception:
                logger.exception("Failed to publish trade event: %s", event_type)
        else:
            logger.debug("Trade event (no Redis): %s", message)

        return payload
