"""ζ.B2 — Suffering Side Veto (D-049 LOCKED).

Determines which side of the market is "suffering" (trapped traders)
and vetoes entries aligned with that side.

Suffering side = direction where recent stops/exits cluster + volume
shows trapped participants. Entry in that direction = joining losers.
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 🟡 V1 thresholds — calibrate post-SHADOW
LOOKBACK_TRADES = 10
SUFFERING_THRESHOLD = 0.6  # 60% of recent outcomes must be negative


class SufferingSideVeto:
    """D-049: Veto fires aligned with the suffering side."""

    def __init__(self):
        self._recent_outcomes: list = []  # list of {"direction": "LONG"|"SHORT", "outcome": "WIN"|"STOP"}
        self._suffering_side: Optional[str] = None

    def record_outcome(self, direction: str, outcome: str) -> None:
        self._recent_outcomes.append({"direction": direction, "outcome": outcome})
        if len(self._recent_outcomes) > LOOKBACK_TRADES:
            self._recent_outcomes = self._recent_outcomes[-LOOKBACK_TRADES:]
        self._recompute()

    def _recompute(self) -> None:
        if len(self._recent_outcomes) < 3:
            self._suffering_side = None
            return

        long_stops = sum(1 for o in self._recent_outcomes if o["direction"] == "LONG" and o["outcome"] == "STOP")
        short_stops = sum(1 for o in self._recent_outcomes if o["direction"] == "SHORT" and o["outcome"] == "STOP")
        long_total = sum(1 for o in self._recent_outcomes if o["direction"] == "LONG")
        short_total = sum(1 for o in self._recent_outcomes if o["direction"] == "SHORT")

        long_fail_rate = long_stops / max(long_total, 1)
        short_fail_rate = short_stops / max(short_total, 1)

        if long_fail_rate >= SUFFERING_THRESHOLD and long_total >= 2:
            self._suffering_side = "LONG"
        elif short_fail_rate >= SUFFERING_THRESHOLD and short_total >= 2:
            self._suffering_side = "SHORT"
        else:
            self._suffering_side = None

    def check_veto(self, direction: str) -> bool:
        """Return True if this direction is VETOED (aligned with suffering side)."""
        return self._suffering_side == direction

    def get_state(self) -> dict:
        return {
            "suffering_side": self._suffering_side,
            "recent_outcomes": len(self._recent_outcomes),
            "veto_active": self._suffering_side is not None,
            "reasoning_notes": f"D-049 SSV: suffering_side={self._suffering_side or 'NONE'}, "
                               f"{len(self._recent_outcomes)} recent outcomes tracked",
        }
