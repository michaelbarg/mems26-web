"""B4b. Descending Triangle — flat support + falling highs."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import find_pivots, swing_lows, swing_highs, prices_near, linear_regression_slope


def detect_descending_triangle(bars: List[Bar]) -> PatternResult:
    """Detect Descending Triangle in 10-20 bars."""
    if len(bars) < 10:
        return PatternResult()

    window = bars[-min(len(bars), 25):]
    pivots = find_pivots(window, lookback=2)
    highs = swing_highs(pivots)
    lows = swing_lows(pivots)

    if len(highs) < 2 or len(lows) < 2:
        return PatternResult()

    # Flat support
    l_prices = [lo.price for lo in lows[-3:]]
    support = min(l_prices)
    flat_bottom = all(prices_near(p, support, 0.10) for p in l_prices)
    if not flat_bottom:
        return PatternResult()

    # Falling highs
    h_prices = [h.price for h in highs[-3:]]
    h_slope = linear_regression_slope(h_prices)
    if h_slope >= 0:
        return PatternResult()

    bar_count = lows[-1].index - highs[0].index + 1
    last = window[-1]
    completion = min(1.0, (h_prices[-1] - last.c) / (h_prices[-1] - support)) \
        if h_prices[-1] > support else 0.0

    if completion < 0.5:
        return PatternResult()

    pattern_height = max(h_prices) - support
    entry = support
    stop_price = h_prices[-1]
    t1 = support - pattern_height * 0.618
    t2 = support - pattern_height
    t3 = support - pattern_height * 1.618

    return PatternResult(
        detected=True,
        pattern_id="descending_triangle",
        group="B",
        direction="SHORT",
        completion=completion,
        bar_count=max(bar_count, len(window)),
        method="Geometric",
        potential_r="4-7R",
        key_levels={
            "support": support,
            "highs_slope": h_slope,
            "target": support - pattern_height,
            "stop": stop_price,
        },
        confidence=0.6 + 0.15 * completion,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
