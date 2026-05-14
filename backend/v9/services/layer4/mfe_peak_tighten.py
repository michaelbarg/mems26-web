"""MFE Peak 80% T2 → Tighten — V3 Layer 4 don't-give-back rule.

When Maximum Favorable Excursion reaches 80% of T2 target distance,
tighten stop to lock in 50% of the MFE profit.
"""
from typing import Dict, Optional

# 🟡 default thresholds — to-calibrate-in-SHADOW
MFE_TRIGGER_PCT = 0.80  # trigger at 80% of T2 distance
LOCK_PCT = 0.50  # lock 50% of MFE as new stop


def evaluate(trade: Dict) -> Optional[Dict]:
    """Evaluate MFE peak tighten rule.

    Args:
        trade: {entry, stop, t2, current_price, mfe, direction}
            mfe = maximum favorable excursion price reached so far

    Returns:
        TIGHTEN_STOP action or None.
    """
    entry = trade.get("entry")
    stop = trade.get("stop")
    t2 = trade.get("t2")
    mfe = trade.get("mfe")
    direction = trade.get("direction")

    if any(v is None for v in [entry, stop, t2, mfe, direction]):
        return None

    # T2 distance from entry
    t2_distance = abs(t2 - entry)
    if t2_distance <= 0:
        return None

    # MFE distance from entry (directional)
    if direction == "LONG":
        mfe_distance = mfe - entry
    elif direction == "SHORT":
        mfe_distance = entry - mfe
    else:
        return None

    if mfe_distance <= 0:
        return None

    mfe_pct = mfe_distance / t2_distance

    if mfe_pct < MFE_TRIGGER_PCT:
        return None

    # Lock 50% of MFE profit as new stop
    lock_distance = mfe_distance * LOCK_PCT

    if direction == "LONG":
        new_stop = entry + lock_distance
    else:
        new_stop = entry - lock_distance

    # Only tighten (never loosen)
    if direction == "LONG" and new_stop <= stop:
        return None
    if direction == "SHORT" and new_stop >= stop:
        return None

    return {
        "action": "TIGHTEN_STOP",
        "rule": "MFE_PEAK",
        "new_stop": round(new_stop, 2),
        "old_stop": stop,
        "mfe": mfe,
        "mfe_pct_of_t2": round(mfe_pct * 100, 1),
        "lock_pct": int(LOCK_PCT * 100),
        "reasoning_notes": (
            f"MFE reached {mfe_pct * 100:.0f}% of T2 ({mfe:.2f}) "
            f"→ lock {int(LOCK_PCT * 100)}% of MFE: stop {stop:.2f} → {new_stop:.2f}"
        ),
    }
