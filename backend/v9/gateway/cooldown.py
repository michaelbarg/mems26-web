"""ζ.A4 — 2-Stop Cooldown + ζ.A5 — Cluster Guard D-037.

Risk filters that gate trade entry at the gateway level.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

COOLDOWN_MINUTES = 30
CLUSTER_WINDOW_SEC = 60
CLUSTER_MAX_TRADES = 5
CLUSTER_BLOCK_MINUTES = 5


class CooldownManager:
    """ζ.A4: Block new entries for 30min after 2 consecutive stops."""

    def __init__(self):
        self.consecutive_stops: int = 0
        self.cooldown_until: Optional[datetime] = None

    def on_trade_close(self, outcome: str) -> None:
        if outcome == "STOP":
            self.consecutive_stops += 1
            if self.consecutive_stops >= 2:
                self.cooldown_until = datetime.utcnow() + timedelta(minutes=COOLDOWN_MINUTES)
                logger.info("[Cooldown] 2 consecutive stops → cooldown until %s",
                            self.cooldown_until.isoformat())
        else:
            self.consecutive_stops = 0
            self.cooldown_until = None

    def is_blocked(self) -> bool:
        if self.cooldown_until and datetime.utcnow() < self.cooldown_until:
            return True
        if self.cooldown_until and datetime.utcnow() >= self.cooldown_until:
            self.cooldown_until = None
            self.consecutive_stops = 0
        return False

    def get_state(self) -> dict:
        remaining = 0
        if self.cooldown_until:
            remaining = max(0, (self.cooldown_until - datetime.utcnow()).total_seconds())
        return {
            "consecutive_stops": self.consecutive_stops,
            "cooldown_active": self.is_blocked(),
            "cooldown_remaining_sec": round(remaining),
            "reasoning_notes": f"2-stop cooldown: {self.consecutive_stops} consecutive stops"
                               + (f", blocked {remaining:.0f}s remaining" if self.is_blocked() else ""),
        }


class ClusterGuard:
    """ζ.A5: Block new entries if 5+ trades attempted within 60s (D-037)."""

    def __init__(self):
        self._attempt_timestamps: list = []
        self._blocked_until: Optional[datetime] = None

    def record_attempt(self) -> None:
        now = time.time()
        self._attempt_timestamps.append(now)
        # Trim old entries
        cutoff = now - CLUSTER_WINDOW_SEC
        self._attempt_timestamps = [t for t in self._attempt_timestamps if t > cutoff]
        if len(self._attempt_timestamps) >= CLUSTER_MAX_TRADES:
            self._blocked_until = datetime.utcnow() + timedelta(minutes=CLUSTER_BLOCK_MINUTES)
            logger.info("[ClusterGuard] D-037: %d trades in %ds → blocked 5min",
                        len(self._attempt_timestamps), CLUSTER_WINDOW_SEC)

    def is_blocked(self) -> bool:
        if self._blocked_until and datetime.utcnow() < self._blocked_until:
            return True
        if self._blocked_until and datetime.utcnow() >= self._blocked_until:
            self._blocked_until = None
        return False

    def get_state(self) -> dict:
        remaining = 0
        if self._blocked_until:
            remaining = max(0, (self._blocked_until - datetime.utcnow()).total_seconds())
        return {
            "recent_attempts": len(self._attempt_timestamps),
            "cluster_guard_active": self.is_blocked(),
            "block_remaining_sec": round(remaining),
            "reasoning_notes": f"D-037 cluster guard: {len(self._attempt_timestamps)} attempts in 60s"
                               + (f", blocked {remaining:.0f}s" if self.is_blocked() else ""),
        }
