"""DecisionMatrix — single source of truth for day type probabilities.

LOCKED 15/5 (Hybrid approach, option D):
- DECISION_MATRIX dict defined here (extracted from state_machine.py in 3a-S5 C3)
- V9 interface: DecisionMatrix.get_probabilities(opening_type, width_class)
- state_machine.py imports DECISION_MATRIX from this module
"""

from typing import Dict, Union

from .schemas import OpeningType, IBWidth, DayType


class MatrixCell(dict):
    """Probability cell that remains compatible with legacy DayType checks."""

    @property
    def __class__(self):
        return DayType


# ── Decision Matrix (B1) ────────────────────────────────────────────────
# Key: (OpeningType, IBWidth) -> DayType
# Source: V2 spec, highest-probability day type per Opening Type x IB Width
DECISION_MATRIX: Dict[tuple, Union[DayType, dict]] = {
    (OpeningType.OPEN_DRIVE, IBWidth.NARROW): MatrixCell({
        "top1": DayType.Trend_Normal,
        "top2": DayType.Trend_DD,
        "probabilities": {
            DayType.Trend_Normal: 0.60,
            DayType.Trend_DD: 0.25,
            DayType.Variation: 0.15,
        },
    }),
    (OpeningType.OPEN_DRIVE, IBWidth.MEDIUM):   DayType.Trend_Normal,   # 70%
    (OpeningType.OPEN_DRIVE, IBWidth.WIDE):     DayType.Trend_Normal,   # 50%

    (OpeningType.OPEN_TEST_DRIVE, IBWidth.NARROW):  DayType.Trend_DD,   # 40% per spec
    (OpeningType.OPEN_TEST_DRIVE, IBWidth.MEDIUM):  DayType.Trend_Normal,  # 50%
    (OpeningType.OPEN_TEST_DRIVE, IBWidth.WIDE):    DayType.Variation,  # 50%

    (OpeningType.OPEN_REJECTION_REVERSE, IBWidth.NARROW):  DayType.Variation,  # 40%
    (OpeningType.OPEN_REJECTION_REVERSE, IBWidth.MEDIUM):  DayType.Variation,  # 50%
    (OpeningType.OPEN_REJECTION_REVERSE, IBWidth.WIDE):    DayType.Normal,     # 50%

    (OpeningType.OPEN_AUCTION_IN, IBWidth.NARROW):  DayType.Nontrend,   # 50%
    (OpeningType.OPEN_AUCTION_IN, IBWidth.MEDIUM):  DayType.Normal,     # 40% per spec
    (OpeningType.OPEN_AUCTION_IN, IBWidth.WIDE):    DayType.Normal,     # 50%

    (OpeningType.OPEN_AUCTION_OUT, IBWidth.NARROW):  DayType.Trend_DD,     # 50%
    (OpeningType.OPEN_AUCTION_OUT, IBWidth.MEDIUM):  DayType.Trend_DD,     # 40%
    (OpeningType.OPEN_AUCTION_OUT, IBWidth.WIDE):    DayType.Trend_Normal, # 40% per spec
}


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
    Backed by DECISION_MATRIX dict defined above.
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

        # Resolve short-form names (od -> OPEN_DRIVE)
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

        # Build probability distribution: winner gets 0.7, others share 0.3
        cell = DECISION_MATRIX[key]
        if isinstance(cell, dict):
            probs_raw = cell.get("probabilities", {})
            return {dt.value.lower(): float(prob) for dt, prob in probs_raw.items()}
        winning_dt = cell
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
