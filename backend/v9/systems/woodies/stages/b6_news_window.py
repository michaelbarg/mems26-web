"""Stage B6 — News Window (PROMPT 2 · 2.3 stub).

Purpose: Force exit before high-impact news event.
Reference: Decision Tree V1 § Section 5 · B6
Type: Woodies Core
Priority Class: ABSOLUTE_EXIT
Logic: PROMPT 3
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class B6Output:
    """B6 stage output."""
    news_exit: bool
    action: str  # "CLOSE_ALL" | "REDUCE" | "HOLD"


class B6NewsWindow:
    """Stage B6 — News Window.

    Tier 1 news within ±5min → CLOSE ALL
    Tier 2 news within ±5min and size > 1 → reduce to 1 contract
    Terminal: CLOSE ALL — News emergency
    """

    priority_class = "ABSOLUTE_EXIT"

    def evaluate(
        self,
        news_calendar: Optional[dict] = None,
        current_time: Optional[str] = None,
        position_size: int = 1,
    ) -> B6Output:
        """Evaluate news window. STUB: returns no exit."""
        # STUB: real logic in PROMPT 3
        return B6Output(news_exit=False, action="HOLD")
