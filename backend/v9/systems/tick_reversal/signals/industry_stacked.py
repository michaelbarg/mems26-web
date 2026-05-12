"""Industry Signal 2: Stacked Imbalance.

3+ consecutive price levels with imbalance in the same direction.
Strong directional conviction signal.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput


def calc_stacked_imbalance(
    bar: BarInput,
    bars: List[BarInput],
    imbalance_ratio: int = 250,
    stacked_count: int = 3,
) -> bool:
    """Check for 3+ consecutive levels with same-direction imbalance."""
    if not bar.footprint or not isinstance(bar.footprint, dict):
        # Fallback: check cluster data from bridge
        if bar.cluster and isinstance(bar.cluster, dict):
            stacked_buy = bar.cluster.get("stacked_buy", 0)
            stacked_sell = bar.cluster.get("stacked_sell", 0)
            return (stacked_buy or 0) >= stacked_count or (stacked_sell or 0) >= stacked_count
        return False

    levels = bar.footprint.get("levels", [])
    if not levels:
        return False

    # Walk through levels looking for consecutive imbalances
    buy_streak = 0
    sell_streak = 0
    max_buy = 0
    max_sell = 0

    for level in levels:
        if not isinstance(level, dict):
            continue
        bid = level.get("bid", 0)
        ask = level.get("ask", 0)

        if bid > 0 and ask > 0:
            ratio = ask / bid
            if ratio * 100 >= imbalance_ratio:
                buy_streak += 1
                sell_streak = 0
            elif (bid / ask) * 100 >= imbalance_ratio:
                sell_streak += 1
                buy_streak = 0
            else:
                max_buy = max(max_buy, buy_streak)
                max_sell = max(max_sell, sell_streak)
                buy_streak = 0
                sell_streak = 0
        else:
            max_buy = max(max_buy, buy_streak)
            max_sell = max(max_sell, sell_streak)
            buy_streak = 0
            sell_streak = 0

    max_buy = max(max_buy, buy_streak)
    max_sell = max(max_sell, sell_streak)

    return max_buy >= stacked_count or max_sell >= stacked_count
