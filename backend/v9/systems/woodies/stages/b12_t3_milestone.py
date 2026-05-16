"""Stage B12 — T3 Milestone (PROMPT 3 · 3.6).

Purpose: Handle T3 hit event (Initiative only).
Reference: Decision Tree V1 § Section 5 · B12
Type: Woodies Core
Priority Class: TARGET
"""

from dataclasses import dataclass


@dataclass
class B12Output:
    """B12 stage output."""
    t3_hit: bool
    action: str  # "CLOSE_C3" | "HOLD"


class B12T3Milestone:
    """Stage B12 — T3 Milestone.

    If T3 price reached (Initiative trades only):
      → close C3
      → Terminal: SUCCESS — Initiative Full Win
    """

    priority_class = "TARGET"

    def evaluate(
        self,
        current_price: float,
        t3_price: float,
        direction: str,
        t3_already_hit: bool = False,
    ) -> B12Output:
        """Evaluate T3 milestone per Decision Tree V1 § B12."""
        if t3_already_hit:
            return B12Output(t3_hit=False, action="HOLD")

        if direction == "LONG" and current_price >= t3_price:
            return B12Output(t3_hit=True, action="CLOSE_C3")

        if direction == "SHORT" and current_price <= t3_price:
            return B12Output(t3_hit=True, action="CLOSE_C3")

        return B12Output(t3_hit=False, action="HOLD")
