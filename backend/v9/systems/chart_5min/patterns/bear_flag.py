"""B2b. Bear Flag — mirror of Bull Flag."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import linear_regression_slope


def detect_bear_flag(bars: List[Bar]) -> PatternResult:
    """Detect Bear Flag in 5-10 bars."""
    if len(bars) < 5:
        return PatternResult()

    window = bars[-min(len(bars), 12):]
    n = len(window)

    pole_len = min(3, n // 2)
    pole = window[:pole_len]
    flag = window[pole_len:]

    if len(flag) < 2:
        return PatternResult()

    pole_move = pole[0].o - pole[-1].c  # downward = positive
    pole_range = max(b.h for b in pole) - min(b.l for b in pole)
    if pole_range == 0 or pole_move / pole_range < 0.5:
        return PatternResult()

    flag_body = flag[:-1] if len(flag) > 2 else flag
    flag_closes = [b.c for b in flag_body]
    flag_slope = linear_regression_slope(flag_closes)
    if flag_slope < -pole_range * 0.05:
        return PatternResult()

    flag_range = max(b.h for b in flag) - min(b.l for b in flag)
    if flag_range > pole_range * 0.7:
        return PatternResult()

    flag_low = min(b.l for b in flag[:-1]) if len(flag) > 1 else flag[0].l
    last = window[-1]

    flag_high = max(b.h for b in flag)
    completion = min(1.0, (flag_high - last.c) / (flag_high - flag_low)) \
        if flag_high > flag_low else 0.0

    if completion < 0.6:
        return PatternResult()

    pole_height = pole[0].h - pole[-1].l
    entry = flag_low
    stop_price = flag_high
    t1 = entry - pole_height * 0.618
    t2 = entry - pole_height
    t3 = entry - pole_height * 1.618

    return PatternResult(
        detected=True,
        pattern_id="bear_flag",
        group="B",
        direction="SHORT",
        completion=completion,
        bar_count=n,
        method="Hybrid",
        potential_r="3-6R",
        key_levels={
            "pole_high": pole[0].h,
            "pole_low": pole[-1].l,
            "pole_height": pole_height,
            "flag_low": flag_low,
            "flag_high": flag_high,
            "target": flag_low - pole_height,
        },
        confidence=0.6 + 0.2 * completion,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
