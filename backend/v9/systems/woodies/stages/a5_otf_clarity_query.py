"""Stage A5 — OTF Clarity Query · Touch-Point (PROMPT 2 · 2.2 stub).

Purpose: Get OTF Clarity State to warn on chaotic market conditions.
Reference: Decision Tree V1 § Section 4 · A5
Type: Touch-Point (advisory only · NEVER vetoes)
Blocking: false
Logic: PROMPT 3
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class A5Output:
    """A5 stage output."""
    clarity_warning: str  # "NONE" | "NO_CLARITY" | "DIRECTION_MISMATCH"
    otf_state_value: str  # "BOTH_CLEAR" | "SELLERS_CLEAR" | "BUYERS_CLEAR" | "UNCLEAR" | "UNAVAILABLE"


class A5OtfClarityQuery:
    """Stage A5 — OTF Clarity Query (Touch-Point).

    Queries /api/v9/tpo/current (otf_clarity field).
    OTF states: BOTH_CLEAR (1), SELLERS_CLEAR (2), BUYERS_CLEAR (3), UNCLEAR (4).
    State 4 → NO_CLARITY warning. Direction mismatch → DIRECTION_MISMATCH.

    Degraded mode: skip clarity check, proceed to A6
    Terminal states: None (advisory only)
    """

    def evaluate(
        self,
        otf_clarity: Optional[str] = None,
        entry_direction: Optional[str] = None,
    ) -> A5Output:
        """Evaluate OTF clarity. STUB: returns NONE/UNAVAILABLE."""
        # STUB: real logic in PROMPT 3
        return A5Output(
            clarity_warning="NONE",
            otf_state_value="UNAVAILABLE",
        )
