"""B2a. Bull Flag — pole + consolidation channel + breakout."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import linear_regression_slope


def detect_bull_flag(bars: List[Bar]) -> PatternResult:
    """Detect Bull Flag in 5-10 bars.

    Criteria:
    1. Strong upward pole (first 2-3 bars): big bullish move
    2. Consolidation channel (next 3-7 bars): slight downward drift, lower vol
    3. Breakout or near-breakout above consolidation high
    """
    if len(bars) < 5:
        return PatternResult()

    window = bars[-min(len(bars), 12):]
    n = len(window)

    # Find the pole: first few bars should show strong upward move
    pole_len = min(3, n // 2)
    pole = window[:pole_len]
    flag = window[pole_len:]

    if len(flag) < 2:
        return PatternResult()

    # Pole must be bullish: close of last pole bar >> close of first
    pole_move = pole[-1].c - pole[0].o
    pole_range = max(b.h for b in pole) - min(b.l for b in pole)
    if pole_range == 0 or pole_move / pole_range < 0.5:
        return PatternResult()

    # Flag: slight downward or flat drift (exclude last bar — may be breakout)
    flag_body = flag[:-1] if len(flag) > 2 else flag
    flag_closes = [b.c for b in flag_body]
    flag_slope = linear_regression_slope(flag_closes)
    if flag_slope > pole_range * 0.05:
        # Flag should drift down or flat, not strongly up
        return PatternResult()

    # Flag range should be smaller than pole range
    flag_range = max(b.h for b in flag) - min(b.l for b in flag)
    if flag_range > pole_range * 0.7:
        return PatternResult()

    # Check breakout: last bar close above flag high
    flag_high = max(b.h for b in flag[:-1]) if len(flag) > 1 else flag[0].h
    last = window[-1]

    completion = min(1.0, (last.c - min(b.l for b in flag)) / (flag_high - min(b.l for b in flag))) \
        if flag_high > min(b.l for b in flag) else 0.0

    if completion < 0.6:
        return PatternResult()

    pole_height = pole[-1].h - pole[0].l
    flag_low_price = min(b.l for b in flag)
    entry = flag_high
    stop_price = flag_low_price
    risk = entry - stop_price if entry > stop_price else 1.0
    t1 = entry + pole_height * 0.618
    t2 = entry + pole_height
    t3 = entry + pole_height * 1.618

    return PatternResult(
        detected=True,
        pattern_id="bull_flag",
        group="B",
        direction="LONG",
        completion=completion,
        bar_count=n,
        method="Hybrid",
        potential_r="3-6R",
        key_levels={
            "pole_low": pole[0].l,
            "pole_high": pole[-1].h,
            "pole_height": pole_height,
            "flag_high": flag_high,
            "flag_low": flag_low_price,
            "target": flag_high + pole_height,
        },
        confidence=0.6 + 0.2 * completion,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
