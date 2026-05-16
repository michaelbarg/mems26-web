"""Stage B10 — T1 Milestone (PROMPT 3 · 3.6).

Purpose: Handle T1 hit event.
Reference: Decision Tree V1 § Section 5 · B10
Type: Woodies Core
Priority Class: TARGET
"""

from dataclasses import dataclass


@dataclass
class B10Output:
    """B10 stage output."""
    t1_hit: bool
    action: str  # "CLOSE_C1" | "HOLD"
    be_moved: bool  # D-002: NEVER move BE on T1


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
        """Evaluate T1 milestone per Decision Tree V1 § B10.

        D-002: DO NOT move stop to BE on T1 (stop-hunt zone).
        """
        if t1_already_hit:
            return B10Output(t1_hit=False, action="HOLD", be_moved=False)

        hit = False
        if direction == "LONG" and current_price >= t1_price:
            hit = True
        elif direction == "SHORT" and current_price <= t1_price:
            hit = True

        if hit:
            # D-002: explicitly NO BE move on T1
            return B10Output(t1_hit=True, action="CLOSE_C1", be_moved=False)

        return B10Output(t1_hit=False, action="HOLD", be_moved=False)
