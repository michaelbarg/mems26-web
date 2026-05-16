"""Stage B3 — Color Flip Check (PROMPT 2 · 2.3 stub).

Purpose: Detect if Strategic Gate (color) flipped against position.
Reference: Decision Tree V1 § Section 5 · B3
Type: Woodies Core (Strategic Gate broken)
Priority Class: STRATEGIC_EXIT
Logic: PROMPT 3
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
    YELLOW/GREY for N bars = DEGRADATION (configurable: TIGHTEN or EXIT)
    Terminal: CLOSE ALL — Strategic Exit
    """

    priority_class = "STRATEGIC_EXIT"

    def evaluate(
        self,
        current_color: str,
        entry_color: str,
        direction: str,
    ) -> B3Output:
        """Evaluate color flip. STUB: returns no flip."""
        # STUB: real logic in PROMPT 3
        return B3Output(flip_detected=False, action="HOLD")
