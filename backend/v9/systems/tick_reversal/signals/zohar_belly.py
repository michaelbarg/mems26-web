"""Zohar Signal 1: Belly Comparison.

LONG: buyer belly volume > seller belly volume × belly_dominance_ratio.
SHORT: inverse.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput


def calc_belly_comparison(
    bar: BarInput,
    bars: List[BarInput],
    belly_dominance_ratio: float = 1.5,
) -> bool:
    """Compare buy-side vs sell-side belly volume."""
    ask = bar.ask_vol
    bid = bar.bid_vol

    if ask <= 0 and bid <= 0:
        return False

    if ask > 0 and bid > 0:
        ratio = max(ask / bid, bid / ask)
        return ratio >= belly_dominance_ratio

    # One side is zero → extreme dominance
    return True
