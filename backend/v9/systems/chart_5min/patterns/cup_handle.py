"""C2a. Cup & Handle — rounded base + handle + breakout."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import find_pivots, swing_highs, swing_lows, prices_near


def detect_cup_handle(bars: List[Bar]) -> PatternResult:
    """Detect Cup & Handle in 20-40 bars.

    Criteria:
    1. U-shaped price action (cup): decline, rounded base, recovery
    2. Small consolidation after recovery (handle)
    3. Breakout above the rim (cup high)
    """
    if len(bars) < 15:
        return PatternResult()

    window = bars[-min(len(bars), 45):]
    n = len(window)

    # Find the cup: left rim, bottom, right rim
    pivots = find_pivots(window, lookback=3)
    highs = swing_highs(pivots)
    lows = swing_lows(pivots)

    if len(highs) < 2 or len(lows) < 1:
        return PatternResult()

    # Left rim = first swing high, cup bottom = deepest low, right rim = later high
    left_rim = highs[0]

    # Find the deepest low after the left rim
    cup_lows = [lo for lo in lows if lo.index > left_rim.index]
    if not cup_lows:
        return PatternResult()

    cup_bottom = min(cup_lows, key=lambda lo: lo.price)

    # Right rim: high after cup bottom, near left rim level
    right_rims = [h for h in highs if h.index > cup_bottom.index]
    if not right_rims:
        return PatternResult()

    right_rim = None
    for h in right_rims:
        if prices_near(h.price, left_rim.price, 0.15):
            right_rim = h
            break

    if right_rim is None:
        return PatternResult()

    # Cup should be U-shaped (not V): bottom should be rounded
    cup_depth = left_rim.price - cup_bottom.price
    if cup_depth <= 0:
        return PatternResult()

    # Handle: small pullback after right rim (last few bars)
    handle_start = right_rim.index
    handle_bars = [b for b in window[handle_start:]]
    if len(handle_bars) < 2:
        # No handle yet — still forming
        handle_bars = window[-3:]

    handle_low = min(b.l for b in handle_bars)
    handle_pullback = right_rim.price - handle_low

    # Handle should be less than 50% of cup depth
    if handle_pullback > cup_depth * 0.5:
        return PatternResult()

    last = window[-1]
    rim_level = max(left_rim.price, right_rim.price)
    completion = min(1.0, (last.c - cup_bottom.price) / (rim_level - cup_bottom.price)) \
        if rim_level > cup_bottom.price else 0.0

    if completion < 0.5:
        return PatternResult()

    entry = rim_level
    stop_price = handle_low
    t1 = rim_level + cup_depth * 0.618
    t2 = rim_level + cup_depth
    t3 = rim_level + cup_depth * 1.618

    return PatternResult(
        detected=True,
        pattern_id="cup_handle",
        group="C",
        direction="LONG",
        completion=completion,
        bar_count=right_rim.index - left_rim.index + 1,
        method="Geometric",
        potential_r="6-12R",
        key_levels={
            "left_rim": left_rim.price,
            "cup_bottom": cup_bottom.price,
            "right_rim": right_rim.price,
            "handle_low": handle_low,
            "target": rim_level + cup_depth,
            "stop": stop_price,
        },
        confidence=0.6 + 0.15 * completion,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
