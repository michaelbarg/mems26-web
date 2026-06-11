"""Stage A2 — Day Type Query · Touch-Point (PROMPT 3 · 3.3).

Purpose: Query Multi-System for today's Day Type to filter pattern relevance.
Reference: Decision Tree V1 § Section 4 · A2
Type: Touch-Point (advisory only · NEVER vetoes)
Blocking: false

W-3 extension: also emits 9 MatrixVerdict objects from the 63-cell
day-type matrix (DayTypeGate). Advisory only — terminal is always None.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.v9.systems.woodies.day_type_gate import (
    DayType,
    DayTypeGate,
    MatrixVerdict,
    PatternId,
)

logger = logging.getLogger(__name__)

# Day Type → preferred patterns per Decision Tree V1 § A2
PATTERN_PREFERENCES = {
    "TREND": ["ZLR", "TT", "TLB", "GB100"],
    "Normal": ["ZLR", "TT", "TLB", "GB100"],  # alias
    "RANGE": ["HFE", "FAMIR"],
    "REVERSAL": ["VEGAS", "GHOST", "FAMIR"],
    "GAP_FILL": [],  # bias INITIATIVE (handled in A6)
    "BROAD_CHANNEL": ["HFE", "FAMIR"],
    "NEUTRAL": [],
}

VOLATILITY_EXPECTATIONS = {
    "TREND": "LOW",
    "Normal": "LOW",
    "RANGE": "HIGH",
    "REVERSAL": "HIGH",
    "GAP_FILL": "MEDIUM",
    "BROAD_CHANNEL": "HIGH",
    "NEUTRAL": "MEDIUM",
}


@dataclass
class A2Output:
    """A2 stage output."""
    pattern_preference: List[str]
    color_volatility_expectation: str  # "LOW" | "MEDIUM" | "HIGH"
    matrix_verdicts: List[MatrixVerdict] = field(default_factory=list)


# Mapping from Zohar day-type strings to Dalton DayType enum values.
# When the Multi-System returns a Zohar label we map it to the closest
# Dalton taxonomy member for the 63-cell matrix lookup.
_ZOHAR_TO_DALTON: Dict[str, DayType] = {
    # S1 state_machine labels → Dalton day-type codes
    "Trend_Normal": DayType.TN,
    "Trend_DD": DayType.TDD,
    "Variation": DayType.NV,
    "Normal": DayType.Norm,
    "Neutral_Extreme": DayType.NeuE,
    "Neutral_Center": DayType.NeuC,
    "Nontrend": DayType.NT,
    # Legacy labels (backward compat)
    "TREND": DayType.TN,
    "RANGE": DayType.NeuC,
    "REVERSAL": DayType.NeuE,
    "GAP_FILL": DayType.NV,
    "BROAD_CHANNEL": DayType.Norm,
    "NEUTRAL": DayType.NT,
}


class A2DayTypeQuery:
    """Stage A2 — Day Type Query (Touch-Point).

    Queries /api/v9/day_type/current for today's classification.
    Maps day type → pattern preferences + color volatility expectation.
    W-3: also emits 9 MatrixVerdict objects from 63-cell day-type matrix.

    Day types (Zohar): TREND, RANGE, REVERSAL, GAP_FILL, BROAD_CHANNEL, NEUTRAL
    Degraded mode: no preference (all patterns equally weighted)
    Terminal states: None (advisory only — NEVER vetoes per RULE 14)
    """

    def __init__(self) -> None:
        try:
            self._gate = DayTypeGate()
        except FileNotFoundError:
            logger.warning("[A2] DayTypeGate YAML missing — matrix verdicts disabled")
            self._gate = None

    def _get_matrix_verdicts(self, dalton_dt: DayType) -> List[MatrixVerdict]:
        """Query the 63-cell matrix for all 9 patterns against a day type."""
        if self._gate is None:
            return []
        verdicts = []
        for pid in PatternId:
            verdicts.append(self._gate.get_verdict(pid, dalton_dt))
        return verdicts

    def evaluate(self, day_type: Optional[str] = None) -> A2Output:
        """Evaluate day type query per Decision Tree V1 § A2.

        Advisory only — returns preferences, NEVER blocks entry.
        Degraded mode (day_type=None): no preference, MEDIUM volatility.
        """
        if day_type is None:
            logger.debug("[A2] Day type unavailable — degraded mode (no preference)")
            verdicts = self._get_matrix_verdicts(DayType.UNAVAILABLE)
            return A2Output(
                pattern_preference=[],
                color_volatility_expectation="MEDIUM",
                matrix_verdicts=verdicts,
            )

        prefs = PATTERN_PREFERENCES.get(day_type, [])
        vol = VOLATILITY_EXPECTATIONS.get(day_type, "MEDIUM")

        # Map Zohar label → Dalton for matrix lookup
        dalton_dt = _ZOHAR_TO_DALTON.get(day_type, DayType.UNAVAILABLE)
        verdicts = self._get_matrix_verdicts(dalton_dt)

        return A2Output(
            pattern_preference=prefs,
            color_volatility_expectation=vol,
            matrix_verdicts=verdicts,
        )
