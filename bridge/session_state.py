"""SessionState — tracks trading session state (ET-aware for US futures).

Detects pre-market, RTH (Regular Trading Hours), and post-market periods
for MES/ES futures on CME.

CME Equity Index Futures Schedule (ET):
  Pre-market:  18:00 (prev day) - 09:30
  RTH:         09:30 - 16:00
  Post-market: 16:00 - 17:00
  Closed:      17:00 - 18:00 (daily maintenance), weekends, holidays
"""

from dataclasses import dataclass
from datetime import datetime, time as dtime
from enum import Enum
from typing import Optional

import pytz

ET = pytz.timezone("US/Eastern")


class SessionPhase(str, Enum):
    """Trading session phase."""
    PRE_MARKET = "pre_market"
    RTH = "rth"
    POST_MARKET = "post_market"
    CLOSED = "closed"


# RTH boundaries
RTH_OPEN = dtime(9, 30)
RTH_CLOSE = dtime(16, 0)
# Post-market
POST_CLOSE = dtime(17, 0)
# Pre-market starts at 18:00 previous day (overnight session)
OVERNIGHT_OPEN = dtime(18, 0)
# Daily maintenance window
MAINTENANCE_START = dtime(17, 0)
MAINTENANCE_END = dtime(18, 0)

# US market holidays 2026 (CME equity futures closed)
_HOLIDAYS_2026 = {
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # MLK Day
    "2026-02-16",  # Presidents' Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-07-03",  # Independence Day (observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Christmas
}


@dataclass
class SessionState:
    """Current trading session state."""
    phase: SessionPhase
    is_trading_hours: bool
    session_start: Optional[datetime] = None
    session_end: Optional[datetime] = None
    next_rth_open: Optional[datetime] = None


def _is_holiday(dt_et: datetime) -> bool:
    """Check if date is a US market holiday."""
    return dt_et.strftime("%Y-%m-%d") in _HOLIDAYS_2026


def _is_weekend(dt_et: datetime) -> bool:
    """Check if date is Saturday or Sunday."""
    return dt_et.weekday() >= 5


def get_session_state(now: Optional[datetime] = None) -> SessionState:
    """Determine the current trading session state.

    Args:
        now: Current datetime (timezone-aware). Uses current ET time if None.

    Returns:
        SessionState with phase, trading hours flag, and session boundaries.
    """
    if now is None:
        now = datetime.now(ET)
    elif now.tzinfo is None:
        now = ET.localize(now)
    else:
        now = now.astimezone(ET)

    current_time = now.time()
    today_date = now.date()

    # Weekend check (Sunday before 18:00 is still closed)
    if _is_weekend(now):
        # Sunday after 18:00 ET = pre-market opens
        if now.weekday() == 6 and current_time >= OVERNIGHT_OPEN:
            return SessionState(
                phase=SessionPhase.PRE_MARKET,
                is_trading_hours=True,
                session_start=now.replace(hour=18, minute=0, second=0, microsecond=0),
            )
        return SessionState(phase=SessionPhase.CLOSED, is_trading_hours=False)

    # Holiday check
    if _is_holiday(now):
        return SessionState(phase=SessionPhase.CLOSED, is_trading_hours=False)

    # Maintenance window: 17:00 - 18:00 ET
    if MAINTENANCE_START <= current_time < MAINTENANCE_END:
        return SessionState(phase=SessionPhase.CLOSED, is_trading_hours=False)

    # RTH: 09:30 - 16:00 ET
    if RTH_OPEN <= current_time < RTH_CLOSE:
        session_start = now.replace(hour=9, minute=30, second=0, microsecond=0)
        session_end = now.replace(hour=16, minute=0, second=0, microsecond=0)
        return SessionState(
            phase=SessionPhase.RTH,
            is_trading_hours=True,
            session_start=session_start,
            session_end=session_end,
        )

    # Post-market: 16:00 - 17:00 ET
    if RTH_CLOSE <= current_time < POST_CLOSE:
        return SessionState(
            phase=SessionPhase.POST_MARKET,
            is_trading_hours=True,
            session_start=now.replace(hour=16, minute=0, second=0, microsecond=0),
            session_end=now.replace(hour=17, minute=0, second=0, microsecond=0),
        )

    # Pre-market / overnight: 18:00 (prev day) - 09:30
    if current_time >= OVERNIGHT_OPEN or current_time < RTH_OPEN:
        return SessionState(
            phase=SessionPhase.PRE_MARKET,
            is_trading_hours=True,
        )

    # Should not reach here, but default to closed
    return SessionState(phase=SessionPhase.CLOSED, is_trading_hours=False)
