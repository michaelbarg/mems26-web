"""V9 stream: Footprint (bid×ask per price level per bar).

Uses VAPRecomputer to read REAL bid/ask from SCID tick data,
replacing the DLL's degraded proportional distribution
(DLL v9.2.0 has MaintainVolumeAtPriceData=0).

DLL footprint.json is IGNORED — Python recomputes from ticks.
"""

import json
import logging
import time

from .base_stream import BaseV9Stream
from .vap_recompute import VAPRecomputer

logger = logging.getLogger("v9_bridge")


class FootprintStream(BaseV9Stream):
    name = "footprint"
    filename = "footprint.json"  # DLL file (monitored but not used for data)
    redis_key = "mems26:v9:footprint"
    api_path = "/api/v9/bars/footprint"

    def __init__(self):
        super().__init__()
        self._recomputer = VAPRecomputer()
        self._recomputer.seek_to_recent(lookback_seconds=5400)  # last 90 min
        self._last_poll_ts: float = 0

    def _tick(self):
        """Override base _tick: use VAPRecomputer instead of DLL file."""
        now = time.time()

        # Heartbeat
        if now - self._last_heartbeat >= 30.0:
            self._send_heartbeat()
            self._last_heartbeat = now

        # Poll SCID for new ticks
        new_ticks = self._recomputer.poll_scid()
        if new_ticks == 0:
            return

        self._consecutive_errors = 0

        # Get recomputed footprint
        data = self._recomputer.get_footprint(num_bars=30)

        logger.info(
            "[%s] Recomputed from %d new ticks — %d bars, cum_delta=%.0f",
            self.name, new_ticks, data["bar_count"], data["cumulative_delta"],
        )

        self.push_count += 1
        self.last_push_ts = time.time()
        self._push_redis(data)
        self._push_api(data)
