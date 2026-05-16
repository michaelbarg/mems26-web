"""Stage A2 — Day Type Query · Touch-Point (PROMPT 3 · 3.3).

Purpose: Query Multi-System for today's Day Type to filter pattern relevance.
Reference: Decision Tree V1 § Section 4 · A2
Type: Touch-Point (advisory only · NEVER vetoes)
Blocking: false
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

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


class A2DayTypeQuery:
    """Stage A2 — Day Type Query (Touch-Point).

    Queries /api/v9/day_type/current for today's classification.
    Maps day type → pattern preferences + color volatility expectation.

    Day types (Zohar): TREND, RANGE, REVERSAL, GAP_FILL, BROAD_CHANNEL, NEUTRAL
    Degraded mode: no preference (all patterns equally weighted)
    Terminal states: None (advisory only — NEVER vetoes per RULE 14)
    """

    def evaluate(self, day_type: Optional[str] = None) -> A2Output:
        """Evaluate day type query per Decision Tree V1 § A2.

        Advisory only — returns preferences, NEVER blocks entry.
        Degraded mode (day_type=None): no preference, MEDIUM volatility.
        """
        if day_type is None:
            logger.debug("[A2] Day type unavailable — degraded mode (no preference)")
            return A2Output(pattern_preference=[], color_volatility_expectation="MEDIUM")

        prefs = PATTERN_PREFERENCES.get(day_type, [])
        vol = VOLATILITY_EXPECTATIONS.get(day_type, "MEDIUM")

        return A2Output(pattern_preference=prefs, color_volatility_expectation=vol)
