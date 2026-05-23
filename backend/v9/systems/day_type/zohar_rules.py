"""Zohar Rules Engine — 6 evaluation rules for day-type refinement.

Sources:
  - Zohar, "Mastering Market Profile" (2016), Chapters 4-7
  - Dalton, "Mind Over Markets" (1990), pp.63-102
  - Dalton, "Markets in Profile" (2007), pp.45-68

Rules:
  alpha  — TREND_DD invalidation if price returns to IB (Zohar Ch.5 §5.3)
  beta   — Open Drive break detection (Mind Over Markets p.65)
  gamma  — Test Drive failure when reversal doesn't hold (Zohar Ch.4 §4.7)
  delta  — Both-side extension → NEUTRAL (Mind Over Markets p.87)
  width  — Max TPO row > 5 letters indicates Normal day (Zohar Ch.6 §6.2)
  timing — VARIATION before 12:30, TREND_DD after (Zohar Ch.7 §7.1)
"""

from __future__ import annotations

from datetime import time
from enum import Enum
from typing import Optional

from .schemas import DayType


class RuleVerdict(str, Enum):
    """Outcome of a rule evaluation."""
    INVALIDATE = "INVALIDATE"    # current classification is wrong
    CONFIRM = "CONFIRM"          # current classification is supported
    UPGRADE = "UPGRADE"          # switch to a stronger classification
    DOWNGRADE = "DOWNGRADE"      # switch to a weaker classification
    NO_OPINION = "NO_OPINION"    # rule does not apply


class ZoharRulesEngine:
    """Six evaluation methods for day-type refinement.

    Constants:
        MIDDAY_CUTOFF — time(12, 30): dividing line for timing bias
            (Zohar Ch.7 §7.1: reversals before midday lean VARIATION,
            trend continuation after midday leans TREND_DD)
        WIDTH_MAX_LETTERS — 5: max TPO letters in widest row before
            switching to Normal day (Zohar Ch.6 §6.2)
    """

    # Zohar Ch.7 §7.1: midday cutoff for timing-based bias
    MIDDAY_CUTOFF: time = time(12, 30)

    # Zohar Ch.6 §6.2: TPO width threshold for Normal day detection
    WIDTH_MAX_LETTERS: int = 5

    def evaluate_alpha(
        self,
        current_type: DayType,
        price: float,
        ib_high: float,
        ib_low: float,
    ) -> RuleVerdict:
        """Alpha rule: TREND_DD invalidation.

        If the current classification is Trend_DD but price has returned
        inside the IB range, the trend thesis is invalidated.

        Source: Zohar Ch.5 §5.3 — "A Trend Double-Distribution day requires
        price to remain outside the IB. Return to IB negates the pattern."
        """
        if current_type != DayType.Trend_DD:
            return RuleVerdict.NO_OPINION
        if ib_low <= price <= ib_high:
            return RuleVerdict.INVALIDATE
        return RuleVerdict.CONFIRM

    def evaluate_beta(
        self,
        opening_is_drive: bool,
        drive_direction_up: bool,
        current_price: float,
        open_price: float,
    ) -> RuleVerdict:
        """Beta rule: Open Drive break detection.

        If opening was an Open Drive but price has broken back through
        the open, the drive has failed.

        Source: Mind Over Markets p.65 — "An Open Drive that retraces
        fully back through the opening print signals drive failure."
        """
        if not opening_is_drive:
            return RuleVerdict.NO_OPINION
        if drive_direction_up and current_price < open_price:
            return RuleVerdict.INVALIDATE
        if not drive_direction_up and current_price > open_price:
            return RuleVerdict.INVALIDATE
        return RuleVerdict.CONFIRM

    def evaluate_gamma(
        self,
        opening_is_test_drive: bool,
        reversal_held: bool,
    ) -> RuleVerdict:
        """Gamma rule: Test Drive failure.

        If opening was a Test Drive but the reversal didn't hold,
        the test drive pattern has failed.

        Source: Zohar Ch.4 §4.7 — "An Open Test Drive that fails to
        sustain the reversal degrades to Open Auction behavior."
        """
        if not opening_is_test_drive:
            return RuleVerdict.NO_OPINION
        if not reversal_held:
            return RuleVerdict.INVALIDATE
        return RuleVerdict.CONFIRM

    def evaluate_delta(
        self,
        extensions_up: int,
        extensions_down: int,
    ) -> RuleVerdict:
        """Delta rule: Both-side extension → NEUTRAL (NeuE or NeuC per D-091.Q1).

        If price has extended beyond both IB high and IB low,
        the day should be classified as Neutral subtype (no directional conviction).
        NeuE/NeuC classification done downstream by neutral_classifier.py.

        Source: Mind Over Markets p.87 — "Extensions in both directions
        during a single session indicate a Neutral day structure."
        """
        if extensions_up > 0 and extensions_down > 0:
            return RuleVerdict.DOWNGRADE  # → Neutral
        return RuleVerdict.NO_OPINION

    def evaluate_width(
        self,
        max_tpo_count: int,
    ) -> RuleVerdict:
        """Width rule: wide TPO row indicates Normal day.

        If the widest TPO row has more than WIDTH_MAX_LETTERS letters,
        the market is building value (rotating) — consistent with Normal day.

        Source: Zohar Ch.6 §6.2 — "A TPO row exceeding 5 letters shows
        sustained two-sided trade, characteristic of a Normal day."
        """
        if max_tpo_count > self.WIDTH_MAX_LETTERS:
            return RuleVerdict.DOWNGRADE  # suggests Normal day
        return RuleVerdict.NO_OPINION

    def evaluate_timing_bias(
        self,
        current_time: time,
        has_reversal: bool,
        has_trend_continuation: bool,
    ) -> Optional[DayType]:
        """Timing bias: classification hint based on time of day.

        - Reversal before MIDDAY_CUTOFF (12:30) → VARIATION
        - Trend continuation after MIDDAY_CUTOFF → TREND_DD

        Source: Zohar Ch.7 §7.1 — "Reversals developing before midday
        typically resolve as Variation days. Trend continuation emerging
        in the afternoon session points toward Double-Distribution."

        Returns:
            Suggested DayType or None if no timing bias applies.
        """
        if has_reversal and current_time < self.MIDDAY_CUTOFF:
            return DayType.Variation
        if has_trend_continuation and current_time >= self.MIDDAY_CUTOFF:
            return DayType.Trend_DD
        return None
