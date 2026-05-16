"""Stage B4 — POC Migration Query · Touch-Point (PROMPT 3 · 3.6).

Purpose: Check if POC has crossed against position (Suffering Side flip).
Reference: Decision Tree V1 § Section 5 · B4
Type: Touch-Point (advisory only · NEVER auto-exits)
Priority Class: ADVISORY_EXIT
Blocking: false
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class B4Output:
    """B4 stage output."""
    suffering_flip_warning: str  # "SUFFERING_FLIP" | "NONE"
    action: str  # "TIGHTEN" | "HOLD"


class B4PocMigrationQuery:
    """Stage B4 — POC Migration Query (Touch-Point).

    Queries /api/v9/tpo/current for POC location.
    Warns if POC crossed against position (but NEVER auto-exits — RULE 14).
    Default action when warning: TIGHTEN STOP TO ENTRY (NOT auto-exit).
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
        """Evaluate POC migration per Decision Tree V1 § B4.

        Advisory only — default action is TIGHTEN, NEVER auto-exit.
        """
        # Degraded mode
        if direction is None or current_price is None or poc_location is None:
            logger.debug("[B4] POC data unavailable — degraded mode (skip)")
            return B4Output(suffering_flip_warning="NONE", action="HOLD")

        # UFL/UFH bypass
        if ufl_ufh:
            ufl = ufl_ufh.get("ufl")
            ufh = ufl_ufh.get("ufh")
            if ufl is not None and current_price <= ufl:
                return B4Output(suffering_flip_warning="NONE", action="HOLD")
            if ufh is not None and current_price >= ufh:
                return B4Output(suffering_flip_warning="NONE", action="HOLD")

        # POC crossed against position
        if direction == "LONG" and current_price < poc_location:
            return B4Output(suffering_flip_warning="SUFFERING_FLIP", action="TIGHTEN")

        if direction == "SHORT" and current_price > poc_location:
            return B4Output(suffering_flip_warning="SUFFERING_FLIP", action="TIGHTEN")

        return B4Output(suffering_flip_warning="NONE", action="HOLD")
