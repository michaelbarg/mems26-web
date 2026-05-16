"""Stage B6 — News Window (PROMPT 3 · 3.4).

Purpose: Force exit before high-impact news event.
Reference: Decision Tree V1 § Section 5 · B6
Type: Woodies Core
Priority Class: ABSOLUTE_EXIT
"""

from dataclasses import dataclass
from typing import Optional

# News window buffer (minutes)
NEWS_WINDOW_MINUTES = 5


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
        """Evaluate news window per Decision Tree V1 § B6."""
        if not news_calendar:
            return B6Output(news_exit=False, action="HOLD")

        # Check Tier 1 news
        minutes_to_tier1 = news_calendar.get("minutes_to_next_tier1", 999)
        if abs(minutes_to_tier1) <= NEWS_WINDOW_MINUTES:
            return B6Output(news_exit=True, action="CLOSE_ALL")

        # Check Tier 2 news
        minutes_to_tier2 = news_calendar.get("minutes_to_next_tier2", 999)
        if abs(minutes_to_tier2) <= NEWS_WINDOW_MINUTES and position_size > 1:
            return B6Output(news_exit=False, action="REDUCE")

        return B6Output(news_exit=False, action="HOLD")
