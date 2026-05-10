"""A4. Initiative Seller — Mirror of Initiative Buyer, POC falling."""

from __future__ import annotations
from typing import List
from backend.v9.systems.chart_5min.models import Bar, PatternResult


def detect_initiative_seller(bars: List[Bar]) -> PatternResult:
    """Detect Initiative Seller in last 4 bars.

    Mirror of A3: POC migrating downward, no buyer entry, delta negative.
    """
    if len(bars) < 4:
        return PatternResult()

    window = bars[-4:]

    poc_values = [b.poc_price for b in window if b.poc_price > 0]
    if len(poc_values) < 2:
        poc_values = [b.c for b in window]

    poc_migration = poc_values[0] - poc_values[-1]  # positive = falling

    tick_size = 0.25
    min_migration_ticks = 4
    if poc_migration < tick_size * min_migration_ticks:
        return PatternResult()

    avg_sellers = sum(b.belly_sellers for b in window) / 4
    avg_buyers = sum(b.belly_buyers for b in window) / 4
    if avg_buyers > 0 and avg_sellers > 0 and avg_buyers > avg_sellers * 1.5:
        return PatternResult()

    last = window[-1]
    if last.cumulative_delta > 0:
        return PatternResult()

    stop_price = max(b.h for b in window)
    entry = last.c
    risk = stop_price - entry
    t1 = entry - risk * 4 if risk > 0 else entry - 1.0
    t2 = entry - risk * 6 if risk > 0 else entry - 2.0
    t3 = entry - risk * 8 if risk > 0 else entry - 3.0

    return PatternResult(
        detected=True,
        pattern_id="initiative_seller",
        group="A",
        direction="SHORT",
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
