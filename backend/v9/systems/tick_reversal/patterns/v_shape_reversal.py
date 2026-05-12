"""Pattern: V-Shape Reversal.

Sharp move down followed by sharp move up (or vice versa).
Creates a V/inverted-V shape on the chart.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput, ContextResult, PatternResult


def detect_v_shape_reversal(
    bars: List[BarInput],
    ctx: ContextResult,
) -> PatternResult:
    """Detect V-shape reversal: 2+ bars down then 2+ bars up (or inverse)."""
    if len(bars) < 5:
        return PatternResult()

    recent = bars[-5:]

    # Check for V-bottom: 2+ down bars then 2+ up bars
    down_count = 0
    pivot_idx = -1
    for i in range(len(recent) - 1):
        if recent[i].c < recent[i].o:
            down_count += 1
        else:
            if down_count >= 2:
                pivot_idx = i
            break

    if pivot_idx > 0:
        up_count = sum(1 for b in recent[pivot_idx:] if b.c > b.o)
        if up_count >= 2:
            # V-bottom confirmed
            low_at_pivot = min(b.l for b in recent[:pivot_idx + 1])
            recovery = recent[-1].c - low_at_pivot
            drop = recent[0].o - low_at_pivot
            completion = min(1.0, recovery / drop) if drop > 0 else 0.0
            return PatternResult(detected="V-Shape Reversal", completion=round(completion, 2))

    # Check for inverted-V: 2+ up bars then 2+ down bars
    up_count = 0
    pivot_idx = -1
    for i in range(len(recent) - 1):
        if recent[i].c > recent[i].o:
            up_count += 1
        else:
            if up_count >= 2:
                pivot_idx = i
            break

    if pivot_idx > 0:
        dn_count = sum(1 for b in recent[pivot_idx:] if b.c < b.o)
        if dn_count >= 2:
            high_at_pivot = max(b.h for b in recent[:pivot_idx + 1])
            drop_from_high = high_at_pivot - recent[-1].c
            rise = high_at_pivot - recent[0].o
            completion = min(1.0, drop_from_high / rise) if rise > 0 else 0.0
            return PatternResult(detected="V-Shape Reversal", completion=round(completion, 2))

    return PatternResult()
