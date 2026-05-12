"""Zohar Signal 2: 90% Volume Drop.

Zohar: volume of the losing side drops by 90% compared to recent bars.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput


def calc_volume_drop_90(
    bar: BarInput,
    bars: List[BarInput],
    volume_drop_pct: int = 90,
) -> bool:
    """Check if the losing side's volume dropped 90%+ vs recent average."""
    if len(bars) < 3:
        return False

    lookback = bars[-4:-1] if len(bars) >= 4 else bars[:-1]

    is_up = bar.c > bar.o
    current_losing = bar.bid_vol if is_up else bar.ask_vol

    # Average losing-side volume of recent bars
    losing_vols = []
    for b in lookback:
        b_up = b.c > b.o
        losing_vols.append(b.bid_vol if b_up else b.ask_vol)

    if not losing_vols:
        return False

    avg_losing = sum(losing_vols) / len(losing_vols)
    if avg_losing <= 0:
        return False

    drop_pct = ((avg_losing - current_losing) / avg_losing) * 100
    return drop_pct >= volume_drop_pct
