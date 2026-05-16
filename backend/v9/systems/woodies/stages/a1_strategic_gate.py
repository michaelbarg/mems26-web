"""Stage A1 — Strategic Gate (PROMPT 3 · 3.2).

Purpose: Determine direction allowed per CCI 14 vs Zero Line behavior over 6+ bars.
Reference: Decision Tree V1 § Section 4 · A1
Type: Woodies Core (independent decision)
"""

from dataclasses import dataclass
from typing import List

# Configurable threshold: consecutive bars above/below zero
BARS_PERSISTENCE_REQUIRED = 6
# Frequent crosses threshold: 3+ crosses in last 10 bars → GREY
FREQUENT_CROSS_THRESHOLD = 3
CROSS_LOOKBACK = 10


@dataclass
class A1Output:
    """A1 stage output."""
    direction_allowed: str  # "LONG" | "SHORT" | "NONE"
    color: str  # "BLUE" | "RED" | "GREY" | "YELLOW" | "INDETERMINATE"


class A1StrategicGate:
    """Stage A1 — Strategic Gate.

    Determines which trade direction is allowed based on CCI 14 vs Zero Line
    behavior over 6+ consecutive bars.

    Colors:
      BLUE  — CCI > 0 for 6+ bars → LONG allowed
      RED   — CCI < 0 for 6+ bars → SHORT allowed
      GREY  — frequent zero-line crosses → wait
      YELLOW — sustained trend changing to opposite → stand aside
      INDETERMINATE — else → wait

    Terminal states: SKIP (color veto on GREY/YELLOW/INDETERMINATE)
    """

    def evaluate(
        self,
        cci_14_value: float,
        cci_14_history: List[float],
        zero_line: float = 0,
    ) -> A1Output:
        """Evaluate strategic gate per Decision Tree V1 § A1."""
        if not cci_14_history:
            return A1Output(direction_allowed="NONE", color="INDETERMINATE")

        # Count consecutive bars on current side of zero from most recent
        consecutive_above = 0
        consecutive_below = 0
        for val in reversed(cci_14_history):
            if val > zero_line:
                if consecutive_below > 0:
                    break
                consecutive_above += 1
            elif val < zero_line:
                if consecutive_above > 0:
                    break
                consecutive_below += 1
            else:
                break  # exactly on zero line breaks streak

        # Count zero-line crosses in lookback window
        lookback = cci_14_history[-CROSS_LOOKBACK:] if len(cci_14_history) >= CROSS_LOOKBACK else cci_14_history
        crosses = 0
        for i in range(1, len(lookback)):
            if (lookback[i - 1] > zero_line and lookback[i] < zero_line) or \
               (lookback[i - 1] < zero_line and lookback[i] > zero_line):
                crosses += 1

        # GREY: frequent crosses (choppy market)
        if crosses >= FREQUENT_CROSS_THRESHOLD:
            return A1Output(direction_allowed="NONE", color="GREY")

        # BLUE: sustained above zero
        if consecutive_above >= BARS_PERSISTENCE_REQUIRED:
            # Check for YELLOW: was previously RED (sustained below) before this BLUE run
            if self._was_opposite_trend(cci_14_history, zero_line, current_side="above"):
                return A1Output(direction_allowed="NONE", color="YELLOW")
            return A1Output(direction_allowed="LONG", color="BLUE")

        # RED: sustained below zero
        if consecutive_below >= BARS_PERSISTENCE_REQUIRED:
            if self._was_opposite_trend(cci_14_history, zero_line, current_side="below"):
                return A1Output(direction_allowed="NONE", color="YELLOW")
            return A1Output(direction_allowed="SHORT", color="RED")

        # Not enough persistence yet
        return A1Output(direction_allowed="NONE", color="INDETERMINATE")

    def _was_opposite_trend(
        self,
        history: List[float],
        zero_line: float,
        current_side: str,
    ) -> bool:
        """Detect if there was a sustained opposite trend before current run.

        YELLOW = color just changed from sustained opposite (trend transition).
        Look before the current consecutive run for a prior sustained run on
        the opposite side.
        """
        # Skip the current consecutive run
        idx = len(history) - 1
        if current_side == "above":
            while idx >= 0 and history[idx] > zero_line:
                idx -= 1
        else:
            while idx >= 0 and history[idx] < zero_line:
                idx -= 1

        if idx < BARS_PERSISTENCE_REQUIRED - 1:
            return False

        # Count consecutive bars on opposite side before the transition
        opposite_count = 0
        if current_side == "above":
            while idx >= 0 and history[idx] < zero_line:
                opposite_count += 1
                idx -= 1
        else:
            while idx >= 0 and history[idx] > zero_line:
                opposite_count += 1
                idx -= 1

        return opposite_count >= BARS_PERSISTENCE_REQUIRED
