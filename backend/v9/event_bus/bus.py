"""EventBus — Redis Streams-backed event bus for MEMS26.

Uses Upstash Redis REST API (same pattern as existing bridge streams)
for compatibility with the Upstash infrastructure already in use.
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, List, Optional, Tuple

from .schemas.base import BaseEvent

logger = logging.getLogger("mems26.event_bus")

REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

# Max stream length — auto-trim old entries
STREAM_MAXLEN = 1000


def _redis_cmd(args: list) -> Any:
    """Execute a Redis command via Upstash REST API."""
    if not REDIS_URL or not REDIS_TOKEN:
        logger.debug("[EventBus] Redis not configured, skipping")
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
    except urllib.error.URLError as e:
        logger.warning("[EventBus] Redis cmd %s error: %s", args[0], e)
        return None


class EventBus:
    """Redis Streams-backed event bus.

    Publish: XADD to stream key with auto-ID and MAXLEN trim.
    Subscribe: XREAD with blocking for real-time consumption.
    """

    def __init__(self, redis_url: str = "", redis_token: str = ""):
        self._redis_url = redis_url or REDIS_URL
        self._redis_token = redis_token or REDIS_TOKEN

    def _cmd(self, args: list) -> Any:
        """Execute Redis command with instance credentials."""
        if not self._redis_url or not self._redis_token:
            return None
        try:
            body = json.dumps(args).encode()
            req = urllib.request.Request(
                self._redis_url,
                data=body,
                headers={
                    "Authorization": f"Bearer {self._redis_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get("result")
        except urllib.error.URLError as e:
            logger.warning("[EventBus] Redis cmd %s error: %s", args[0], e)
            return None

    def publish(self, channel: str, event: BaseEvent) -> Optional[str]:
        """Publish an event to a Redis Stream.

        Returns the stream entry ID, or None on failure.
        """
        data = event.to_stream_dict()
        # XADD channel MAXLEN ~ 1000 * field1 value1 field2 value2 ...
        args = ["XADD", channel, "MAXLEN", "~", str(STREAM_MAXLEN), "*"]
        for k, v in data.items():
            args.extend([k, v])

        result = self._cmd(args)
        if result:
            logger.debug("[EventBus] published %s to %s: %s", event.event_type, channel, result)
        return result

    def read(
        self, channel: str, last_id: str = "0", count: int = 10
    ) -> List[Tuple[str, Dict[str, str]]]:
        """Read entries from a stream (non-blocking).

        Returns list of (entry_id, field_dict) tuples.
        """
        result = self._cmd(["XRANGE", channel, last_id, "+", "COUNT", str(count)])
        if not result:
            return []

        entries = []
        for entry in result:
            entry_id = entry[0]
            fields = entry[1]
            # Upstash returns fields as flat list [k1, v1, k2, v2, ...]
            if isinstance(fields, list):
                d = {}
                for i in range(0, len(fields), 2):
                    d[fields[i]] = fields[i + 1]
                entries.append((entry_id, d))
            elif isinstance(fields, dict):
                entries.append((entry_id, fields))
        return entries

    def stream_length(self, channel: str) -> int:
        """Get the length of a stream."""
        result = self._cmd(["XLEN", channel])
        return int(result) if result is not None else 0

    def trim(self, channel: str, maxlen: int = STREAM_MAXLEN) -> None:
        """Trim a stream to maxlen entries."""
        self._cmd(["XTRIM", channel, "MAXLEN", "~", str(maxlen)])
