"""Stage B13 — Trail Check (PROMPT 3 · 3.5).

Purpose: Vegas trail logic for C3 runner (post-T2 Initiative).
Reference: Decision Tree V1 § Section 5 · B13
Type: Woodies Core
Priority Class: TRAIL
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class B13Output:
    """B13 stage output."""
    trail_exit: bool
    action: str  # "CLOSE_C3" | "HOLD"


class B13TrailCheck:
    """Stage B13 — Trail Check.

    Post-T2 Initiative: trail C3 using EMA-169 (Vegas).
    LONG: price crosses below EMA-169 → close C3
    SHORT: price crosses above EMA-169 → close C3
    Terminal: Trail Exit

    Uses EMACalculator(169) from helpers/ema_calculator.py.
    """

    priority_class = "TRAIL"

    def evaluate(
        self,
        vegas_ema_169: Optional[float] = None,
        current_price: Optional[float] = None,
        direction: Optional[str] = None,
        t2_already_hit: bool = False,
        trail_mode_active: bool = False,
    ) -> B13Output:
        """Evaluate trail check per Decision Tree V1 § B13."""
        # Only active post-T2 in trail mode
        if not t2_already_hit or not trail_mode_active:
            return B13Output(trail_exit=False, action="HOLD")

        if vegas_ema_169 is None or current_price is None or direction is None:
            return B13Output(trail_exit=False, action="HOLD")

        # LONG: price crosses below EMA-169
        if direction == "LONG" and current_price < vegas_ema_169:
            return B13Output(trail_exit=True, action="CLOSE_C3")

        # SHORT: price crosses above EMA-169
        if direction == "SHORT" and current_price > vegas_ema_169:
            return B13Output(trail_exit=True, action="CLOSE_C3")

        return B13Output(trail_exit=False, action="HOLD")
