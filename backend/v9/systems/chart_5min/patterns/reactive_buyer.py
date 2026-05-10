"""A1. Reactive Buyer — OFA pattern, 4 bars, near support.

Detection: Price drops to support → 90%+ sellers → belly buyers appear
→ POC holds above support → reversal candle.
"""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult


def detect_reactive_buyer(bars: List[Bar]) -> PatternResult:
    """Detect Reactive Buyer pattern in last 4 bars.

    Criteria:
    1. Bar[-4] or [-3]: strong selling (belly_sellers > 60%)
    2. Bar[-2]: selling exhaustion (belly_sellers drops or belly_buyers rises)
    3. Bar[-1]: reversal — close > open, POC holds above recent low
    4. Price near a support level (val or recent swing low)
    """
    if len(bars) < 4:
        return PatternResult()

    window = bars[-4:]
    b0, b1, b2, b3 = window

    # Phase 1: Selling pressure in first bars
    total_range = max(b.h for b in window) - min(b.l for b in window)
    if total_range == 0:
        return PatternResult()

    # Check for selling into support
    has_sell_pressure = (b0.is_bearish or b1.is_bearish)
    if not has_sell_pressure:
        return PatternResult()

    # Phase 2: Buyer absorption — sellers weaken or buyers show up
    seller_exhaustion = (
        b2.belly_sellers < b1.belly_sellers or
        b2.belly_buyers > b1.belly_buyers or
        b2.body < b1.body  # smaller body = exhaustion
    )

    # Phase 3: Reversal bar
    reversal = b3.is_bullish and b3.c > b2.mid

    # Phase 4: POC integrity — POC hasn't broken below the pattern low
    pattern_low = min(b.l for b in window)
    poc_holds = b3.poc_price >= pattern_low or b3.poc_price == 0

    if not (seller_exhaustion and reversal and poc_holds):
        return PatternResult()

    # Near support check (val or pattern low relative to range)
    near_support = b3.l <= b3.val * 1.002 if b3.val > 0 else True

    completion = 1.0 if near_support else 0.85
    confidence = 0.7 if near_support else 0.5

    stop_price = pattern_low - total_range * 0.25
    entry = b3.c
    risk = entry - stop_price
    t1 = entry + risk * 2
    t2 = entry + risk * 3
    t3 = entry + risk * 4

    return PatternResult(
        detected=True,
        pattern_id="reactive_buyer",
        group="A",
        direction="LONG",
        completion=completion,
        bar_count=4,
        method="OFA",
        potential_r="2-4R",
        key_levels={
            "support": pattern_low,
            "entry_zone": entry,
            "stop": stop_price,
        },
        confidence=confidence,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
