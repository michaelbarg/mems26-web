"""time_stop_mapper — maps Day Type to Optional[int] time_stop_minutes.

Per Constitution V3 §Layer 4 targets matrix + EXIT_V6 (D-091).
Returns None when day_type's targets specify no time stop (e.g. Trend_Normal).
Returns None when day_type is unknown — caller MUST handle explicitly.
"""
from __future__ import annotations
from typing import Optional
from backend.v9.systems.day_type.targets_table import get_targets


def get_time_stop(day_type: Optional[str]) -> Optional[int]:
    """Get time_stop_minutes for given Day Type, or None.

    Returns:
      - int 1..180 when day_type has a numeric time_stop_minutes
      - None when day_type has no time stop (Trend_Normal) OR no_trade=True (Nontrend)
      - None when day_type is unknown or None (no silent default per pre-LIVE protocol)
    """
    if day_type is None:
        return None
    targets = get_targets(day_type)
    if targets is None:
        return None
    if targets.get("no_trade", False):
        return None
    time_stop = targets.get("time_stop_minutes")
    if time_stop is None:
        return None
    return int(time_stop)
