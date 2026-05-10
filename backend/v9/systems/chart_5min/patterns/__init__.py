"""Pattern detectors — one per file, unified interface."""

from __future__ import annotations
from typing import List, Optional

from .reactive_buyer import detect_reactive_buyer
from .reactive_seller import detect_reactive_seller
from .initiative_buyer import detect_initiative_buyer
from .initiative_seller import detect_initiative_seller
from .bull_flag import detect_bull_flag
from .bear_flag import detect_bear_flag
from .bull_pennant import detect_bull_pennant
from .bear_pennant import detect_bear_pennant
from .double_bottom import detect_double_bottom
from .double_top import detect_double_top
from .ascending_triangle import detect_ascending_triangle
from .descending_triangle import detect_descending_triangle
from .head_shoulders import detect_head_shoulders
from .inverse_head_shoulders import detect_inverse_head_shoulders
from .symmetrical_triangle import detect_symmetrical_triangle
from .falling_wedge import detect_falling_wedge
from .rising_wedge import detect_rising_wedge
from .cup_handle import detect_cup_handle
from .inverse_cup_handle import detect_inverse_cup_handle

# Registry: pattern_id -> detector function
# Each detector takes List[Bar] and returns PatternResult
PATTERN_REGISTRY = {
    "reactive_buyer": detect_reactive_buyer,
    "reactive_seller": detect_reactive_seller,
    "initiative_buyer": detect_initiative_buyer,
    "initiative_seller": detect_initiative_seller,
    "bull_flag": detect_bull_flag,
    "bear_flag": detect_bear_flag,
    "bull_pennant": detect_bull_pennant,
    "bear_pennant": detect_bear_pennant,
    "double_bottom": detect_double_bottom,
    "double_top": detect_double_top,
    "ascending_triangle": detect_ascending_triangle,
    "descending_triangle": detect_descending_triangle,
    "head_shoulders": detect_head_shoulders,
    "inverse_head_shoulders": detect_inverse_head_shoulders,
    "symmetrical_triangle": detect_symmetrical_triangle,
    "falling_wedge": detect_falling_wedge,
    "rising_wedge": detect_rising_wedge,
    "cup_handle": detect_cup_handle,
    "inverse_cup_handle": detect_inverse_cup_handle,
}


def detect_all(bars, context: Optional[dict] = None):
    """Run all pattern detectors and return detected results.

    Args:
        bars: List[Bar] — bar data to scan.
        context: Optional dict with extra context (day_type, etc.).

    Returns:
        List[PatternResult] — only results where detected is True.
    """
    results = []
    for pattern_id, detector in PATTERN_REGISTRY.items():
        result = detector(bars)
        if result.detected:
            results.append(result)
    return results
