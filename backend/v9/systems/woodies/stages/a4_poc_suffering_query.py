"""Stage A4 — POC + Suffering Side Query · Touch-Point (PROMPT 2 · 2.2 stub).

Purpose: Get POC location + Suffering Side to classify entry type + warn on thesis risk.
Reference: Decision Tree V1 § Section 4 · A4
Type: Touch-Point (advisory only · NEVER vetoes)
Blocking: false
Logic: PROMPT 3
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class A4Output:
    """A4 stage output."""
    entry_classification_hint: str  # "REACTIVE" | "INITIATIVE" | "UNCLEAR"
    suffering_warning: str  # "SUFFERING_SIDE" | "NONE"
    bypass_active: str  # "UFL" | "UFH" | "NONE"


class A4PocSufferingQuery:
    """Stage A4 — POC + Suffering Side Query (Touch-Point).

    Queries /api/v9/tpo/current (POC) and /api/v9/veto/state (suffering_side).
    Classifies entry as REACTIVE vs INITIATIVE based on price vs IB/VA.
    Warns if on suffering side (but NEVER blocks).
    UFL/UFH zones bypass suffering check.

    Degraded mode: INITIATIVE default, skip suffering warning
    Terminal states: None (advisory only)
    """

    def evaluate(
        self,
        entry_direction: Optional[str] = None,
        current_price: Optional[float] = None,
        poc_location: Optional[float] = None,
        suffering_side: Optional[str] = None,
        ufl_ufh: Optional[dict] = None,
    ) -> A4Output:
        """Evaluate POC + suffering side. STUB: returns INITIATIVE/NONE."""
        # STUB: real logic in PROMPT 3
        return A4Output(
            entry_classification_hint="INITIATIVE",
            suffering_warning="NONE",
            bypass_active="NONE",
        )
