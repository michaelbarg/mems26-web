"""Pattern: Failed Test.

Price tests a level (high/low), fails to hold, and reverses.
Classic false breakout / stop hunt pattern.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput, ContextResult, PatternResult


def detect_failed_test(
    bars: List[BarInput],
    ctx: ContextResult,
) -> PatternResult:
    """Detect failed test: bar pokes beyond prior extreme then reverses."""
    if len(bars) < 4:
        return PatternResult()

    current = bars[-1]
    lookback = bars[-4:-1]

    prior_high = max(b.h for b in lookback)
    prior_low = min(b.l for b in lookback)

    # Failed test high: wick above prior high, but close back inside
    if current.h > prior_high and current.c < prior_high:
        overshoot = current.h - prior_high
        bar_range = current.h - current.l
        if bar_range > 0:
            rejection_pct = (current.h - current.c) / bar_range
            if rejection_pct > 0.5:
                return PatternResult(
                    detected="Failed Test",
                    completion=round(rejection_pct, 2),
                )

    # Failed test low: wick below prior low, but close back inside
    if current.l < prior_low and current.c > prior_low:
        overshoot = prior_low - current.l
        bar_range = current.h - current.l
        if bar_range > 0:
            rejection_pct = (current.c - current.l) / bar_range
            if rejection_pct > 0.5:
                return PatternResult(
                    detected="Failed Test",
                    completion=round(rejection_pct, 2),
                )

    return PatternResult()
