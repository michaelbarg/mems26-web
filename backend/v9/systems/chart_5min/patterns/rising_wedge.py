"""C4b. Rising Wedge — both lines rising, converging. Bearish."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import find_pivots, swing_highs, swing_lows, linear_regression_slope


def detect_rising_wedge(bars: List[Bar]) -> PatternResult:
    """Detect Rising Wedge in 15-30 bars."""
    if len(bars) < 12:
        return PatternResult()

    window = bars[-min(len(bars), 35):]
    pivots = find_pivots(window, lookback=2)
    highs = swing_highs(pivots)
    lows = swing_lows(pivots)

    if len(highs) < 2 or len(lows) < 2:
        return PatternResult()

    h_prices = [h.price for h in highs[-4:]]
    l_prices = [lo.price for lo in lows[-4:]]

    h_slope = linear_regression_slope(h_prices)
    l_slope = linear_regression_slope(l_prices)

    # Both slopes must be positive (rising)
    if h_slope <= 0 or l_slope <= 0:
        return PatternResult()

    # Lines converge: resistance rises slower than support
    if h_slope >= l_slope:
        return PatternResult()

    last = window[-1]
    pattern_height = max(h_prices) - min(l_prices)
    breakout = last.c < l_prices[-1]
    completion = 0.9 if breakout else 0.6

    entry = l_prices[-1]
    stop_price = h_prices[-1]
    t1 = entry - pattern_height * 0.382
    t2 = entry - pattern_height * 0.618
    t3 = entry - pattern_height

    return PatternResult(
        detected=True,
        pattern_id="rising_wedge",
        group="C",
        direction="SHORT",
        completion=completion,
        bar_count=len(window),
        method="Geometric",
        potential_r="5-8R",
        key_levels={
            "upper_trend": h_prices[-1],
            "lower_trend": l_prices[-1],
            "target": entry - pattern_height * 0.618,
            "stop": stop_price,
        },
        confidence=0.55 + 0.2 * completion,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
