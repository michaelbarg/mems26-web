"""Industry Signal 1: Imbalance 250%+.

Bid or Ask volume dominates by 250%+ at a price level.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput


def calc_imbalance_250(
    bar: BarInput,
    bars: List[BarInput],
    imbalance_ratio: int = 250,
) -> bool:
    """Check if any footprint level has 250%+ imbalance."""
    # Check from footprint data
    if bar.footprint and isinstance(bar.footprint, dict):
        levels = bar.footprint.get("levels", [])
        for level in levels:
            if isinstance(level, dict):
                bid = level.get("bid", 0)
                ask = level.get("ask", 0)
                if bid > 0 and ask > 0:
                    ratio_pct = max(ask / bid, bid / ask) * 100
                    if ratio_pct >= imbalance_ratio:
                        return True

    # Fallback: bar-level bid/ask ratio
    if bar.ask_vol > 0 and bar.bid_vol > 0:
        ratio_pct = max(bar.ask_vol / bar.bid_vol, bar.bid_vol / bar.ask_vol) * 100
        return ratio_pct >= imbalance_ratio

    return False
