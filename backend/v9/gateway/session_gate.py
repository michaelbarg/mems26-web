"""Session firing gate — B-13 D3 (2026-06-05).

Canonical trading session: 08:30–15:00 America/Chicago (CT).
No firing allowed outside this window in ANY mode (incl. SHADOW).

CLAUDE.md Rule 4: TZ ambiguity is forbidden. All constants carry explicit TZ.
The window is defined ONCE here; all consumers reference this module.

Note: 08:30–15:00 CT == 09:30–16:00 ET.  Data INGEST is allowed until 16:00 CT
(bars.py RTH gate extends to 17:00 ET = 16:00 CT), but FIRING stops at 15:00 CT.
"""

from __future__ import annotations

import logging
from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Canonical firing window — America/Chicago (CT)
FIRING_TZ = ZoneInfo("America/Chicago")
FIRING_OPEN = time(8, 30)   # 08:30 CT = 09:30 ET
FIRING_CLOSE = time(15, 0)  # 15:00 CT = 16:00 ET


def is_within_firing_window(now_utc: Optional[datetime] = None) -> bool:
    """Return True if current time is within the canonical firing window.

    Used by TradingGateway.route_setup to gate ALL modes including SHADOW.
    """
    if now_utc is None:
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
    ct_now = now_utc.astimezone(FIRING_TZ)
    ct_time = ct_now.time()
    # Weekend check: no firing Sat/Sun
    if ct_now.weekday() >= 5:
        return False
    return FIRING_OPEN <= ct_time < FIRING_CLOSE


def is_after_firing_close(now_utc: Optional[datetime] = None) -> bool:
    """Return True if we're past 15:00 CT on a weekday (for DAY_TYPE→OVERNIGHT)."""
    if now_utc is None:
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
    ct_now = now_utc.astimezone(FIRING_TZ)
    if ct_now.weekday() >= 5:
        return True
    return ct_now.time() >= FIRING_CLOSE
