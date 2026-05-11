"""NewsGuard — blocks trading around high-impact economic news events.

Reuses the hardcoded 2026 FOMC/CPI/NFP calendar from
backend/v9/services/risk_validator/news_calendar.py.

Provides a simple is_news_blocked(current_time) interface for the bridge
and trading systems to check before executing trades.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

import pytz

ET = pytz.timezone("US/Eastern")

# Reuse the same event data from risk_validator/news_calendar.py
# Duplicated here to keep bridge self-contained (no backend dependency).
_RAW_EVENTS = [
    # FOMC 2026 (14:00 ET)
    ("2026-01-28", "14:00", "FOMC"),
    ("2026-03-18", "14:00", "FOMC"),
    ("2026-05-06", "14:00", "FOMC"),
    ("2026-06-17", "14:00", "FOMC"),
    ("2026-07-29", "14:00", "FOMC"),
    ("2026-09-16", "14:00", "FOMC"),
    ("2026-11-04", "14:00", "FOMC"),
    ("2026-12-16", "14:00", "FOMC"),
    # CPI 2026 (08:30 ET)
    ("2026-01-14", "08:30", "CPI"),
    ("2026-02-12", "08:30", "CPI"),
    ("2026-03-11", "08:30", "CPI"),
    ("2026-04-14", "08:30", "CPI"),
    ("2026-05-12", "08:30", "CPI"),
    ("2026-06-10", "08:30", "CPI"),
    ("2026-07-14", "08:30", "CPI"),
    ("2026-08-12", "08:30", "CPI"),
    ("2026-09-15", "08:30", "CPI"),
    ("2026-10-13", "08:30", "CPI"),
    ("2026-11-12", "08:30", "CPI"),
    ("2026-12-10", "08:30", "CPI"),
    # NFP 2026 (first Friday, 08:30 ET)
    ("2026-01-02", "08:30", "NFP"),
    ("2026-02-06", "08:30", "NFP"),
    ("2026-03-06", "08:30", "NFP"),
    ("2026-04-03", "08:30", "NFP"),
    ("2026-05-01", "08:30", "NFP"),
    ("2026-06-05", "08:30", "NFP"),
    ("2026-07-02", "08:30", "NFP"),
    ("2026-08-07", "08:30", "NFP"),
    ("2026-09-04", "08:30", "NFP"),
    ("2026-10-02", "08:30", "NFP"),
    ("2026-11-06", "08:30", "NFP"),
    ("2026-12-04", "08:30", "NFP"),
]

NEWS_BLOCK_WINDOW_MINUTES = 10

# Pre-parse all events at import time for fast lookup
_PARSED_EVENTS = []
for _d, _t, _etype in _RAW_EVENTS:
    _dt = ET.localize(datetime.strptime(f"{_d} {_t}", "%Y-%m-%d %H:%M"))
    _PARSED_EVENTS.append((_dt, _etype))


class NewsGuard:
    """Checks whether trading should be blocked due to nearby news events.

    Uses a +/-10 minute window around each high-impact event (FOMC, CPI, NFP).
    """

    def __init__(self, block_window_minutes: int = NEWS_BLOCK_WINDOW_MINUTES):
        self.block_window = timedelta(minutes=block_window_minutes)
        self.events = _PARSED_EVENTS

    def is_news_blocked(self, current_time: Optional[datetime] = None) -> bool:
        """Check if trading is blocked due to nearby news event.

        Args:
            current_time: Timezone-aware datetime. Uses current ET time if None.

        Returns:
            True if within the blocking window of any event.
        """
        blocked, _ = self.check(current_time)
        return blocked

    def check(self, current_time: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
        """Check for news block with description.

        Args:
            current_time: Timezone-aware datetime. Uses current ET time if None.

        Returns:
            (blocked, description) — description is like "FOMC +/-10min (2026-05-06 14:00 ET)".
        """
        if current_time is None:
            current_time = datetime.now(ET)
        elif current_time.tzinfo is None:
            current_time = ET.localize(current_time)
        else:
            current_time = current_time.astimezone(ET)

        for event_dt, event_type in self.events:
            if abs(current_time - event_dt) <= self.block_window:
                desc = (f"{event_type} +/-{self.block_window.total_seconds() / 60:.0f}min "
                        f"({event_dt.strftime('%Y-%m-%d %H:%M')} ET)")
                return True, desc

        return False, None

    def next_event(self, current_time: Optional[datetime] = None) -> Optional[Tuple[datetime, str]]:
        """Return the next upcoming news event.

        Args:
            current_time: Timezone-aware datetime. Uses current ET time if None.

        Returns:
            (event_datetime, event_type) or None if no future events.
        """
        if current_time is None:
            current_time = datetime.now(ET)
        elif current_time.tzinfo is None:
            current_time = ET.localize(current_time)

        future = [(dt, etype) for dt, etype in self.events if dt > current_time]
        if not future:
            return None
        return min(future, key=lambda x: x[0])
