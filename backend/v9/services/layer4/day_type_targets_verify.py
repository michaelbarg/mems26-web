"""Day Type Targets Verify — V3 Layer 4 consistency check.

Cross-checks that an active trade's target scheme matches the current
Day Type classification. If day type changed after entry (re-eval),
flags the mismatch for the trader.

Reads W3-γ targets_table.get_targets().
"""
from typing import Dict, Optional


def evaluate(trade: Dict, current_day_type: str) -> Optional[Dict]:
    """Verify trade targets match current Day Type.

    Args:
        trade: {direction, day_type_at_entry, t1, t2, t3, time_stop_minutes}
        current_day_type: current classification from /api/v9/day_type/current

    Returns:
        WARN action if mismatch, None if consistent.
    """
    from backend.v9.systems.day_type.targets_table import get_targets

    entry_day_type = trade.get("day_type_at_entry")
    if not entry_day_type or not current_day_type:
        return None

    # Normalize for comparison
    entry_norm = entry_day_type.upper().replace(" ", "_")
    current_norm = current_day_type.upper().replace(" ", "_")

    if entry_norm == current_norm:
        return None  # consistent, no action

    # Day type changed — get both target schemes
    entry_targets = get_targets(entry_day_type)
    current_targets = get_targets(current_day_type)

    if entry_targets is None or current_targets is None:
        return None

    # Check if current scheme is more restrictive (shorter time stop, fewer targets)
    entry_time = entry_targets.get("time_stop_minutes")
    current_time = current_targets.get("time_stop_minutes")

    more_restrictive = False
    if current_time is not None and (entry_time is None or current_time < entry_time):
        more_restrictive = True

    return {
        "action": "WARN",
        "rule": "DAY_TYPE_TARGETS_MISMATCH",
        "entry_day_type": entry_day_type,
        "current_day_type": current_day_type,
        "entry_time_stop": entry_time,
        "current_time_stop": current_time,
        "more_restrictive": more_restrictive,
        "reasoning_notes": (
            f"Day Type changed: {entry_day_type} → {current_day_type}. "
            f"Time stop: {entry_time}min → {current_time}min. "
            f"{'TIGHTER scheme — consider adjusting targets.' if more_restrictive else 'Looser scheme — original targets still valid.'}"
        ),
    }
