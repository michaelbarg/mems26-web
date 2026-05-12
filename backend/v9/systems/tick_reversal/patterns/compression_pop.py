"""Pattern: Compression + Pop.

Bars get progressively smaller (compression), then a large bar breaks out.
Inside-bar / narrowing-range sequence followed by expansion.
"""

from __future__ import annotations
from typing import List
from ..schemas import BarInput, ContextResult, PatternResult


def detect_compression_pop(
    bars: List[BarInput],
    ctx: ContextResult,
) -> PatternResult:
    """Detect compression (shrinking ranges) then pop (large expansion bar)."""
    if len(bars) < 4:
        return PatternResult()

    # Check last 3 bars before current for compression
    lookback = bars[-4:-1]
    current = bars[-1]

    ranges = [b.h - b.l for b in lookback]
    current_range = current.h - current.l

    # All ranges must be positive
    if any(r <= 0 for r in ranges) or current_range <= 0:
        return PatternResult()

    # Compression: each bar's range <= previous (shrinking)
    is_compressing = all(ranges[i] <= ranges[i - 1] for i in range(1, len(ranges)))
    if not is_compressing:
        return PatternResult()

    # Pop: current bar range is at least 1.5x the smallest compression bar
    min_compressed = min(ranges)
    if current_range < min_compressed * 1.5:
        return PatternResult()

    avg_compressed = sum(ranges) / len(ranges)
    expansion_ratio = current_range / avg_compressed

    return PatternResult(
        detected="Compression + Pop",
        completion=round(min(1.0, expansion_ratio / 2.0), 2),
    )
