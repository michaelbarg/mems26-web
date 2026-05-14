"""TCCI Cross CCI14 → Exit — V3 Layer 4 don't-give-back rule.

When Direction Change is detected (TCCI crosses CCI14 against trade direction),
exit the trade. Uses W3-β direction_change_detector output.
"""
from typing import Dict, Optional


def evaluate(trade: Dict, direction_change_event: Optional[Dict]) -> Optional[Dict]:
    """Evaluate TCCI cross exit rule.

    Args:
        trade: {direction} — current trade direction
        direction_change_event: output from W3-β direction_change_detector.detect()
            {type: "DIRECTION_CHANGE", direction: "BULLISH"|"BEARISH", reasoning_notes: ...}

    Returns:
        EXIT action dict or None.
    """
    if direction_change_event is None:
        return None

    if direction_change_event.get("type") != "DIRECTION_CHANGE":
        return None

    trade_direction = trade.get("direction")
    change_direction = direction_change_event.get("direction")

    if not trade_direction or not change_direction:
        return None

    # BULLISH cross against SHORT trade → exit
    # BEARISH cross against LONG trade → exit
    should_exit = (
        (trade_direction == "LONG" and change_direction == "BEARISH") or
        (trade_direction == "SHORT" and change_direction == "BULLISH")
    )

    if not should_exit:
        return None

    return {
        "action": "EXIT",
        "rule": "TCCI_CROSS",
        "trade_direction": trade_direction,
        "change_direction": change_direction,
        "reasoning_notes": (
            f"Direction Change {change_direction} against {trade_direction} trade → EXIT. "
            f"{direction_change_event.get('reasoning_notes', '')}"
        ),
    }
