"""A2. Reactive Seller — Mirror of Reactive Buyer, near resistance."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult


def detect_reactive_seller(bars: List[Bar]) -> PatternResult:
    """Detect Reactive Seller in last 4 bars.

    Mirror of A1: Price rises to resistance → 90%+ buyers → belly sellers
    appear → POC holds below resistance → reversal candle down.
    """
    if len(bars) < 4:
        return PatternResult()

    window = bars[-4:]
    b0, b1, b2, b3 = window

    total_range = max(b.h for b in window) - min(b.l for b in window)
    if total_range == 0:
        return PatternResult()

    # Phase 1: Buying pressure into resistance
    has_buy_pressure = (b0.is_bullish or b1.is_bullish)
    if not has_buy_pressure:
        return PatternResult()

    # Phase 2: Buyer exhaustion
    buyer_exhaustion = (
        b2.belly_buyers < b1.belly_buyers or
        b2.belly_sellers > b1.belly_sellers or
        b2.body < b1.body
    )

    # Phase 3: Bearish reversal
    reversal = b3.is_bearish and b3.c < b2.mid

    # Phase 4: POC integrity
    pattern_high = max(b.h for b in window)
    poc_holds = b3.poc_price <= pattern_high or b3.poc_price == 0

    if not (buyer_exhaustion and reversal and poc_holds):
        return PatternResult()

    near_resistance = b3.h >= b3.vah * 0.998 if b3.vah > 0 else True
    completion = 1.0 if near_resistance else 0.85

    stop_price = pattern_high + total_range * 0.25
    entry = b3.c
    risk = stop_price - entry
    t1 = entry - risk * 2
    t2 = entry - risk * 3
    t3 = entry - risk * 4

    return PatternResult(
        detected=True,
        pattern_id="reactive_seller",
        group="A",
        direction="SHORT",
        completion=completion,
        bar_count=4,
        method="OFA",
        potential_r="2-4R",
        key_levels={
            "resistance": pattern_high,
            "entry_zone": entry,
            "stop": stop_price,
        },
        confidence=0.7 if near_resistance else 0.5,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
