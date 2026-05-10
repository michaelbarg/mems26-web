"""B1b. Double Top — mirror of Double Bottom."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import find_pivots, swing_lows, swing_highs, prices_near


def detect_double_top(bars: List[Bar]) -> PatternResult:
    """Detect Double Top in 8-15 bars."""
    if len(bars) < 8:
        return PatternResult()

    window = bars[-min(len(bars), 20):]
    lookback = 2 if len(window) >= 12 else 1
    pivots = find_pivots(window, lookback=lookback)
    lows = swing_lows(pivots)
    highs = swing_highs(pivots)

    if len(highs) < 2 or len(lows) < 1:
        return PatternResult()

    for i in range(len(highs) - 1):
        h1, h2 = highs[i], highs[i + 1]
        if not prices_near(h1.price, h2.price, 0.15):
            continue

        between_lows = [lo for lo in lows if h1.index < lo.index < h2.index]
        if not between_lows:
            continue

        neckline = min(lo.price for lo in between_lows)
        bar_count = h2.index - h1.index + 1
        if bar_count < 4:
            continue

        last = window[-1]
        completion = min(1.0, (h2.price - last.c) / (h2.price - neckline)) if h2.price > neckline else 0.0
        if completion < 0.5:
            continue

        pattern_height = max(h1.price, h2.price) - neckline
        entry = neckline
        stop_price = max(h1.price, h2.price)
        t1 = neckline - pattern_height * 0.618
        t2 = neckline - pattern_height
        t3 = neckline - pattern_height * 1.618

        return PatternResult(
            detected=True,
            pattern_id="double_top",
            group="B",
            direction="SHORT",
            completion=completion,
            bar_count=bar_count,
            method="Geometric",
            potential_r="3-5R",
            key_levels={
                "high_1": h1.price,
                "high_2": h2.price,
                "neckline": neckline,
                "target": neckline - pattern_height,
                "stop": stop_price,
            },
            confidence=0.65 + 0.15 * completion,
            entry_price=entry,
            stop=stop_price,
            targets=[t1, t2, t3],
        )

    return PatternResult()
