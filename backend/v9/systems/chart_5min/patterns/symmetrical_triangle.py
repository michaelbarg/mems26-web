"""C3. Symmetrical Triangle — converging trendlines, ambiguous direction."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import find_pivots, swing_highs, swing_lows, linear_regression_slope


def detect_symmetrical_triangle(bars: List[Bar]) -> PatternResult:
    """Detect Symmetrical Triangle in 10-25 bars.

    Criteria:
    1. Falling highs (downward slope)
    2. Rising lows (upward slope)
    3. Converging toward apex
    4. Direction determined by breakout
    """
    if len(bars) < 10:
        return PatternResult()

    window = bars[-min(len(bars), 30):]
    pivots = find_pivots(window, lookback=2)
    highs = swing_highs(pivots)
    lows = swing_lows(pivots)

    if len(highs) < 2 or len(lows) < 2:
        return PatternResult()

    h_prices = [h.price for h in highs[-4:]]
    l_prices = [lo.price for lo in lows[-4:]]

    h_slope = linear_regression_slope(h_prices)
    l_slope = linear_regression_slope(l_prices)

    # Both must converge: highs falling, lows rising
    if not (h_slope < 0 and l_slope > 0):
        return PatternResult()

    # Determine breakout direction from last bar
    last = window[-1]
    upper = h_prices[-1]
    lower = l_prices[-1]

    if upper <= lower:
        return PatternResult()

    mid = (upper + lower) / 2
    direction = "LONG" if last.c > mid else "SHORT"

    # Completion based on how close to apex
    initial_width = h_prices[0] - l_prices[0] if len(h_prices) > 0 and len(l_prices) > 0 else 1
    current_width = upper - lower
    if initial_width <= 0:
        return PatternResult()

    completion = min(1.0, 1.0 - current_width / initial_width)
    if completion < 0.3:
        return PatternResult()

    pattern_height = max(h_prices) - min(l_prices)
    target = (last.c + pattern_height) if direction == "LONG" else (last.c - pattern_height)
    stop_price = lower if direction == "LONG" else upper
    entry = upper if direction == "LONG" else lower

    if direction == "LONG":
        t1 = entry + pattern_height * 0.618
        t2 = entry + pattern_height
        t3 = entry + pattern_height * 1.618
    else:
        t1 = entry - pattern_height * 0.618
        t2 = entry - pattern_height
        t3 = entry - pattern_height * 1.618

    return PatternResult(
        detected=True,
        pattern_id="symmetrical_triangle",
        group="C",
        direction=direction,
        completion=completion,
        bar_count=len(window),
        method="Geometric",
        potential_r="4-7R",
        key_levels={
            "upper_trend": upper,
            "lower_trend": lower,
            "target": target,
            "stop": stop_price,
        },
        confidence=0.55 + 0.2 * completion,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
