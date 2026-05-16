"""Stage B11 — T2 Milestone (PROMPT 3 · 3.6).

Purpose: Handle T2 hit event.
Reference: Decision Tree V1 § Section 5 · B11
Type: Woodies Core
Priority Class: TARGET
"""

from dataclasses import dataclass


@dataclass
class B11Output:
    """B11 stage output."""
    t2_hit: bool
    action: str  # "CLOSE_ALL" | "CLOSE_C2" | "HOLD"
    be_moved: bool  # Smart BE activated (D-055)


class B11T2Milestone:
    """Stage B11 — T2 Milestone.

    If T2 price reached:
      REACTIVE → close ALL (no runner — mean reversion target)
      INITIATIVE → close C2 + Smart BE to entry (D-055) + activate C3 trail
    """

    priority_class = "TARGET"

    def evaluate(
        self,
        current_price: float,
        t2_price: float,
        direction: str,
        entry_classification: str = "INITIATIVE",
        t2_already_hit: bool = False,
    ) -> B11Output:
        """Evaluate T2 milestone per Decision Tree V1 § B11.

        REACTIVE: close ALL. INITIATIVE: close C2 + Smart BE (D-055).
        """
        if t2_already_hit:
            return B11Output(t2_hit=False, action="HOLD", be_moved=False)

        hit = False
        if direction == "LONG" and current_price >= t2_price:
            hit = True
        elif direction == "SHORT" and current_price <= t2_price:
            hit = True

        if hit:
            if entry_classification == "REACTIVE":
                return B11Output(t2_hit=True, action="CLOSE_ALL", be_moved=False)
            else:
                # INITIATIVE: close C2 + Smart BE to entry (D-055)
                return B11Output(t2_hit=True, action="CLOSE_C2", be_moved=True)

        return B11Output(t2_hit=False, action="HOLD", be_moved=False)
