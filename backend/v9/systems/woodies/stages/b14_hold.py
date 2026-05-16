"""Stage B14 — Hold (PROMPT 3 · 3.6).

Purpose: Default state when no other stage triggers an action.
Reference: Decision Tree V1 § Section 5 · B14
Type: Woodies Core
Priority Class: NO_ACTION (always last)
Logic: N/A — default no-action state
"""

from dataclasses import dataclass


@dataclass
class B14Output:
    """B14 stage output."""
    action: str  # always "HOLD"


class B14Hold:
    """Stage B14 — Hold (Default No-Action).

    Default state when no other stage triggers an action.
    Always returns HOLD — wait for next bar update.
    Always last in priority hierarchy.
    """

    priority_class = "NO_ACTION"

    def evaluate(self) -> B14Output:
        """Evaluate hold per Decision Tree V1 § B14. Always returns HOLD."""
        return B14Output(action="HOLD")
