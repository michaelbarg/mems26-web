"""Q0 Dispatcher — Pre/Post-Lock branching per Tree V3.3.

Consumes Market Clock to determine current mode:
  PRE_LOCK (09:30-10:30 ET): First Hour Mode
  POST_LOCK (10:30+ ET): Day Type Mode

DST-aware via market_clock service (zoneinfo America/New_York).
"""
from __future__ import annotations

from datetime import time
from enum import Enum
from typing import Literal

from backend.v9.services.market_clock import now_et


class S2Mode(str, Enum):
    PRE_LOCK = "PRE_LOCK"       # First Hour: 09:30-10:30 ET
    POST_LOCK = "POST_LOCK"     # Day Type Mode: 10:30+ ET
    CLOSED = "CLOSED"           # Outside RTH


# IB lock time = 10:30 ET (60 minutes after RTH open)
IB_LOCK_TIME = time(10, 30)
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)


def get_current_mode(et_now=None) -> S2Mode:
    """Determine S2 operating mode based on current ET time.

    Args:
        et_now: override for testing (datetime with ET timezone)

    Returns:
        S2Mode enum value
    """
    if et_now is None:
        et_now = now_et()

    current_time = et_now.time()

    # Outside RTH
    if current_time < RTH_OPEN or current_time >= RTH_CLOSE:
        return S2Mode.CLOSED

    # Pre-lock (First Hour): 09:30-10:30
    if current_time < IB_LOCK_TIME:
        return S2Mode.PRE_LOCK

    # Post-lock (Day Type Mode): 10:30+
    return S2Mode.POST_LOCK


def is_transition_bar(et_now=None) -> bool:
    """Check if current bar is the 10:30 ET transition bar.

    Returns True if time is within 5 minutes of IB_LOCK_TIME.
    """
    if et_now is None:
        et_now = now_et()

    current_time = et_now.time()
    # Within 10:30-10:35 window
    return time(10, 30) <= current_time < time(10, 35)
