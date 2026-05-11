"""CandleBuilder — builds candles from tick data and stores in Redis.

Receives individual ticks (price, volume, timestamp), aggregates them into
time-based candles, and emits completed candles. Stores recent candles in
Redis as mems26:candles (list capped at 500).
"""

import json
import time
import logging
import urllib.request
import urllib.error
import os
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger("v9_bridge")

REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
CANDLE_REDIS_KEY = "mems26:candles"
MAX_CANDLES = 500


@dataclass
class Candle:
    """A single OHLCV candle."""
    ts_open: float = 0.0
    ts_close: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    tick_count: int = 0

    def to_dict(self) -> dict:
        return {
            "ts_open": self.ts_open,
            "ts_close": self.ts_close,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "tick_count": self.tick_count,
        }


class CandleBuilder:
    """Builds time-based candles from tick data.

    Args:
        interval_seconds: Candle duration in seconds (default 60 = 1-min candles).
    """

    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self._current: Optional[Candle] = None
        self._completed: List[Candle] = []

    def _candle_start(self, ts: float) -> float:
        """Compute the start timestamp for the candle containing ts."""
        return ts - (ts % self.interval_seconds)

    def add_tick(self, price: float, volume: int = 1, ts: Optional[float] = None) -> Optional[Candle]:
        """Add a tick and return a completed Candle if the interval rolled over.

        Args:
            price: Tick price.
            volume: Tick volume (contracts).
            ts: Tick timestamp (epoch seconds). Uses time.time() if None.

        Returns:
            A completed Candle if the previous candle closed, else None.
        """
        if ts is None:
            ts = time.time()

        candle_start = self._candle_start(ts)
        completed = None

        if self._current is None:
            self._current = Candle(
                ts_open=candle_start,
                ts_close=ts,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                tick_count=1,
            )
        elif candle_start > self._current.ts_open:
            # New candle period — finalize the current one
            completed = self._current
            self._completed.append(completed)
            self._push_candle_to_redis(completed)

            self._current = Candle(
                ts_open=candle_start,
                ts_close=ts,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                tick_count=1,
            )
        else:
            # Same candle period — update OHLCV
            self._current.ts_close = ts
            self._current.high = max(self._current.high, price)
            self._current.low = min(self._current.low, price)
            self._current.close = price
            self._current.volume += volume
            self._current.tick_count += 1

        return completed

    def get_current(self) -> Optional[Candle]:
        """Return the in-progress candle (not yet closed)."""
        return self._current

    def get_completed(self) -> List[Candle]:
        """Return all completed candles this session."""
        return list(self._completed)

    def _push_candle_to_redis(self, candle: Candle):
        """Push a completed candle to Redis list mems26:candles."""
        if not REDIS_URL or not REDIS_TOKEN:
            return
        payload = json.dumps(candle.to_dict())
        try:
            # LPUSH
            body = json.dumps(["LPUSH", CANDLE_REDIS_KEY, payload]).encode()
            req = urllib.request.Request(
                REDIS_URL,
                data=body,
                headers={
                    "Authorization": f"Bearer {REDIS_TOKEN}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)

            # LTRIM to cap at MAX_CANDLES
            body2 = json.dumps(["LTRIM", CANDLE_REDIS_KEY, "0", str(MAX_CANDLES - 1)]).encode()
            req2 = urllib.request.Request(
                REDIS_URL,
                data=body2,
                headers={
                    "Authorization": f"Bearer {REDIS_TOKEN}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(req2, timeout=10)
        except urllib.error.URLError as e:
            logger.warning(f"[candle_builder] Redis push error: {e}")
