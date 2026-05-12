"""Pattern: Stair-step (HH/HL or LL/LH).

Orderly trending structure: higher-highs + higher-lows (up)
or lower-lows + lower-highs (down).
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput, ContextResult, PatternResult


def detect_stair_step(
    bars: List[BarInput],
    ctx: ContextResult,
) -> PatternResult:
    """Detect stair-step: 3+ bars making HH/HL or LL/LH."""
    if len(bars) < 4:
        return PatternResult()

    recent = bars[-4:]

    # Check HH/HL (bullish stair-step)
    hh_count = 0
    hl_count = 0
    for i in range(1, len(recent)):
        if recent[i].h > recent[i - 1].h:
            hh_count += 1
        if recent[i].l > recent[i - 1].l:
            hl_count += 1

    if hh_count >= 3 and hl_count >= 2:
        return PatternResult(
            detected="Stair-step",
            completion=round(min(hh_count, hl_count) / 3.0, 2),
        )

    # Check LL/LH (bearish stair-step)
    ll_count = 0
    lh_count = 0
    for i in range(1, len(recent)):
        if recent[i].l < recent[i - 1].l:
            ll_count += 1
        if recent[i].h < recent[i - 1].h:
            lh_count += 1

    if ll_count >= 3 and lh_count >= 2:
        return PatternResult(
            detected="Stair-step",
            completion=round(min(ll_count, lh_count) / 3.0, 2),
        )

    return PatternResult()
