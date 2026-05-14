"""SWI Red → Tighten Stop — V3 Layer 4 don't-give-back rule.

When Sidewinder (S4 Woodies) turns red, reduce stop distance by 25%.
Reads SWI state from /api/v9/woodies/current.
"""
from typing import Dict, Optional


def evaluate(trade: Dict, swi: Dict) -> Optional[Dict]:
    """Evaluate SWI tighten rule.

    Args:
        trade: {direction, current_price, stop_price}
        swi: {value, color} from S4 Sidewinder

    Returns:
        Action dict with new_stop or None if no action.
    """
    color = swi.get("color", "").lower()
    if color != "red":
        return None

    direction = trade.get("direction")
    current_price = trade.get("current_price", 0)
    stop_price = trade.get("stop_price", 0)

    if not direction or not stop_price:
        return None

    distance = abs(current_price - stop_price)
    if distance <= 0:
        return None

    # Tighten by 25%
    reduction = distance * 0.25

    if direction == "LONG":
        new_stop = stop_price + reduction
    elif direction == "SHORT":
        new_stop = stop_price - reduction
    else:
        return None

    return {
        "action": "TIGHTEN_STOP",
        "rule": "SWI_RED",
        "new_stop": round(new_stop, 2),
        "old_stop": stop_price,
        "reduction_pct": 25,
        "swi_value": swi.get("value"),
        "reasoning_notes": (
            f"SWI red ({swi.get('value')}) → tighten stop 25%: "
            f"{stop_price:.2f} → {new_stop:.2f} (distance {distance:.2f} → {distance - reduction:.2f})"
        ),
    }
