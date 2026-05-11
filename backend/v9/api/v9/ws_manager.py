"""V9 WebSocket connection manager with Redis pub/sub."""

import asyncio
import json
import os
import time
from typing import Dict, Set
from fastapi import WebSocket

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HEARTBEAT_INTERVAL = 30  # seconds

# Redis channel names
CHANNEL_BARS_5MIN = "v9:bars:5min"
CHANNEL_BARS_TICK_REVERSAL = "v9:bars:tick_reversal"
CHANNEL_BARS_WOODIES = "v9:bars:woodies"
CHANNEL_BARS_TPO = "v9:bars:tpo"
CHANNEL_MARKERS = "v9:markers:{system_id}"
CHANNEL_SIGNALS = "v9:signals:{system_id}"
CHANNEL_TRADES = "v9:trades"
CHANNEL_ACCOUNT = "v9:account"
CHANNEL_LEVELS = "v9:levels"
CHANNEL_PRICE = "v9:price"


def get_redis_client():
    """Get a synchronous Redis client for publishing."""
    return redis.from_url(REDIS_URL, decode_responses=True)


def publish_event(channel: str, data: dict):
    """Publish an event to a Redis channel. Called from POST endpoints."""
    try:
        r = get_redis_client()
        r.publish(channel, json.dumps(data))
        r.close()
    except Exception:
        # Redis unavailable — degrade gracefully (no WS updates, but API still works)
        pass


class ConnectionManager:
    """Manages WebSocket connections grouped by channel."""

    def __init__(self):
        self._channels: Dict[str, Set[WebSocket]] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self._channels:
            self._channels[channel] = set()
        self._channels[channel].add(websocket)

        # Start listener for this channel if not already running
        if channel not in self._tasks or self._tasks[channel].done():
            self._tasks[channel] = asyncio.create_task(
                self._redis_listener(channel)
            )

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self._channels:
            self._channels[channel].discard(websocket)
            if not self._channels[channel]:
                del self._channels[channel]
                # Cancel listener if no subscribers
                if channel in self._tasks and not self._tasks[channel].done():
                    self._tasks[channel].cancel()
                    del self._tasks[channel]

    async def broadcast(self, channel: str, message: dict):
        """Send message to all clients subscribed to a channel."""
        if channel not in self._channels:
            return
        dead = set()
        for ws in self._channels[channel]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._channels[channel].discard(ws)

    async def send_heartbeat(self, websocket: WebSocket):
        """Send periodic heartbeat to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await websocket.send_json({"type": "heartbeat", "ts": time.time()})
        except Exception:
            pass

    async def _redis_listener(self, channel: str):
        """Subscribe to Redis channel and broadcast to WS clients."""
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.subscribe(channel)

            while channel in self._channels and self._channels[channel]:
                msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg["type"] == "message":
                    data = json.loads(msg["data"])
                    await self.broadcast(channel, {
                        "type": "update",
                        "channel": channel,
                        "data": data,
                        "ts": time.time(),
                    })
                await asyncio.sleep(0.05)

            pubsub.unsubscribe(channel)
            pubsub.close()
            r.close()
        except asyncio.CancelledError:
            pass
        except Exception:
            # Redis connection failed — listener exits gracefully
            pass


# Singleton manager
manager = ConnectionManager()
