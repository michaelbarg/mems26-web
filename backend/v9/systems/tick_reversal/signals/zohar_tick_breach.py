"""Zohar Signal 4: Tick Breach (4-5 max if near level).

Zohar: the bar doesn't overshoot too far. If near a key level,
the wick beyond the level is limited to 4-5 ticks.
Measured as: wick-to-body ratio is healthy (not excessive).
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput


def calc_tick_breach(
    bar: BarInput,
    bars: List[BarInput],
) -> bool:
    """Check if tick breach is within acceptable range (controlled wick)."""
    body = abs(bar.c - bar.o)
    bar_range = bar.h - bar.l

    if bar_range <= 0:
        return False

    # Upper wick and lower wick
    if bar.c >= bar.o:
        upper_wick = bar.h - bar.c
        lower_wick = bar.o - bar.l
    else:
        upper_wick = bar.h - bar.o
        lower_wick = bar.c - bar.l

    # The non-dominant wick should be small (4-5 ticks = controlled)
    # Each tick = 0.25 for MES
    tick = 0.25
    max_breach_ticks = 5

    is_up = bar.c > bar.o
    breach_wick = lower_wick if is_up else upper_wick

    return breach_wick <= max_breach_ticks * tick
