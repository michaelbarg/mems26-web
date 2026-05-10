"""A3. Initiative Buyer — OFA, mid-range, POC rising 6-7 ticks."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult


def detect_initiative_buyer(bars: List[Bar]) -> PatternResult:
    """Detect Initiative Buyer in last 4 bars.

    Criteria:
    1. Price in mid-range (not at extremes)
    2. POC migrating upward across bars (6-7+ ticks)
    3. No significant seller entry (belly_sellers stays low)
    4. Cumulative delta positive and increasing
    """
    if len(bars) < 4:
        return PatternResult()

    window = bars[-4:]

    # POC migration check — need POC values
    poc_values = [b.poc_price for b in window if b.poc_price > 0]
    if len(poc_values) < 2:
        # No POC data: use close prices for directional momentum
        poc_values = [b.c for b in window]

    poc_migration = poc_values[-1] - poc_values[0]

    # Need upward POC migration (min ~1.5 ticks on MES = 0.375 points)
    tick_size = 0.25  # MES tick
    min_migration_ticks = 4
    if poc_migration < tick_size * min_migration_ticks:
        return PatternResult()

    # Sellers should not be dominating
    avg_sellers = sum(b.belly_sellers for b in window) / 4
    avg_buyers = sum(b.belly_buyers for b in window) / 4
    if avg_sellers > 0 and avg_buyers > 0 and avg_sellers > avg_buyers * 1.5:
        return PatternResult()

    # Cumulative delta should be positive
    last = window[-1]
    if last.cumulative_delta < 0:
        return PatternResult()

    # Mid-range check: not at extremes
    pattern_range = max(b.h for b in window) - min(b.l for b in window)
    if pattern_range == 0:
        return PatternResult()

    stop_price = min(b.l for b in window)
    entry = last.c
    risk = entry - stop_price
    t1 = entry + risk * 4 if risk > 0 else entry + 1.0
    t2 = entry + risk * 6 if risk > 0 else entry + 2.0
    t3 = entry + risk * 8 if risk > 0 else entry + 3.0

    return PatternResult(
        detected=True,
        pattern_id="initiative_buyer",
        group="A",
        direction="LONG",
        completion=1.0,
        bar_count=4,
        method="OFA",
        potential_r="4-8R",
        key_levels={
            "poc_start": poc_values[0],
            "poc_end": poc_values[-1],
            "poc_migration_ticks": poc_migration / tick_size,
            "entry_zone": entry,
            "stop": stop_price,
        },
        confidence=0.7,
        entry_price=entry,
        stop=stop_price,
        targets=[t1, t2, t3],
    )
