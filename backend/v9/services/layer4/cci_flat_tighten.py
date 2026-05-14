"""CCI Flat 3+ bars → Tighten Stop — V3 Layer 4 don't-give-back rule.

When CCI14 remains flat (within ±10 band) for 3+ consecutive bars,
momentum is stalling — tighten stop to protect gains.
"""
from typing import Dict, List, Optional

# 🟡 default — to-calibrate-in-SHADOW
CCI_FLAT_THRESHOLD = 10  # max absolute change between bars to count as "flat"
CCI_FLAT_BARS_REQUIRED = 3
TIGHTEN_PCT = 20  # reduce stop distance by 20%


def evaluate(trade: Dict, cci_history: List[float]) -> Optional[Dict]:
    """Evaluate CCI flat tighten rule.

    Args:
        trade: {direction, current_price, stop_price}
        cci_history: list of CCI14 values, most recent last.

    Returns:
        Action dict or None.
    """
    if len(cci_history) < CCI_FLAT_BARS_REQUIRED:
        return None

    recent = cci_history[-CCI_FLAT_BARS_REQUIRED:]

    # Check if all consecutive changes are within threshold
    flat = True
    for i in range(1, len(recent)):
        if abs(recent[i] - recent[i - 1]) > CCI_FLAT_THRESHOLD:
            flat = False
            break

    if not flat:
        return None

    direction = trade.get("direction")
    current_price = trade.get("current_price", 0)
    stop_price = trade.get("stop_price", 0)

    if not direction or not stop_price:
        return None

    distance = abs(current_price - stop_price)
    if distance <= 0:
        return None

    reduction = distance * (TIGHTEN_PCT / 100)

    if direction == "LONG":
        new_stop = stop_price + reduction
    elif direction == "SHORT":
        new_stop = stop_price - reduction
    else:
        return None

    return {
        "action": "TIGHTEN_STOP",
        "rule": "CCI_FLAT",
        "new_stop": round(new_stop, 2),
        "old_stop": stop_price,
        "flat_bars": CCI_FLAT_BARS_REQUIRED,
        "cci_values": recent,
        "reasoning_notes": (
            f"CCI14 flat {CCI_FLAT_BARS_REQUIRED} bars (range {min(recent):.1f}–{max(recent):.1f}) "
            f"→ tighten stop {TIGHTEN_PCT}%: {stop_price:.2f} → {new_stop:.2f}"
        ),
    }
