"""Stage B1 — Stop Check (PROMPT 3 · 3.4).

Purpose: Check if stop has been hit.
Reference: Decision Tree V1 § Section 5 · B1
Type: Woodies Core
Priority Class: ABSOLUTE_EXIT (highest)
"""

from dataclasses import dataclass


@dataclass
class B1Output:
    """B1 stage output."""
    stop_hit: bool
    action: str  # "CLOSE_ALL" | "HOLD"


class B1StopCheck:
    """Stage B1 — Stop Check.

    Checks if current price has hit the stop level.
    LONG: current_price <= stop_price → STOP_HIT
    SHORT: current_price >= stop_price → STOP_HIT
    Terminal: CLOSE ALL + cool-down 30min
    """

    priority_class = "ABSOLUTE_EXIT"

    def evaluate(
        self,
        current_price: float,
        stop_price: float,
        direction: str,
    ) -> B1Output:
        """Evaluate stop check per Decision Tree V1 § B1."""
        if direction == "LONG" and current_price <= stop_price:
            return B1Output(stop_hit=True, action="CLOSE_ALL")

        if direction == "SHORT" and current_price >= stop_price:
            return B1Output(stop_hit=True, action="CLOSE_ALL")

        return B1Output(stop_hit=False, action="HOLD")
