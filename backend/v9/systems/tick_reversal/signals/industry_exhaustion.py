"""Industry Signal 4: Exhaustion at Extreme.

High volume at the extreme of a move that fails to continue.
Large wick + high volume at the tip = exhaustion (bearish for longs, bullish for shorts).
This is a NEGATIVE signal (caution flag per spec).
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput


def calc_exhaustion(
    bar: BarInput,
    bars: List[BarInput],
) -> bool:
    """Check for exhaustion: high volume at extreme with reversal wick."""
    if len(bars) < 3:
        return False

    bar_range = bar.h - bar.l
    if bar_range <= 0:
        return False

    body = abs(bar.c - bar.o)
    body_pct = body / bar_range

    # Exhaustion: small body, large wicks, high relative volume
    avg_vol = sum(b.vol for b in bars[-4:-1]) / min(3, len(bars) - 1) if len(bars) > 1 else bar.vol
    if avg_vol <= 0:
        return False

    high_volume = bar.vol > avg_vol * 1.5
    small_body = body_pct < 0.3

    # Check if at recent extreme
    recent_high = max(b.h for b in bars[-6:]) if len(bars) >= 6 else max(b.h for b in bars)
    recent_low = min(b.l for b in bars[-6:]) if len(bars) >= 6 else min(b.l for b in bars)

    at_high = bar.h >= recent_high
    at_low = bar.l <= recent_low

    return high_volume and small_body and (at_high or at_low)
