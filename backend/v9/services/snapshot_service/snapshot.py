"""CrossSystemSnapshotService — reads all 6 systems' current state from Redis.

Per MEMS26_SPEC_COMPLIANCE_AND_CROSS_SYSTEM_SNAPSHOT_LOCKED V1.1 Section 2.4:
- Captures state of all 6 systems at trade events (entry, target hits, stop, close)
- Reads from Redis keys: mems26:v9:{system_name}:latest
- If a system has no data, returns {status: "unavailable"} (not an error)
- Returns dict ready for V9Trade.cross_context

System mapping (per MASTER_DEV_SKILL):
  1: day_type, 2: chart_5min, 3: tick_reversal, 4: woodies, 5: tpo, 6: killzone
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# System ID to Redis key name mapping (per MASTER_DEV_SKILL naming conventions)
SYSTEM_NAMES: Dict[int, str] = {
    1: "day_type",
    2: "chart_5min",
    3: "tick_reversal",
    4: "woodies",
    5: "tpo",
    6: "killzone",
}

# Redis key template — matches project convention: mems26:v9:{name}:latest
REDIS_KEY_TEMPLATE = "mems26:v9:{name}:latest"

# Required fields per system (per spec Section 2.3)
SYSTEM_FIELDS: Dict[int, tuple] = {
    1: ("day_type", "confidence", "classification_ts", "open_range", "ib_range", "rotation_count"),
    2: ("active_patterns", "last_signal", "current_bar"),
    3: ("current_imbalance", "absorption_signal", "zlr_signal", "last_3_bars_delta"),
    4: ("cci_value", "trend_state", "active_patterns", "last_zero_line_cross"),
    5: ("poc", "vah", "val", "shape", "current_price_zone"),
    6: ("active_zone", "intensity", "minutes_into_zone", "next_zone", "next_zone_in_minutes"),
}


class CrossSystemSnapshotService:
    """Captures a point-in-time snapshot of all 6 MEMS26 systems.

    Used by W11 TradeManager to populate V9Trade.cross_context at
    entry, target hits, stop hits, and manual closes.
    """

    def __init__(self, redis_client: Any = None):
        self._redis = redis_client

    def capture(
        self,
        trigger: str,
        firing_system_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Capture snapshot of all 6 systems' current state.

        Args:
            trigger: Event type — "entry", "t1_hit", "t2_hit", "t3_hit",
                     "stop_hit", "close"
            firing_system_id: Which system fired the trade (1, 2, or 4)

        Returns:
            Dict ready for V9Trade.cross_context array append.
        """
        captured_ts = datetime.now(timezone.utc).isoformat()

        systems: Dict[str, Dict[str, Any]] = {}
        for sys_id in SYSTEM_NAMES:
            systems[str(sys_id)] = self._get_system_state(sys_id)

        snapshot: Dict[str, Any] = {
            "captured_ts": captured_ts,
            "trigger": trigger,
            "firing_system_id": firing_system_id,
            "systems": systems,
            "market": self._get_market_state(),
        }

        return snapshot

    def _get_system_state(self, system_id: int) -> Dict[str, Any]:
        """Fetch a single system's latest state from Redis.

        Returns the system's output dict, or {status: "unavailable"}
        if Redis is down or the key does not exist.
        """
        name = SYSTEM_NAMES[system_id]
        redis_key = REDIS_KEY_TEMPLATE.format(name=name)

        if self._redis is None:
            return {"status": "unavailable"}

        try:
            raw = self._redis.get(redis_key)
            if raw is None:
                return {"status": "unavailable"}
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {"status": "unavailable"}
            return data
        except (ConnectionError, OSError, json.JSONDecodeError, TypeError) as exc:
            logger.warning(
                "Snapshot: system %d (%s) read failed: %s",
                system_id, name, exc,
            )
            return {"status": "unavailable"}

    def _get_market_state(self) -> Dict[str, Any]:
        """Fetch current market state from Redis.

        Returns price/volume/ohlc dict, or {status: "unavailable"}.
        """
        redis_key = "mems26:v9:market:latest"

        if self._redis is None:
            return {"status": "unavailable"}

        try:
            raw = self._redis.get(redis_key)
            if raw is None:
                return {"status": "unavailable"}
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {"status": "unavailable"}
            return data
        except (ConnectionError, OSError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Snapshot: market state read failed: %s", exc)
            return {"status": "unavailable"}
