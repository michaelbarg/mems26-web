"""Stage B5 — OTF Clarity Mid-Trade · Touch-Point (PROMPT 3 · 3.6).

Purpose: Check if OTF state degraded to State 4 mid-trade.
Reference: Decision Tree V1 § Section 5 · B5
Type: Touch-Point (advisory only · NEVER auto-exits)
Priority Class: ADVISORY_EXIT
Blocking: false
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class B5Output:
    """B5 stage output."""
    clarity_warning: str  # "NO_CLARITY_MID_TRADE" | "NONE"
    action: str  # "TIGHTEN" | "HOLD"


class B5OtfMidTradeQuery:
    """Stage B5 — OTF Clarity Mid-Trade (Touch-Point).

    Queries /api/v9/tpo/current (otf_clarity).
    State 4 (UNCLEAR) → NO_CLARITY_MID_TRADE warning.
    Default action: tighten stop (NOT auto-exit — RULE 14).

    Degraded mode: skip entirely
    """

    priority_class = "ADVISORY_EXIT"

    def evaluate(
        self,
        otf_clarity: Optional[str] = None,
    ) -> B5Output:
        """Evaluate OTF mid-trade per Decision Tree V1 § B5.

        Advisory only — default action TIGHTEN, NEVER auto-exit.
        """
        if otf_clarity is None:
            logger.debug("[B5] OTF clarity unavailable — degraded mode (skip)")
            return B5Output(clarity_warning="NONE", action="HOLD")

        if otf_clarity == "UNCLEAR":
            return B5Output(clarity_warning="NO_CLARITY_MID_TRADE", action="TIGHTEN")

        return B5Output(clarity_warning="NONE", action="HOLD")
