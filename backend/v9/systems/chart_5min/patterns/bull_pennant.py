"""B3a. Bull Pennant — pole + converging triangle."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import linear_regression_slope


def detect_bull_pennant(bars: List[Bar]) -> PatternResult:
    """Detect Bull Pennant in 5-10 bars.

    Similar to Bull Flag but consolidation converges (triangle shape).
    """
    if len(bars) < 5:
        return PatternResult()

    window = bars[-min(len(bars), 12):]
    n = len(window)

    pole_len = min(3, n // 2)
    pole = window[:pole_len]
    pennant = window[pole_len:]

    if len(pennant) < 3:
        return PatternResult()

    # Strong upward pole
    pole_move = pole[-1].c - pole[0].o
    pole_range = max(b.h for b in pole) - min(b.l for b in pole)
    if pole_range == 0 or pole_move / pole_range < 0.4:
        return PatternResult()

    # Pennant: converging — highs slope down, lows slope up
    p_highs = [b.h for b in pennant]
    p_lows = [b.l for b in pennant]
    h_slope = linear_regression_slope(p_highs)
    l_slope = linear_regression_slope(p_lows)

    if not (h_slope < 0 and l_slope > 0):
        return PatternResult()

    # Pennant range shrinks
    first_range = pennant[0].range
    last_range = pennant[-1].range
    if first_range > 0 and last_range / first_range > 0.9:
        return PatternResult()

    last = window[-1]
    pennant_high = max(b.h for b in pennant)
    pole_height = pole[-1].h - pole[0].l

    completion = 0.85 if last.c >= pennant_high else 0.7

    pennant_low = min(b.l for b in pennant)
    entry = pennant_high
    stop_price = pennant_low
    t1 = entry + pole_height * 0.618
    t2 = entry + pole_height
    t3 = entry + pole_height * 1.618

    return PatternResult(
        detected=True,
        pattern_id="bull_pennant",
        group="B",
        direction="LONG",
        completion=completion,
        bar_count=n,
        method="Geometric",
        potential_r="3-5R",
        key_levels={
            "pole_height": pole_height,
            "pennant_high": pennant_high,
            "pennant_low": pennant_low,
            "target": pennant_high + pole_height,
        },
        confidence=0.65,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
