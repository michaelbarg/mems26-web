"""C2b. Inverse Cup & Handle — bearish mirror."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import find_pivots, swing_highs, swing_lows, prices_near


def detect_inverse_cup_handle(bars: List[Bar]) -> PatternResult:
    """Detect Inverse Cup & Handle in 20-40 bars."""
    if len(bars) < 15:
        return PatternResult()

    window = bars[-min(len(bars), 45):]
    pivots = find_pivots(window, lookback=3)
    highs = swing_highs(pivots)
    lows = swing_lows(pivots)

    if len(lows) < 2 or len(highs) < 1:
        return PatternResult()

    left_rim = lows[0]
    cup_highs = [h for h in highs if h.index > left_rim.index]
    if not cup_highs:
        return PatternResult()

    cup_top = max(cup_highs, key=lambda h: h.price)
    right_rims = [lo for lo in lows if lo.index > cup_top.index]
    if not right_rims:
        return PatternResult()

    right_rim = None
    for lo in right_rims:
        if prices_near(lo.price, left_rim.price, 0.15):
            right_rim = lo
            break

    if right_rim is None:
        return PatternResult()

    cup_depth = cup_top.price - left_rim.price
    if cup_depth <= 0:
        return PatternResult()

    handle_bars = window[right_rim.index:] if right_rim.index < len(window) else window[-3:]
    if len(handle_bars) < 2:
        handle_bars = window[-3:]

    handle_high = max(b.h for b in handle_bars)
    handle_pullback = handle_high - right_rim.price
    if handle_pullback > cup_depth * 0.5:
        return PatternResult()

    last = window[-1]
    rim_level = min(left_rim.price, right_rim.price)
    completion = min(1.0, (cup_top.price - last.c) / (cup_top.price - rim_level)) \
        if cup_top.price > rim_level else 0.0

    if completion < 0.5:
        return PatternResult()

    entry = rim_level
    stop_price = handle_high
    t1 = rim_level - cup_depth * 0.618
    t2 = rim_level - cup_depth
    t3 = rim_level - cup_depth * 1.618

    return PatternResult(
        detected=True,
        pattern_id="inverse_cup_handle",
        group="C",
        direction="SHORT",
        completion=completion,
        bar_count=right_rim.index - left_rim.index + 1,
        method="Geometric",
        potential_r="6-12R",
        key_levels={
            "left_rim": left_rim.price,
            "cup_top": cup_top.price,
            "right_rim": right_rim.price,
            "handle_high": handle_high,
            "target": rim_level - cup_depth,
            "stop": stop_price,
        },
        confidence=0.6 + 0.15 * completion,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
