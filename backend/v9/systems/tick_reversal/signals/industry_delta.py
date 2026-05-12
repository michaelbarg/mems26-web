"""Industry Signal 3: Cumulative Delta Aligned.

Delta direction agrees with bar direction.
LONG bar + positive delta = aligned. SHORT bar + negative delta = aligned.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput


def calc_cumulative_delta_aligned(
    bar: BarInput,
    bars: List[BarInput],
) -> bool:
    """Check if cumulative delta direction matches bar direction."""
    delta = bar.delta
    if delta is None:
        # Approximate from ask_vol - bid_vol
        delta = bar.ask_vol - bar.bid_vol

    is_up = bar.c > bar.o

    if is_up:
        return delta > 0
    else:
        return delta < 0
