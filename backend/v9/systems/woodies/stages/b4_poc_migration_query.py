"""Stage B4 — POC Migration Query · Touch-Point (PROMPT 2 · 2.3 stub).

Purpose: Check if POC has crossed against position (Suffering Side flip).
Reference: Decision Tree V1 § Section 5 · B4
Type: Touch-Point (advisory only · NEVER auto-exits)
Priority Class: ADVISORY_EXIT
Blocking: false
Logic: PROMPT 3
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class B4Output:
    """B4 stage output."""
    suffering_flip_warning: str  # "SUFFERING_FLIP" | "NONE"
    action: str  # "TIGHTEN" | "HOLD"


class B4PocMigrationQuery:
    """Stage B4 — POC Migration Query (Touch-Point).

    Queries /api/v9/tpo/current for POC location.
    Warns if POC crossed against position (but NEVER auto-exits).
    Default action: tighten stop to entry.
    UFL/UFH zones bypass.

    Degraded mode: skip entirely if M-S unavailable
    """

    priority_class = "ADVISORY_EXIT"

    def evaluate(
        self,
        direction: Optional[str] = None,
        current_price: Optional[float] = None,
        poc_location: Optional[float] = None,
        ufl_ufh: Optional[dict] = None,
    ) -> B4Output:
        """Evaluate POC migration. STUB: returns NONE/HOLD."""
        # STUB: real logic in PROMPT 3
        return B4Output(suffering_flip_warning="NONE", action="HOLD")
