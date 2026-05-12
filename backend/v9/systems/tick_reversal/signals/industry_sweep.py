"""Industry Signal 5: Liquidity Sweep + Return.

Price sweeps beyond a prior high/low (takes liquidity / stops),
then returns inside. Classic stop-hunt pattern.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput


def calc_liquidity_sweep(
    bar: BarInput,
    bars: List[BarInput],
) -> bool:
    """Check for liquidity sweep: bar extends beyond prior extreme then closes back."""
    if len(bars) < 5:
        return False

    lookback = bars[-6:-1] if len(bars) >= 6 else bars[:-1]

    prior_high = max(b.h for b in lookback)
    prior_low = min(b.l for b in lookback)

    # Sweep high: wick above prior high, close back below
    if bar.h > prior_high and bar.c < prior_high:
        sweep_distance = bar.h - prior_high
        if sweep_distance > 0:
            return True

    # Sweep low: wick below prior low, close back above
    if bar.l < prior_low and bar.c > prior_low:
        sweep_distance = prior_low - bar.l
        if sweep_distance > 0:
            return True

    return False
