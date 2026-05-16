"""Direction Change Detector — TCCI crosses CCI14 per V3 Part 5 #16.

Detects directional flip when TCCI (6-period CCI) crosses the CCI14 line.
Used by Layer 4 "don't give back" rules for exit triggers.

Per AP-SY02: every detection includes reasoning_notes.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger("mems26.woodies.direction_change")


def detect(history: List[Dict]) -> Optional[Dict]:
    """Detect TCCI crossing CCI14 in the last 2 bars.

    Args:
        history: list of dicts with cci_14 and tcci (cci_6_tcci) fields.
                 Most recent bar last.

    Returns:
        Detection event dict or None if no cross detected.
    """
    if len(history) < 2:
        return None

    prev = history[-2]
    curr = history[-1]

    prev_cci = prev.get("cci_14")
    prev_tcci = prev.get("tcci") or prev.get("cci_6_tcci")
    curr_cci = curr.get("cci_14")
    curr_tcci = curr.get("tcci") or curr.get("cci_6_tcci")

    if any(v is None for v in [prev_cci, prev_tcci, curr_cci, curr_tcci]):
        return None  # explicit None — no fallback per §6.7

    # Cross detection
    prev_above = prev_tcci > prev_cci
    curr_above = curr_tcci > curr_cci

    if prev_above == curr_above:
        return None  # no cross

    # Determine direction of the cross
    if curr_above:
        direction = "BULLISH"
        notes = f"TCCI crossed ABOVE CCI14: TCCI {curr_tcci:.1f} > CCI14 {curr_cci:.1f} (was {prev_tcci:.1f} < {prev_cci:.1f})"
    else:
        direction = "BEARISH"
        notes = f"TCCI crossed BELOW CCI14: TCCI {curr_tcci:.1f} < CCI14 {curr_cci:.1f} (was {prev_tcci:.1f} > {prev_cci:.1f})"

    return {
        "type": "DIRECTION_CHANGE",
        "direction": direction,
        "cci_14": curr_cci,
        "tcci": curr_tcci,
        "prev_cci_14": prev_cci,
        "prev_tcci": prev_tcci,
        "reasoning_notes": notes,
    }


def detect_from_buffer(bar_buffer: List) -> Optional[Dict]:
    """Convenience: detect from WoodiesBar buffer (last 2 bars)."""
    if len(bar_buffer) < 2:
        return None
    history = [
        {"cci_14": _read_bar_value(b, "cci_14"),
         "tcci": _read_bar_value(b, "cci_6_tcci")}
        for b in bar_buffer[-2:]
    ]
    return detect(history)


def _read_bar_value(bar, field: str):
    if hasattr(bar, field):
        return getattr(bar, field)
    if isinstance(bar, dict):
        return bar.get(field)
    return None
