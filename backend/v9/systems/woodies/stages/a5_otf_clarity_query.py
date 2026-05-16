"""Stage A5 — OTF Clarity Query · Touch-Point (PROMPT 3 · 3.3).

Purpose: Get OTF Clarity State to warn on chaotic market conditions.
Reference: Decision Tree V1 § Section 4 · A5
Type: Touch-Point (advisory only · NEVER vetoes)
Blocking: false
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class A5Output:
    """A5 stage output."""
    clarity_warning: str  # "NONE" | "NO_CLARITY" | "DIRECTION_MISMATCH"
    otf_state_value: str  # "BOTH_CLEAR" | "SELLERS_CLEAR" | "BUYERS_CLEAR" | "UNCLEAR" | "UNAVAILABLE"


class A5OtfClarityQuery:
    """Stage A5 — OTF Clarity Query (Touch-Point).

    Queries /api/v9/tpo/current (otf_clarity field).
    OTF states: BOTH_CLEAR, SELLERS_CLEAR, BUYERS_CLEAR, UNCLEAR.

    State mapping per Decision Tree V1 § A5:
      BOTH_CLEAR → safe (no warning)
      SELLERS_CLEAR + LONG → safe (sellers suffering)
      BUYERS_CLEAR + SHORT → safe (buyers suffering)
      UNCLEAR → NO_CLARITY warning (but no veto — RULE 14)
      Mismatch → DIRECTION_MISMATCH warning

    Degraded mode: skip entirely, proceed to A6
    Terminal states: None (advisory only)
    """

    def evaluate(
        self,
        otf_clarity: Optional[str] = None,
        entry_direction: Optional[str] = None,
    ) -> A5Output:
        """Evaluate OTF clarity per Decision Tree V1 § A5.

        Advisory only — returns warnings, NEVER blocks entry.
        """
        if otf_clarity is None:
            logger.debug("[A5] OTF clarity unavailable — degraded mode (skip)")
            return A5Output(clarity_warning="NONE", otf_state_value="UNAVAILABLE")

        state = otf_clarity

        # BOTH_CLEAR → always safe
        if state == "BOTH_CLEAR":
            return A5Output(clarity_warning="NONE", otf_state_value=state)

        # SELLERS_CLEAR + LONG → safe (sellers are suffering)
        if state == "SELLERS_CLEAR" and entry_direction == "LONG":
            return A5Output(clarity_warning="NONE", otf_state_value=state)

        # BUYERS_CLEAR + SHORT → safe (buyers are suffering)
        if state == "BUYERS_CLEAR" and entry_direction == "SHORT":
            return A5Output(clarity_warning="NONE", otf_state_value=state)

        # UNCLEAR → NO_CLARITY warning
        if state == "UNCLEAR":
            return A5Output(clarity_warning="NO_CLARITY", otf_state_value=state)

        # Mismatch: SELLERS_CLEAR + SHORT or BUYERS_CLEAR + LONG
        return A5Output(clarity_warning="DIRECTION_MISMATCH", otf_state_value=state)
