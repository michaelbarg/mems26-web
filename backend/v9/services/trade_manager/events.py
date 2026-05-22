"""Trade event emitter — publishes lifecycle events to Redis pub/sub and WS.

Channel: v9:trades:events
WS:      /ws/v9/price (same manager, type="trade.event")
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger(__name__)

# Main asyncio loop — injected at startup so synchronous emit() can
# schedule WS broadcasts without blocking the calling thread.
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_trade_events_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called at startup to inject the FastAPI event loop for WS broadcasts."""
    global _main_loop
    _main_loop = loop


async def _broadcast_trade_event(payload: dict) -> None:
    """Broadcast trade event to all WS clients (price manager reused)."""
    try:
        from backend.v9.ws.manager import price_ws_manager
        await price_ws_manager.broadcast({"type": "trade.event", "data": payload})
    except Exception:
        pass

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

        # WS broadcast — fire-and-forget on main loop
        if _main_loop is not None and _main_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                _broadcast_trade_event(payload), _main_loop
            )

        return payload
