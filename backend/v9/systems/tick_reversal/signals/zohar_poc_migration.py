"""Zohar Signal 5: POC Migration (POC Jumping).

Zohar: POC must move with the trend. Stuck POC = "חבל מתוח" (bad).
Check if the POC of the current bar moved in the direction of the trend.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput


def calc_poc_jumping(
    bar: BarInput,
    bars: List[BarInput],
) -> bool:
    """Check if POC is migrating in trend direction across recent bars."""
    if len(bars) < 3:
        return False

    # Extract POC from footprint data or approximate from bar midpoint
    def get_poc(b: BarInput) -> float:
        if b.footprint and isinstance(b.footprint, dict):
            poc = b.footprint.get("poc_price")
            if poc is not None:
                return float(poc)
        # Fallback: volume-weighted midpoint approximation
        if b.ask_vol + b.bid_vol > 0:
            weight = b.ask_vol / (b.ask_vol + b.bid_vol)
            return b.l + (b.h - b.l) * weight
        return (b.h + b.l) / 2

    recent = bars[-3:]
    pocs = [get_poc(b) for b in recent]
    current_poc = get_poc(bar)

    is_up = bar.c > bar.o

    if is_up:
        # POC should be moving up
        return current_poc > pocs[-1] and pocs[-1] >= pocs[-2]
    else:
        # POC should be moving down
        return current_poc < pocs[-1] and pocs[-1] <= pocs[-2]
