"""Pattern: Accumulation + Breakout.

Zohar: "כדי שיתפוצץ - צריך אגירה"
5+ bars in tight range, then a breakout bar that closes outside.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput, ContextResult, PatternResult


def detect_accumulation_breakout(
    bars: List[BarInput],
    ctx: ContextResult,
) -> PatternResult:
    """Detect accumulation followed by breakout."""
    if len(bars) < 2:
        return PatternResult()

    if not ctx.accumulation_active:
        return PatternResult()

    # Need at least min_bars of accumulation before this bar
    if ctx.accumulation_bars < 5:
        return PatternResult()

    current = bars[-1]
    prev = bars[-2]

    # Calculate range of accumulation zone from recent bars
    accum_bars = bars[-(ctx.accumulation_bars + 1):-1]
    if not accum_bars:
        return PatternResult()

    accum_high = max(b.h for b in accum_bars)
    accum_low = min(b.l for b in accum_bars)

    # Breakout: current bar closes outside the accumulation range
    breakout_up = current.c > accum_high
    breakout_down = current.c < accum_low

    if not (breakout_up or breakout_down):
        return PatternResult()

    # Completion: how far beyond the range did we close?
    accum_range = accum_high - accum_low
    if accum_range <= 0:
        return PatternResult()

    if breakout_up:
        overshoot = current.c - accum_high
    else:
        overshoot = accum_low - current.c

    completion = min(1.0, overshoot / accum_range) if accum_range > 0 else 1.0

    return PatternResult(
        detected="Accumulation + Breakout",
        completion=round(completion, 2),
    )
