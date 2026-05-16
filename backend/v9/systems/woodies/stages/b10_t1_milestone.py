"""Stage B10 — T1 Milestone (PROMPT 2 · 2.3 stub).

Purpose: Handle T1 hit event.
Reference: Decision Tree V1 § Section 5 · B10
Type: Woodies Core
Priority Class: TARGET
Logic: PROMPT 3
"""

from dataclasses import dataclass


@dataclass
class B10Output:
    """B10 stage output."""
    t1_hit: bool
    action: str  # "CLOSE_C1" | "HOLD"


class B10T1Milestone:
    """Stage B10 — T1 Milestone.

    If T1 price reached:
      → close C1 (1 contract)
      → DO NOT MOVE STOP (D-002: T1 = stop-hunt zone)
      → mark t1_already_hit = true
    Action: Close C1 + NO BE move
    """

    priority_class = "TARGET"

    def evaluate(
        self,
        current_price: float,
        t1_price: float,
        direction: str,
        t1_already_hit: bool = False,
    ) -> B10Output:
        """Evaluate T1 milestone. STUB: returns no hit."""
        # STUB: real logic in PROMPT 3
        return B10Output(t1_hit=False, action="HOLD")
