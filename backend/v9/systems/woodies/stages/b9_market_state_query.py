"""Stage B9 — Market State Query · Touch-Point (PROMPT 3 · 3.6).

Purpose: Detect momentum loss to suggest partial close.
Reference: Decision Tree V1 § Section 5 · B9
Type: Touch-Point (advisory only · NEVER auto-exits)
Priority Class: PARTIAL
Blocking: false
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class B9Output:
    """B9 stage output."""
    momentum_warning: str  # "LOST" | "NONE"
    action: str  # "PARTIAL_CLOSE" | "HOLD"


class B9MarketStateQuery:
    """Stage B9 — Market State Query (Touch-Point).

    Queries /api/v9/layer0/state for market state.
    If EXTENDING → SEARCHING transition: momentum_warning = LOST.
    Suggests partial close C2 early, hold C3 trail.
    NEVER auto-exits (RULE 14).

    Degraded mode: skip entirely
    """

    priority_class = "PARTIAL"

    def evaluate(
        self,
        market_state: Optional[str] = None,
        prev_market_state: Optional[str] = None,
        t1_hit: bool = False,
    ) -> B9Output:
        """Evaluate market state per Decision Tree V1 § B9.

        Advisory only — suggests partial close, NEVER auto-exits.
        """
        if market_state is None:
            logger.debug("[B9] Market state unavailable — degraded mode (skip)")
            return B9Output(momentum_warning="NONE", action="HOLD")

        # Detect EXTENDING → SEARCHING transition
        if prev_market_state == "EXPANDING" and market_state == "SEARCHING":
            if t1_hit:
                return B9Output(momentum_warning="LOST", action="PARTIAL_CLOSE")
            return B9Output(momentum_warning="LOST", action="HOLD")

        return B9Output(momentum_warning="NONE", action="HOLD")
