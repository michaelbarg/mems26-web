"""Stage B3 — Color Flip Check (PROMPT 3 · 3.5).

Purpose: Detect if Strategic Gate (color) flipped against position.
Reference: Decision Tree V1 § Section 5 · B3
Type: Woodies Core (Strategic Gate broken)
Priority Class: STRATEGIC_EXIT
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class B3Output:
    """B3 stage output."""
    flip_detected: bool
    action: str  # "CLOSE_ALL" | "TIGHTEN" | "HOLD"


class B3ColorFlip:
    """Stage B3 — Color Flip Check.

    Detects if color flipped against position:
    LONG+BLUE → RED = FLIP → CLOSE ALL
    SHORT+RED → BLUE = FLIP → CLOSE ALL
    YELLOW/GRAY for N bars = DEGRADATION (configurable: TIGHTEN or EXIT)
    Terminal: CLOSE ALL — Strategic Exit
    """

    priority_class = "STRATEGIC_EXIT"

    def evaluate(
        self,
        current_color: str,
        entry_color: str,
        direction: str,
        degradation_bars: int = 0,
        degradation_action: str = "TIGHTEN",
    ) -> B3Output:
        """Evaluate color flip per Decision Tree V1 § B3."""
        # Direct flip: BLUE→RED or RED→BLUE against position
        if direction == "LONG" and entry_color == "BLUE" and current_color == "RED":
            return B3Output(flip_detected=True, action="CLOSE_ALL")

        if direction == "SHORT" and entry_color == "RED" and current_color == "BLUE":
            return B3Output(flip_detected=True, action="CLOSE_ALL")

        # Degradation: YELLOW or GRAY (configurable response)
        if current_color in ("YELLOW", "GRAY"):
            action = degradation_action  # default TIGHTEN, configurable to EXIT
            if degradation_action == "EXIT":
                return B3Output(flip_detected=True, action="CLOSE_ALL")
            return B3Output(flip_detected=False, action="TIGHTEN")

        return B3Output(flip_detected=False, action="HOLD")
