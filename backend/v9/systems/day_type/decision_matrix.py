"""DecisionMatrix wrapper around DECISION_MATRIX dict.

LOCKED 15/5 (Hybrid approach · option D):
- DECISION_MATRIX dict stays inline in state_machine.py (will be extracted in 3a-S5)
- This module provides V9 interface: get_probabilities(opening_type, width_class)
- Wraps the existing dict · zero data duplication
"""

from typing import Dict

from .state_machine import DECISION_MATRIX
from .schemas import OpeningType, IBWidth, DayType


# Short-form names accepted by get_probabilities (Mind Over Markets convention)
_SHORT_TO_OPENING: Dict[str, str] = {
    "od": "OPEN_DRIVE",
    "otd": "OPEN_TEST_DRIVE",
    "orr": "OPEN_REJECTION_REVERSE",
    "oa_in": "OPEN_AUCTION_IN",
    "oa_out": "OPEN_AUCTION_OUT",
}


class DecisionMatrix:
    """V9 interface for day type probabilities by (opening_type, width_class).

    Source: PROMPT 3a-S3 Section B (LOCKED 15/5)
    Backed by existing DECISION_MATRIX dict in state_machine.py.
    """

    def get_probabilities(
        self, opening_type: str, width_class: str
    ) -> Dict[str, float]:
        """Return probability distribution across all 6 day types.

        Args:
            opening_type: enum value or short name (e.g., "OPEN_DRIVE" or "od")
            width_class: enum value (e.g., "NARROW", "MEDIUM", "WIDE")

        Returns:
            Dict mapping day_type string (lowercase) to probability (0.0-1.0).
            Winner gets 0.7, others share 0.3.
        """
        ot_raw = (
            opening_type.value if hasattr(opening_type, "value")
            else str(opening_type)
        )
        wc_raw = (
            width_class.value if hasattr(width_class, "value")
            else str(width_class)
        ).upper()

        # Resolve short-form names (od → OPEN_DRIVE)
        ot_upper = _SHORT_TO_OPENING.get(ot_raw.lower(), ot_raw.upper())

        # Look up enums
        try:
            ot_enum = OpeningType(ot_upper)
            wc_enum = IBWidth(wc_raw)
        except ValueError:
            return {dt.value.lower(): 1.0 / 6.0 for dt in DayType if dt != DayType.UNKNOWN}

        key = (ot_enum, wc_enum)
        if key not in DECISION_MATRIX:
            return {dt.value.lower(): 1.0 / 6.0 for dt in DayType if dt != DayType.UNKNOWN}

        # DECISION_MATRIX maps (OpeningType, IBWidth) -> DayType (winning type)
        # Build probability distribution: winner gets 0.7, others share 0.3
        winning_dt = DECISION_MATRIX[key]
        non_winners = [dt for dt in DayType if dt != DayType.UNKNOWN and dt != winning_dt]
        share = 0.3 / len(non_winners) if non_winners else 0.0
        probs: Dict[str, float] = {}
        for dt in DayType:
            if dt == DayType.UNKNOWN:
                continue
            if dt == winning_dt:
                probs[dt.value.lower()] = 0.7
            else:
                probs[dt.value.lower()] = share
        return probs
