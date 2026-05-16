"""Opening Choppiness scorer — Tree V3.3 §Q4.

Score 0-100 based on first 3-6 bars after open:
  High score = choppy (rotational, overlapping bars)
  Low score = directional (clean trend)

Components:
  - Range/ATR ratio (narrow range relative to recent = choppy)
  - Bar direction flips (alternating red/green = choppy)
  - Body variance (similar-sized bodies = directional, variable = choppy)

Used by Confluence to subtract 1 from score when choppy.
"""
from __future__ import annotations

from typing import List


def compute_choppiness(bars: List[dict], min_bars: int = 3, max_bars: int = 6) -> float:
    """Compute choppiness score 0-100 from opening bars.

    Args:
        bars: list of OHLCV bars (first N bars of session)
        min_bars: minimum bars needed (default 3)
        max_bars: maximum bars to consider (default 6)

    Returns:
        Score 0-100 (higher = choppier)
    """
    if len(bars) < min_bars:
        return 50.0  # neutral when insufficient data

    window = bars[:max_bars]
    n = len(window)

    # Component 1: Direction flips (0-40 points)
    flips = 0
    for i in range(1, n):
        prev_bull = window[i - 1].get("c", 0) > window[i - 1].get("o", 0)
        curr_bull = window[i].get("c", 0) > window[i].get("o", 0)
        if prev_bull != curr_bull:
            flips += 1
    flip_score = min(40.0, (flips / max(1, n - 1)) * 50.0)

    # Component 2: Overlap ratio (0-35 points)
    overlaps = 0
    for i in range(1, n):
        prev_range = (window[i - 1].get("h", 0), window[i - 1].get("l", 0))
        curr_range = (window[i].get("h", 0), window[i].get("l", 0))
        # Overlap exists if current bar's range intersects previous
        if curr_range[1] < prev_range[0] and curr_range[0] > prev_range[1]:
            overlaps += 1
    overlap_score = min(35.0, (overlaps / max(1, n - 1)) * 45.0)

    # Component 3: Body size variance (0-25 points)
    bodies = [abs(b.get("c", 0) - b.get("o", 0)) for b in window]
    if bodies:
        mean_body = sum(bodies) / len(bodies)
        if mean_body > 0:
            variance = sum((b - mean_body) ** 2 for b in bodies) / len(bodies)
            cv = (variance ** 0.5) / mean_body  # coefficient of variation
            variance_score = min(25.0, cv * 25.0)
        else:
            variance_score = 25.0  # all doji = very choppy
    else:
        variance_score = 12.5

    return min(100.0, flip_score + overlap_score + variance_score)


def is_choppy(bars: List[dict], threshold: float = 60.0) -> bool:
    """Quick boolean: is opening choppy? (score > threshold)."""
    return compute_choppiness(bars) > threshold
