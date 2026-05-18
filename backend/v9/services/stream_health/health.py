"""StreamHealthService — in-memory per-stream health tracking.

Tracks push timestamps, error counts, and dispatch timestamps for all
canonical Bridge streams.  Computes a traffic-light status per stream:
    GREEN  — last push < 10s, no recent errors
    YELLOW — last push 10-60s OR errors present
    RED    — last push > 60s OR never received
    GREY   — market closed (all streams stale > 5min)

No DB writes.  Thread-safe via threading.Lock.
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Canonical stream names (per MASTER_DEV_SKILL naming conventions)
STREAM_NAMES: List[str] = [
    "live_price",
    "tick_reversal_15",
    "tick_reversal_12",
    "footprint",
    "volume_profile",
    "imbalance_flags",
    "stacked_imbalances",
    "cumulative_delta",
    "woodies_30min",
    "woodies_5min",  # D-074: primary S4 stream
    "tpo",
    "5min",
]

# Thresholds (seconds)
GREEN_THRESHOLD = 10.0
YELLOW_THRESHOLD = 60.0
GREY_THRESHOLD = 300.0  # 5 minutes — all stale => market closed
ERROR_WINDOW = 60.0     # errors within this window count


class _StreamState:
    """Per-stream mutable state."""

    __slots__ = (
        "name", "last_bridge_push_ts", "push_count",
        "errors", "last_dispatch_ts", "subscribed_systems",
    )

    def __init__(self, name: str) -> None:
        self.name: str = name
        self.last_bridge_push_ts: float = 0.0
        self.push_count: int = 0
        self.errors: List[float] = []  # timestamps of recent errors
        self.last_dispatch_ts: float = 0.0
        self.subscribed_systems: List[int] = []


class StreamHealthService:
    """In-memory health tracker for all canonical Bridge streams."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._streams: Dict[str, _StreamState] = {
            name: _StreamState(name) for name in STREAM_NAMES
        }
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_ts: float = 0.0

    # ── Recording methods (called from bars.py / EventDispatcher) ──

    def record_push(self, stream_name: str) -> None:
        """Record a successful Bridge push for a stream."""
        with self._lock:
            state = self._streams.get(stream_name)
            if state is None:
                logger.warning("[StreamHealth] unknown stream: %s", stream_name)
                return
            state.last_bridge_push_ts = time.time()
            state.push_count += 1

    def record_error(self, stream_name: str, error: str) -> None:
        """Record a processing error for a stream."""
        with self._lock:
            state = self._streams.get(stream_name)
            if state is None:
                return
            state.errors.append(time.time())

    def record_dispatch(self, stream_name: str, system_id: int) -> None:
        """Record that EventDispatcher routed a bar for this stream."""
        with self._lock:
            state = self._streams.get(stream_name)
            if state is None:
                return
            state.last_dispatch_ts = time.time()

    def set_subscribed_systems(self, stream_name: str, system_ids: List[int]) -> None:
        """Set the subscribed system IDs for a stream (from routing table)."""
        with self._lock:
            state = self._streams.get(stream_name)
            if state is None:
                return
            state.subscribed_systems = list(system_ids)

    # ── Query methods ──

    def get_all_streams(self) -> Dict[str, Any]:
        """Return full health snapshot with 1-second caching."""
        now = time.time()
        with self._lock:
            if self._cache is not None and (now - self._cache_ts) < 1.0:
                return self._cache

        result = self._compute_snapshot(now)
        with self._lock:
            self._cache = result
            self._cache_ts = now
        return result

    def _compute_snapshot(self, now: float) -> Dict[str, Any]:
        """Build the full health response dict (not cached)."""
        streams_data: List[Dict[str, Any]] = []
        summary = {"green": 0, "yellow": 0, "red": 0, "grey": 0}

        with self._lock:
            all_stale = True
            for state in self._streams.values():
                age = now - state.last_bridge_push_ts if state.last_bridge_push_ts > 0 else -1
                if age >= 0 and age < GREY_THRESHOLD:
                    all_stale = False

        with self._lock:
            for state in self._streams.values():
                age = now - state.last_bridge_push_ts if state.last_bridge_push_ts > 0 else -1
                recent_errors = [
                    ts for ts in state.errors if (now - ts) < ERROR_WINDOW
                ]
                # Prune old errors
                state.errors = recent_errors

                error_count = len(recent_errors)
                status, color = self._compute_status(
                    age, error_count, all_stale,
                )

                streams_data.append({
                    "name": state.name,
                    "status": status,
                    "color": color,
                    "age_sec": round(age, 1) if age >= 0 else None,
                    "push_count": state.push_count,
                    "error_count": error_count,
                    "subscribed_systems": list(state.subscribed_systems),
                    "last_push_ts": state.last_bridge_push_ts if state.last_bridge_push_ts > 0 else None,
                })
                summary[color] += 1

        from datetime import datetime, timezone
        return {
            "streams": streams_data,
            "summary": summary,
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _compute_status(age_sec: float, error_count: int, all_stale: bool):
        """Determine status label and color for a single stream.

        Returns:
            (status_str, color_str) tuple.
        """
        # Never received
        if age_sec < 0:
            if all_stale:
                return "market_closed", "grey"
            return "no_data", "red"

        # All streams stale > 5min => market closed
        if all_stale and age_sec >= GREY_THRESHOLD:
            return "market_closed", "grey"

        # RED: stale > 60s
        if age_sec > YELLOW_THRESHOLD:
            return "stale", "red"

        # YELLOW: 10-60s OR errors
        if age_sec > GREEN_THRESHOLD or error_count > 0:
            return "degraded", "yellow"

        # GREEN
        return "healthy", "green"
