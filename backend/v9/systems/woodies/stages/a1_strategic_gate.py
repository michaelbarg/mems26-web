"""Stage A1 — Strategic Gate (PROMPT 2 · 2.2 stub).

Purpose: Determine direction allowed per CCI 14 vs Zero Line behavior over 6+ bars.
Reference: Decision Tree V1 § Section 4 · A1
Type: Woodies Core (independent decision)
Logic: PROMPT 3
"""

from dataclasses import dataclass
from typing import List


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
      YELLOW — sustained trend changing → stand aside
      INDETERMINATE — else → wait

    Terminal states: SKIP (color veto on GREY/YELLOW/INDETERMINATE)
    """

    def evaluate(
        self,
        cci_14_value: float,
        cci_14_history: List[float],
        zero_line: float = 0,
    ) -> A1Output:
        """Evaluate strategic gate. STUB: returns NONE/INDETERMINATE."""
        # STUB: real logic in PROMPT 3
        return A1Output(direction_allowed="NONE", color="INDETERMINATE")
