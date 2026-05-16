"""Stage B7 — Time Stop (PROMPT 3 · 3.5).

Purpose: Exit if no T1 hit within time threshold (no momentum).
Reference: Decision Tree V1 § Section 5 · B7
Type: Woodies Core
Priority Class: TIME_EXIT
"""

from dataclasses import dataclass
from typing import Optional

# Default time stop threshold
TIME_STOP_MINUTES = 60


@dataclass
class B7Output:
    """B7 stage output."""
    time_stop_hit: bool
    action: str  # "CLOSE_ALL" | "HOLD"
    elapsed_minutes: float


class B7TimeStop:
    """Stage B7 — Time Stop.

    If elapsed >= 60 minutes and T1 not hit → TIME_STOP.
    Terminal: CLOSE ALL — Time stop
    """

    priority_class = "TIME_EXIT"

    def evaluate(
        self,
        elapsed_minutes: float = 0.0,
        t1_hit: bool = False,
        entry_timestamp: Optional[str] = None,
        current_timestamp: Optional[str] = None,
    ) -> B7Output:
        """Evaluate time stop per Decision Tree V1 § B7."""
        if t1_hit:
            # T1 already hit → no time stop
            return B7Output(time_stop_hit=False, action="HOLD", elapsed_minutes=elapsed_minutes)

        if elapsed_minutes >= TIME_STOP_MINUTES:
            return B7Output(time_stop_hit=True, action="CLOSE_ALL", elapsed_minutes=elapsed_minutes)

        return B7Output(time_stop_hit=False, action="HOLD", elapsed_minutes=elapsed_minutes)
