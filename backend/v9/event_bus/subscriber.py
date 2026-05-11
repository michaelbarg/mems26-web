"""Subscribe helper — polls a Redis Stream for new events.

Designed for use in background threads (Bridge streams) or
async loops (WebSocket relay).
"""

import logging
import time
import threading
from typing import Callable, Dict, Optional

from .bus import EventBus
from .schemas.base import BaseEvent

logger = logging.getLogger("mems26.event_bus")


class StreamSubscriber:
    """Polls a Redis Stream and calls a handler for each new event.

    Usage:
        sub = StreamSubscriber("mems26:events:price.tick", handler_fn)
        sub.start()  # runs in background thread
        ...
        sub.stop()
    """

    def __init__(
        self,
        channel: str,
        handler: Callable[[str, Dict[str, str]], None],
        bus: Optional[EventBus] = None,
        poll_interval: float = 0.1,
        batch_size: int = 50,
    ):
        self.channel = channel
        self.handler = handler
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self._bus = bus or EventBus()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_id = "0"

    def start(self) -> None:
        """Start polling in a background daemon thread."""
        self._thread = threading.Thread(
            target=self._poll_loop,
            name=f"sub:{self.channel}",
            daemon=True,
        )
        self._thread.start()
        logger.info("[Subscriber] started on %s", self.channel)

    def stop(self) -> None:
        """Signal the polling thread to stop."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def poll_once(self) -> int:
        """Poll once and process entries. Returns count of entries processed."""
        # Use XRANGE from last_id (exclusive) to + with COUNT.
        # Upstash REST doesn't support '(' exclusive syntax, so we
        # increment the sequence number to make the start exclusive.
        start = self._last_id
        if start != "0":
            parts = start.split("-")
            if len(parts) == 2:
                start = f"{parts[0]}-{int(parts[1]) + 1}"

        entries = self._bus.read(self.channel, last_id=start, count=self.batch_size)
        for entry_id, fields in entries:
            try:
                self.handler(entry_id, fields)
            except Exception:
                logger.exception("[Subscriber] handler error for %s entry %s", self.channel, entry_id)
            self._last_id = entry_id
        return len(entries)

    def _poll_loop(self) -> None:
        """Main poll loop — runs until stop() is called."""
        # Start from the latest entry (don't replay history).
        # Use XREVRANGE to get the last entry's ID.
        result = self._bus._cmd(["XREVRANGE", self.channel, "+", "-", "COUNT", "1"])
        if result and len(result) > 0:
            self._last_id = result[0][0]
        else:
            self._last_id = "0"

        while not self._stop.is_set():
            try:
                count = self.poll_once()
                if count == 0:
                    self._stop.wait(self.poll_interval)
            except Exception:
                logger.exception("[Subscriber] poll error on %s", self.channel)
                self._stop.wait(1.0)
