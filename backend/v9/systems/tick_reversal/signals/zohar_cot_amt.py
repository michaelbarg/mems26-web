"""Zohar Signal 3: COT vs AMT.

Close of Trade (COT) vs Amount (AMT): the close price is on the
winning side relative to the bar's value area midpoint.
LONG: close above midpoint and close > open.
SHORT: close below midpoint and close < open.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput


def calc_cot_above_amt(
    bar: BarInput,
    bars: List[BarInput],
) -> bool:
    """Check if close-of-trade is above amount (value-area midpoint)."""
    midpoint = (bar.h + bar.l) / 2
    bar_range = bar.h - bar.l

    if bar_range <= 0:
        return False

    is_up = bar.c > bar.o

    if is_up:
        return bar.c > midpoint
    else:
        return bar.c < midpoint
