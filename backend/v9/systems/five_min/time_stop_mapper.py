"""time_stop_mapper — maps Day Type to time_stop_minutes.

Per Constitution V3 §Layer 4 targets matrix.
Source: backend/v9/systems/day_type/targets_table.py (S1 provides).
"""
from __future__ import annotations

from typing import Optional

from backend.v9.systems.day_type.targets_table import get_targets


DEFAULT_TIME_STOP = 60  # fallback when Day Type unknown


def get_time_stop(day_type: Optional[str]) -> int:
    """Get time_stop_minutes for given Day Type.

    Returns time_stop from targets_table, or DEFAULT if unavailable.
    """
    if day_type is None:
        return DEFAULT_TIME_STOP

    targets = get_targets(day_type)
    if targets is None:
        return DEFAULT_TIME_STOP

    time_stop = targets.get("time_stop_minutes")
    if time_stop is None:
        return DEFAULT_TIME_STOP

    return int(time_stop)
