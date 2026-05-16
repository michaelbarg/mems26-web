"""Stage B8 — Counter-Pattern Detection (PROMPT 2 · 2.3 stub).

Purpose: Detect counter-patterns that warn of reversal (tighten, not exit).
Reference: Decision Tree V1 § Section 5 · B8
Type: Woodies Core
Priority Class: TIGHTEN
Logic: PROMPT 3
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class B8Output:
    """B8 stage output."""
    counter_detected: bool
    action: str  # "TIGHTEN_STOP" | "HOLD"
    tighten_destination: Optional[str]  # target level description


class B8CounterPattern:
    """Stage B8 — Counter-Pattern Detection.

    Scans for HFE_against, TT_against, FAMIR_against.
    If detected → TIGHTEN_STOP with destination:
      pre-T1: stop → 50% of T1 distance
      post-T1: stop → entry
      post-T2: stop → T1 level
    Action: TIGHTEN STOP (no close)
    """

    priority_class = "TIGHTEN"

    def evaluate(
        self,
        cci_14_history: Optional[List[float]] = None,
        current_color: Optional[str] = None,
        direction: Optional[str] = None,
        t1_hit: bool = False,
        t2_hit: bool = False,
    ) -> B8Output:
        """Evaluate counter-pattern. STUB: returns no detection."""
        # STUB: real logic in PROMPT 3
        return B8Output(counter_detected=False, action="HOLD", tighten_destination=None)
