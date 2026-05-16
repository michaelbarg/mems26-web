"""Stage B1 — Stop Check (PROMPT 2 · 2.3 stub).

Purpose: Check if stop has been hit.
Reference: Decision Tree V1 § Section 5 · B1
Type: Woodies Core
Priority Class: ABSOLUTE_EXIT (highest)
Logic: PROMPT 3
"""

from dataclasses import dataclass
from typing import Optional


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
        """Evaluate stop check. STUB: returns no stop hit."""
        # STUB: real logic in PROMPT 3
        return B1Output(stop_hit=False, action="HOLD")
