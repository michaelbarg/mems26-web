"""Hardcoded high-impact economic event calendar for 2026.

Events: FOMC decisions, CPI releases, NFP (first Friday each month).
Each event has a +/-10 minute blocking window around its scheduled time.

Phase 3.5 will add a live news feed integration to replace/supplement
this hardcoded calendar. Until then, this is the authoritative source.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import pytz

ET = pytz.timezone("US/Eastern")

# (date_str, time_ET, event_type)
# FOMC: 8 meetings per year, decision at 14:00 ET
# CPI: released ~08:30 ET, usually 2nd or 3rd week
# NFP: first Friday of each month, 08:30 ET

_RAW_EVENTS: List[Tuple[str, str, str]] = [
    # --- FOMC 2026 (decision announcements, 14:00 ET) ---
    ("2026-01-28", "14:00", "FOMC"),
    ("2026-03-18", "14:00", "FOMC"),
    ("2026-05-06", "14:00", "FOMC"),
    ("2026-06-17", "14:00", "FOMC"),
    ("2026-07-29", "14:00", "FOMC"),
    ("2026-09-16", "14:00", "FOMC"),
    ("2026-11-04", "14:00", "FOMC"),
    ("2026-12-16", "14:00", "FOMC"),
    # --- CPI 2026 (08:30 ET releases) ---
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
    # --- NFP 2026 (first Friday, 08:30 ET) ---
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


def _parse_event(date_str: str, time_str: str) -> datetime:
    """Parse date + time string into timezone-aware ET datetime."""
    dt_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return ET.localize(dt_naive)


def get_all_events() -> List[Tuple[datetime, str]]:
    """Return all events as (datetime_ET, event_type) pairs."""
    return [(_parse_event(d, t), etype) for d, t, etype in _RAW_EVENTS]


def is_in_news_window(now_et: datetime) -> Tuple[bool, Optional[str]]:
    """Check if current time falls within +/-10 min of any high-impact event.

    Args:
        now_et: Current time, must be timezone-aware in ET.

    Returns:
        (blocked, event_description) — blocked=True if within window,
        with a description like "FOMC +/-10min (2026-05-06 14:00 ET)".
    """
    window = timedelta(minutes=NEWS_BLOCK_WINDOW_MINUTES)
    for event_dt, event_type in get_all_events():
        if abs(now_et - event_dt) <= window:
            desc = f"{event_type} +/-{NEWS_BLOCK_WINDOW_MINUTES}min ({event_dt.strftime('%Y-%m-%d %H:%M')} ET)"
            return True, desc
    return False, None
