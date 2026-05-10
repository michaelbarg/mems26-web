"""B1a. Double Bottom — two equal lows + neckline break."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import find_pivots, swing_lows, swing_highs, prices_near


def detect_double_bottom(bars: List[Bar]) -> PatternResult:
    """Detect Double Bottom in 8-15 bars.

    Criteria:
    1. Two swing lows at near the same price (within 0.15%)
    2. A swing high between them (the neckline)
    3. Last bar closes above or near the neckline
    """
    if len(bars) < 8:
        return PatternResult()

    window = bars[-min(len(bars), 20):]
    lookback = 2 if len(window) >= 12 else 1
    pivots = find_pivots(window, lookback=lookback)
    lows = swing_lows(pivots)
    highs = swing_highs(pivots)

    if len(lows) < 2 or len(highs) < 1:
        return PatternResult()

    # Find two lows with a high between them
    for i in range(len(lows) - 1):
        l1, l2 = lows[i], lows[i + 1]
        if not prices_near(l1.price, l2.price, 0.15):
            continue

        # Need a high between them
        between_highs = [h for h in highs if l1.index < h.index < l2.index]
        if not between_highs:
            continue

        neckline = max(h.price for h in between_highs)
        bar_count = l2.index - l1.index + 1
        if bar_count < 4:
            continue

        # Check completion: has price broken above neckline?
        last = window[-1]
        completion = min(1.0, (last.c - l2.price) / (neckline - l2.price)) if neckline > l2.price else 0.0
        if completion < 0.5:
            continue

        pattern_height = neckline - min(l1.price, l2.price)
        entry = neckline
        stop_price = min(l1.price, l2.price)
        t1 = neckline + pattern_height * 0.618
        t2 = neckline + pattern_height
        t3 = neckline + pattern_height * 1.618

        return PatternResult(
            detected=True,
            pattern_id="double_bottom",
            group="B",
            direction="LONG",
            completion=completion,
            bar_count=bar_count,
            method="Geometric",
            potential_r="3-5R",
            key_levels={
                "low_1": l1.price,
                "low_2": l2.price,
                "neckline": neckline,
                "target": neckline + pattern_height,
                "stop": stop_price,
            },
            confidence=0.65 + 0.15 * completion,
            entry_price=entry,
            stop=stop_price,
            targets=[t1, t2, t3],
        )

    return PatternResult()
