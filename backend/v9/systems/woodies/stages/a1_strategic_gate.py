"""Stage A1 — Strategic Gate (PROMPT 3 · 3.2).

Purpose: Determine direction allowed per CCI 14 vs Zero Line behavior over 6+ bars.
Reference: Decision Tree V1 § Section 4 · A1
Type: Woodies Core (independent decision)

Trend states per D-092 §Trend State (4 states):
  BLUE   — uptrend confirmed → LONG allowed
  RED    — downtrend confirmed → SHORT allowed
  YELLOW — transition (5th opposite bar) → BLOCK ALL per P-W5 LOCK A
           (Algorithm 2: sustained-persistence. See also cci_calc.py Algorithm 1.)
           Defense-in-depth rationale: docs/notes/YELLOW_DETECTION.md
  GRAY   — chop / no trend → BLOCK (or confidence > 0.55 gate)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class TrendState(str, Enum):
    """4 trend states per D-092 §Trend State."""
    BLUE   = "BLUE"    # uptrend confirmed
    RED    = "RED"     # downtrend confirmed
    YELLOW = "YELLOW"  # transition · 5th opposite bar · BLOCK ALL per P-W5
    GRAY   = "GRAY"    # chop / no trend


# Configurable threshold: consecutive bars above/below zero
BARS_PERSISTENCE_REQUIRED = 6
# Frequent crosses threshold: 3+ crosses in last 10 bars → GRAY
FREQUENT_CROSS_THRESHOLD = 3
CROSS_LOOKBACK = 10
# Liran Stage-1: at least 1 bar must exceed ±100 for BLUE/RED
STAGE1_CCI_THRESHOLD = 100


@dataclass
class StrategicGateResult:
    """A1 stage output."""
    direction_allowed: str  # "LONG" | "SHORT" | "NONE"
    color: TrendState
    terminal: Optional[str] = None  # None if proceed · "SKIP — ..." if blocked
    metadata: dict = field(default_factory=dict)


class A1StrategicGate:
    """Stage A1 — Strategic Gate.

    Determines which trade direction is allowed based on CCI 14 vs Zero Line
    behavior over 6+ consecutive bars.

    Colors per D-092 §Trend State:
      BLUE   — CCI > 0 for 6+ bars + ≥1 bar >+100 (Liran Stage-1) → LONG allowed
      RED    — CCI < 0 for 6+ bars + ≥1 bar <-100 (mirror) → SHORT allowed
      YELLOW — sustained trend changing to opposite (5th bar) → BLOCK ALL (P-W5)
      GRAY   — chop / no trend → BLOCK

    Terminal states: SKIP (color veto on GRAY/YELLOW)
    """

    def evaluate(
        self,
        cci_14_value: float,
        cci_14_history: List[float],
        zero_line: float = 0,
    ) -> StrategicGateResult:
        """Evaluate strategic gate per Decision Tree V1 § A1."""
        if not cci_14_history:
            return StrategicGateResult(
                direction_allowed="NONE",
                color=TrendState.GRAY,
                terminal="SKIP — color veto (GRAY)",
                metadata={"reason": "empty history"},
            )

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

        # GRAY: frequent crosses (choppy market)
        if crosses >= FREQUENT_CROSS_THRESHOLD:
            return StrategicGateResult(
                direction_allowed="NONE",
                color=TrendState.GRAY,
                terminal="SKIP — color veto (GRAY)",
                metadata={"reason": "frequent_crosses", "crosses": crosses},
            )

        # Liran Stage-1: check if any bar exceeded ±100 in the consecutive run
        has_stage1_above = any(v > STAGE1_CCI_THRESHOLD for v in cci_14_history[-consecutive_above:]) if consecutive_above > 0 else False
        has_stage1_below = any(v < -STAGE1_CCI_THRESHOLD for v in cci_14_history[-consecutive_below:]) if consecutive_below > 0 else False

        # BLUE: sustained above zero + Stage-1
        if consecutive_above >= BARS_PERSISTENCE_REQUIRED and has_stage1_above:
            # Check for YELLOW: was previously RED before this BLUE run
            if self._was_opposite_trend(cci_14_history, zero_line, current_side="above"):
                return StrategicGateResult(
                    direction_allowed="NONE",
                    color=TrendState.YELLOW,
                    terminal="SKIP — color veto (YELLOW per P-W5)",
                    metadata={"reason": "transition_red_to_blue", "consecutive_above": consecutive_above},
                )
            return StrategicGateResult(
                direction_allowed="LONG",
                color=TrendState.BLUE,
                metadata={"consecutive_above": consecutive_above},
            )

        # RED: sustained below zero + Stage-1
        if consecutive_below >= BARS_PERSISTENCE_REQUIRED and has_stage1_below:
            if self._was_opposite_trend(cci_14_history, zero_line, current_side="below"):
                return StrategicGateResult(
                    direction_allowed="NONE",
                    color=TrendState.YELLOW,
                    terminal="SKIP — color veto (YELLOW per P-W5)",
                    metadata={"reason": "transition_blue_to_red", "consecutive_below": consecutive_below},
                )
            return StrategicGateResult(
                direction_allowed="SHORT",
                color=TrendState.RED,
                metadata={"consecutive_below": consecutive_below},
            )

        # Not enough persistence or Stage-1 not met
        return StrategicGateResult(
            direction_allowed="NONE",
            color=TrendState.GRAY,
            terminal="SKIP — color veto (GRAY)",
            metadata={"reason": "insufficient_persistence", "above": consecutive_above, "below": consecutive_below},
        )

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
