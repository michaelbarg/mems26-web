"""WebSocket connection manager for Event Bus channels.

Separate from the existing ws_manager.py (which uses Redis pub/sub).
This manager reads from Redis Streams (Event Bus) and relays to WS clients.
"""

import asyncio
import json
import logging
import os
import time
import urllib.request
import urllib.error
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger("mems26.ws")

REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
HEARTBEAT_INTERVAL = 30


class EventBusWSManager:
    """Manages WS connections that relay events from Redis Streams."""

    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._relay_task: asyncio.Task = None
        self._last_stream_id: str = "$"

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.add(ws)
        logger.info("[WS:price] client connected (%d total)", len(self._clients))

        # Start relay if not running
        if self._relay_task is None or self._relay_task.done():
            self._relay_task = asyncio.create_task(self._relay_loop())

    def disconnect(self, ws: WebSocket):
        self._clients.discard(ws)
        logger.info("[WS:price] client disconnected (%d remain)", len(self._clients))
        if not self._clients and self._relay_task and not self._relay_task.done():
            self._relay_task.cancel()
            self._relay_task = None

    async def broadcast(self, data: dict):
        dead = set()
        for ws in self._clients:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._clients.discard(ws)

    async def _relay_loop(self):
        """Poll Redis Streams and relay price.tick events to WS clients."""
        stream_key = "mems26:events:price.tick"

        # Get the latest entry ID to start from "now"
        last_id = await self._get_latest_id(stream_key)

        while self._clients:
            try:
                entries = await self._xrange(stream_key, last_id, count=50)
                for entry_id, fields in entries:
                    event_data = self._parse_entry(fields)
                    if event_data:
                        await self.broadcast({
                            "type": "price.tick",
                            "data": event_data,
                            "ts": time.time(),
                        })
                    last_id = entry_id

                await asyncio.sleep(0.1)  # 100ms poll
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("[WS:price] relay error")
                await asyncio.sleep(1.0)

    async def _get_latest_id(self, stream_key: str) -> str:
        """Get the last entry ID from the stream."""
        result = await self._redis_cmd(["XREVRANGE", stream_key, "+", "-", "COUNT", "1"])
        if result and len(result) > 0:
            return result[0][0]
        return "0"

    async def _xrange(self, stream_key: str, last_id: str, count: int = 50):
        """Read entries after last_id."""
        # Increment sequence for exclusive start
        start = last_id
        if start != "0":
            parts = start.split("-")
            if len(parts) == 2:
                start = f"{parts[0]}-{int(parts[1]) + 1}"

        result = await self._redis_cmd(["XRANGE", stream_key, start, "+", "COUNT", str(count)])
        if not result:
            return []

        entries = []
        for entry in result:
            entry_id = entry[0]
            fields = entry[1]
            if isinstance(fields, list):
                d = {}
                for i in range(0, len(fields), 2):
                    d[fields[i]] = fields[i + 1]
                entries.append((entry_id, d))
            elif isinstance(fields, dict):
                entries.append((entry_id, fields))
        return entries

    def _parse_entry(self, fields: dict) -> dict:
        """Parse stream entry fields into a WS message payload."""
        if "data" in fields:
            try:
                return json.loads(fields["data"])
            except (json.JSONDecodeError, TypeError):
                pass
        # Fallback: use fields directly
        return {
            "event_type": fields.get("event_type", "price.tick"),
            "price": float(fields["price"]) if "price" in fields else None,
            "ts_ms": int(fields["ts_ms"]) if "ts_ms" in fields else None,
            "correlation_id": fields.get("correlation_id"),
        }

    async def _redis_cmd(self, args: list):
        """Execute Redis command via Upstash REST (async via run_in_executor)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._redis_cmd_sync, args)

    def _redis_cmd_sync(self, args: list):
        if not REDIS_URL or not REDIS_TOKEN:
            return None
        try:
            body = json.dumps(args).encode()
            req = urllib.request.Request(
                REDIS_URL,
                data=body,
                headers={
                    "Authorization": f"Bearer {REDIS_TOKEN}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get("result")
        except urllib.error.URLError:
            return None


# Singleton
price_ws_manager = EventBusWSManager()
