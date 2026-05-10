"""B4a. Ascending Triangle — flat resistance + rising lows."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import find_pivots, swing_lows, swing_highs, prices_near, linear_regression_slope


def detect_ascending_triangle(bars: List[Bar]) -> PatternResult:
    """Detect Ascending Triangle in 10-20 bars.

    Criteria:
    1. Flat resistance line (swing highs at same level)
    2. Rising support line (swing lows ascending)
    3. At least 2 touches on each line
    """
    if len(bars) < 10:
        return PatternResult()

    window = bars[-min(len(bars), 25):]
    pivots = find_pivots(window, lookback=2)
    highs = swing_highs(pivots)
    lows = swing_lows(pivots)

    if len(highs) < 2 or len(lows) < 2:
        return PatternResult()

    # Flat resistance: highs should be near same level
    h_prices = [h.price for h in highs[-3:]]
    resistance = max(h_prices)
    flat_top = all(prices_near(p, resistance, 0.10) for p in h_prices)
    if not flat_top:
        return PatternResult()

    # Rising lows
    l_prices = [lo.price for lo in lows[-3:]]
    l_slope = linear_regression_slope(l_prices)
    if l_slope <= 0:
        return PatternResult()

    bar_count = highs[-1].index - lows[0].index + 1
    last = window[-1]
    completion = min(1.0, (last.c - l_prices[-1]) / (resistance - l_prices[-1])) \
        if resistance > l_prices[-1] else 0.0

    if completion < 0.5:
        return PatternResult()

    pattern_height = resistance - min(l_prices)
    entry = resistance
    stop_price = l_prices[-1]
    t1 = resistance + pattern_height * 0.618
    t2 = resistance + pattern_height
    t3 = resistance + pattern_height * 1.618

    return PatternResult(
        detected=True,
        pattern_id="ascending_triangle",
        group="B",
        direction="LONG",
        completion=completion,
        bar_count=max(bar_count, len(window)),
        method="Geometric",
        potential_r="4-7R",
        key_levels={
            "resistance": resistance,
            "support_slope": l_slope,
            "target": resistance + pattern_height,
            "stop": stop_price,
        },
        confidence=0.6 + 0.15 * completion,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
