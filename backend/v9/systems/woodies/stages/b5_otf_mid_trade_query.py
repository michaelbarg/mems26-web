"""Stage B5 — OTF Clarity Mid-Trade · Touch-Point (PROMPT 2 · 2.3 stub).

Purpose: Check if OTF state degraded to State 4 mid-trade.
Reference: Decision Tree V1 § Section 5 · B5
Type: Touch-Point (advisory only · NEVER auto-exits)
Priority Class: ADVISORY_EXIT
Blocking: false
Logic: PROMPT 3
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class B5Output:
    """B5 stage output."""
    clarity_warning: str  # "NO_CLARITY_MID_TRADE" | "NONE"
    action: str  # "TIGHTEN" | "HOLD"


class B5OtfMidTradeQuery:
    """Stage B5 — OTF Clarity Mid-Trade (Touch-Point).

    Queries /api/v9/tpo/current (otf_clarity).
    State 4 (UNCLEAR) → NO_CLARITY_MID_TRADE warning.
    Default action: tighten stop (NOT auto-exit).

    Degraded mode: skip entirely
    """

    priority_class = "ADVISORY_EXIT"

    def evaluate(
        self,
        otf_clarity: Optional[str] = None,
    ) -> B5Output:
        """Evaluate OTF mid-trade. STUB: returns NONE/HOLD."""
        # STUB: real logic in PROMPT 3
        return B5Output(clarity_warning="NONE", action="HOLD")
