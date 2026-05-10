"""C1a. Head & Shoulders — 3 swings, neckline break."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult
from ._helpers import find_pivots, swing_highs, swing_lows, prices_near


def detect_head_shoulders(bars: List[Bar]) -> PatternResult:
    """Detect Head & Shoulders (bearish) in 15-25 bars.

    Criteria:
    1. Three swing highs: left shoulder, head (highest), right shoulder
    2. Shoulders at near same level, head higher
    3. Neckline connecting the lows between the shoulders
    4. Price breaks below neckline
    """
    if len(bars) < 12:
        return PatternResult()

    window = bars[-min(len(bars), 30):]
    pivots = find_pivots(window, lookback=2)
    highs = swing_highs(pivots)
    lows = swing_lows(pivots)

    if len(highs) < 3 or len(lows) < 2:
        return PatternResult()

    # Try combinations of 3 consecutive highs
    for i in range(len(highs) - 2):
        ls, head, rs = highs[i], highs[i + 1], highs[i + 2]

        # Head must be highest
        if head.price <= ls.price or head.price <= rs.price:
            continue

        # Shoulders near equal
        if not prices_near(ls.price, rs.price, 0.20):
            continue

        # Find lows between shoulders (neckline points)
        nl_lows = [lo for lo in lows if ls.index < lo.index < rs.index]
        if len(nl_lows) < 1:
            continue

        neckline = min(lo.price for lo in nl_lows)
        bar_count = rs.index - ls.index + 1

        last = window[-1]
        # Completion: how far below neckline has price gone?
        if head.price <= neckline:
            continue

        completion = min(1.0, (neckline - last.c) / (head.price - neckline) + 0.5) \
            if last.c < neckline else (last.h - neckline) / (head.price - neckline) * 0.5

        if completion < 0.4:
            continue

        pattern_height = head.price - neckline
        entry = neckline
        stop_price = rs.price
        t1 = neckline - pattern_height * 0.618
        t2 = neckline - pattern_height
        t3 = neckline - pattern_height * 1.618

        return PatternResult(
            detected=True,
            pattern_id="head_shoulders",
            group="C",
            direction="SHORT",
            completion=min(completion, 1.0),
            bar_count=bar_count,
            method="Geometric",
            potential_r="5-10R",
            key_levels={
                "left_shoulder": ls.price,
                "head": head.price,
                "right_shoulder": rs.price,
                "neckline": neckline,
                "target": neckline - pattern_height,
                "stop": stop_price,
            },
            confidence=0.6 + 0.2 * min(completion, 1.0),
            entry_price=entry,
            stop=stop_price,
            targets=[t1, t2, t3],
        )

    return PatternResult()
