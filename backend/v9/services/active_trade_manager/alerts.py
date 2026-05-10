"""W15 Alert Emitter — publishes active trade alerts to Redis pub/sub.

Channel: v9:trades:alerts
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger(__name__)

# Redis channel for active trade alerts
TRADE_ALERTS_CHANNEL = "v9:trades:alerts"


class RedisLike(Protocol):
    """Minimal Redis interface for publishing."""

    def publish(self, channel: str, message: str) -> Any: ...


class AlertEmitter:
    """Publishes active trade monitoring alerts to Redis pub/sub."""

    __slots__ = ("_redis",)

    def __init__(self, redis_client: Optional[RedisLike] = None):
        self._redis = redis_client

    def _emit(
        self,
        alert_type: str,
        trade_id: int,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Internal: emit an alert payload to Redis.

        Returns the full payload dict.
        """
        payload: Dict[str, Any] = {
            "trade_id": trade_id,
            "alert_type": alert_type,
            "ts": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }
        message = json.dumps(payload)

        if self._redis is not None:
            try:
                self._redis.publish(TRADE_ALERTS_CHANNEL, message)
            except Exception:
                logger.exception(
                    "Failed to publish alert: %s for trade %d",
                    alert_type, trade_id,
                )
        else:
            logger.debug("Alert (no Redis): %s", message)

        return payload

    def emit_approaching_target(
        self,
        trade_id: int,
        target_name: str,
        distance_pct: float,
    ) -> Dict[str, Any]:
        """Alert: price approaching a target level."""
        return self._emit("approaching_target", trade_id, {
            "target_name": target_name,
            "distance_pct": round(distance_pct, 4),
        })

    def emit_approaching_stop(
        self,
        trade_id: int,
        distance_pct: float,
    ) -> Dict[str, Any]:
        """Alert: price approaching stop level."""
        return self._emit("approaching_stop", trade_id, {
            "distance_pct": round(distance_pct, 4),
        })

    def emit_smart_be_triggered(
        self,
        trade_id: int,
        new_stop: float,
    ) -> Dict[str, Any]:
        """Alert: Smart BE triggered — stop moved to breakeven."""
        return self._emit("smart_be_triggered", trade_id, {
            "new_stop": new_stop,
        })

    def emit_time_exit_suggestion(
        self,
        trade_id: int,
        reason: str,
    ) -> Dict[str, Any]:
        """Alert: time-based exit suggestion (e.g., approaching 14:30 ET cutoff)."""
        return self._emit("time_exit_suggestion", trade_id, {
            "reason": reason,
        })
