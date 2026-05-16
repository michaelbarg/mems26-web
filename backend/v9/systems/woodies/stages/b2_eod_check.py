"""Stage B2 — EOD Check (PROMPT 2 · 2.3 stub).

Purpose: Force flatten before market close.
Reference: Decision Tree V1 § Section 5 · B2
Type: Woodies Core
Priority Class: ABSOLUTE_EXIT
Logic: PROMPT 3
"""

from dataclasses import dataclass


@dataclass
class B2Output:
    """B2 stage output."""
    eod_force: bool
    action: str  # "CLOSE_ALL" | "HOLD"


class B2EodCheck:
    """Stage B2 — EOD Check.

    Force flatten if current_time_et >= 15:59.
    No overnight per D-002.
    Terminal: CLOSE ALL — EOD force
    """

    priority_class = "ABSOLUTE_EXIT"

    def evaluate(self, current_time_et: str) -> B2Output:
        """Evaluate EOD check. STUB: returns no force."""
        # STUB: real logic in PROMPT 3
        return B2Output(eod_force=False, action="HOLD")
