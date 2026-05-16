"""Stage B2 — EOD Check (PROMPT 3 · 3.4).

Purpose: Force flatten before market close.
Reference: Decision Tree V1 § Section 5 · B2
Type: Woodies Core
Priority Class: ABSOLUTE_EXIT
"""

from dataclasses import dataclass
from datetime import time

# EOD force time per Decision Tree V1 (D-002: no overnight)
EOD_FORCE_TIME = time(15, 59)


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
        """Evaluate EOD check per Decision Tree V1 § B2.

        Args:
            current_time_et: Time string in "HH:MM" format (ET).
        """
        try:
            parts = current_time_et.split(":")
            hour, minute = int(parts[0]), int(parts[1])
            current = time(hour, minute)
        except (ValueError, IndexError):
            # Can't parse time → don't force (safe default)
            return B2Output(eod_force=False, action="HOLD")

        if current >= EOD_FORCE_TIME:
            return B2Output(eod_force=True, action="CLOSE_ALL")

        return B2Output(eod_force=False, action="HOLD")
