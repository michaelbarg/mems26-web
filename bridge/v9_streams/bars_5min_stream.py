"""V9 stream: 5-minute OHLCV bars (System 2 data feed).

Source: DLL export — 5min.json.
"""

import logging
import sqlite3
from typing import Optional

from .base_stream import BaseV9Stream

logger = logging.getLogger("mems26.bars_5min_stream")

# Path to local DB for backfill query — same default as db/session.py
import os as _os
_DB_PATH = _os.environ.get("DATABASE_URL", "sqlite:///./data/mems26_local.db")
_DB_PATH = _DB_PATH.replace("sqlite:///", "") if _DB_PATH.startswith("sqlite") else "./data/mems26_local.db"


class Bars5MinStream(BaseV9Stream):
    name = "bars_5min"
    filename = "5min.json"
    redis_key = "mems26:v9:bars_5min"
    api_path = "/api/v9/bars/5min"

    def __init__(self):
        super().__init__()
        self._first_push = True
        self._last_db_ts: Optional[float] = None
        # Query MAX(ts) from DB on startup for backfill
        try:
            conn = sqlite3.connect(_DB_PATH)
            row = conn.execute("SELECT MAX(ts) FROM v9_bars_5min").fetchone()
            conn.close()
            if row and row[0]:
                # ts is stored as ISO string — parse to epoch for comparison
                from datetime import datetime, timezone
                try:
                    dt = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    self._last_db_ts = dt.timestamp()
                except (ValueError, TypeError):
                    self._last_db_ts = float(row[0]) if isinstance(row[0], (int, float)) else None
            if self._last_db_ts:
                logger.info("[bars_5min] startup backfill anchor: last_db_ts=%.0f", self._last_db_ts)
        except Exception as e:
            logger.warning("[bars_5min] could not query MAX(ts) for backfill: %s", e)

    def _push_api(self, data: dict):
        """On first push after startup, backfill bars since last DB ts.

        Subsequent pushes send only the latest bar (normal mode).
        Restart recovery (Michael-approved 2026-05-30): prevents bar gaps.
        """
        bars = data.get("bars")
        if not isinstance(bars, list) or not bars:
            return super()._push_api(data)

        if self._first_push and self._last_db_ts is not None:
            # Backfill: send all bars after last_db_ts
            backfill = [b for b in bars if b.get("ts") and float(b["ts"]) > self._last_db_ts]
            self._first_push = False
            if backfill:
                logger.info("[bars_5min] backfill: sending %d bars (of %d) since ts=%.0f",
                            len(backfill), len(bars), self._last_db_ts)
                backfill_data = dict(data)
                backfill_data["bars"] = backfill
                return super()._push_api(backfill_data)
            # No bars to backfill — fall through to latest-only
        else:
            self._first_push = False

        # Normal mode: send only latest bar
        latest_only = dict(data)
        latest_only["bars"] = [bars[-1]]
        return super()._push_api(latest_only)
