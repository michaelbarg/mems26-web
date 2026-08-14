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
        """Relay price.tick events to WS clients.

        ROOT-FIX 2026-08-14 (Michael: "המערכת לא מצליחה לקבל נתונים בצורה שוטפת
        והוא מתנתק או על stale — זה לא היה לנו"): this loop only ever read the
        Upstash CLOUD Redis stream. That instance no longer resolves (DNS
        failure), so every read returned None: the socket stayed OPEN while
        zero ticks were sent, the store's lastUpdateMs went cold and the UI
        showed stale → disconnected. Meanwhile the local feed was perfectly
        healthy (sierra_state 0.5-2s, live_price.json ~250ms).
        A local-only stack must not depend on a cloud hop for its own screen
        (CLAUDE.md § Bridge Local-Only). Redis stays as the primary path when
        it answers; otherwise we broadcast straight from the LOCAL price file,
        which is the same truth the trading path reads.
        """
        stream_key = "mems26:events:price.tick"
        last_id = await self._get_latest_id(stream_key)
        redis_ok = last_id is not None
        if not redis_ok:
            logger.warning("[WS:price] Redis unavailable — relaying from local "
                           "live_price.json (screen stays live)")
        last_file_ts = None

        while self._clients:
            try:
                sent = False
                if redis_ok:
                    entries = await self._xrange(stream_key, last_id, count=50)
                    if entries is None:
                        redis_ok = False
                        logger.warning("[WS:price] Redis went silent — switching "
                                       "to local live_price.json")
                    else:
                        for entry_id, fields in entries:
                            event_data = self._parse_entry(fields)
                            if event_data:
                                await self.broadcast({
                                    "type": "price.tick",
                                    "data": event_data,
                                    "ts": time.time(),
                                })
                                sent = True
                            last_id = entry_id

                if not redis_ok:
                    tick = self._local_price_tick()
                    if tick and tick.get("ts_ms") != last_file_ts:
                        last_file_ts = tick.get("ts_ms")
                        await self.broadcast({
                            "type": "price.tick", "data": tick, "ts": time.time(),
                        })
                        sent = True

                await asyncio.sleep(0.1 if sent else 0.25)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("[WS:price] relay error")
                await asyncio.sleep(1.0)

    @staticmethod
    def _local_price_tick():
        """Read the local Sierra price export → price.tick payload (or None)."""
        try:
            path = os.path.join(
                os.getenv("V9_EXPORT_DIR",
                          os.path.expanduser("~/SierraChart_Data/v9_export")),
                "live_price.json")
            with open(path, "r") as fh:
                d = json.load(fh)
            price = d.get("last") or d.get("price") or d.get("last_price")
            if price is None:
                return None
            ts = d.get("ts") or d.get("timestamp") or time.time()
            return {
                "price": float(price),
                "bid": float(d["bid"]) if d.get("bid") not in (None, "") else None,
                "ask": float(d["ask"]) if d.get("ask") not in (None, "") else None,
                "last_size": d.get("last_size") or d.get("size"),
                "ts_ms": int(float(ts) * 1000) if float(ts) < 1e12 else int(float(ts)),
            }
        except Exception:
            return None

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
