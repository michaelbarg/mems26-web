"""Shared helpers for pattern detection."""

from __future__ import annotations
from typing import List, Tuple, Optional
from backend.v9.systems.chart_5min.models import Bar, Pivot


def find_pivots(bars: List[Bar], lookback: int = 2) -> List[Pivot]:
    """Find swing highs and lows in bar series.
    A pivot high needs `lookback` lower highs on each side.
    A pivot low needs `lookback` higher lows on each side.
    """
    pivots = []
    if len(bars) < 2 * lookback + 1:
        return pivots

    for i in range(lookback, len(bars) - lookback):
        # Check swing high
        is_high = all(
            bars[i].h >= bars[i - j].h and bars[i].h >= bars[i + j].h
            for j in range(1, lookback + 1)
        )
        if is_high:
            pivots.append(Pivot(index=i, price=bars[i].h, is_high=True, bar=bars[i]))

        # Check swing low
        is_low = all(
            bars[i].l <= bars[i - j].l and bars[i].l <= bars[i + j].l
            for j in range(1, lookback + 1)
        )
        if is_low:
            pivots.append(Pivot(index=i, price=bars[i].l, is_high=False, bar=bars[i]))

    return pivots


def swing_highs(pivots: List[Pivot]) -> List[Pivot]:
    return [p for p in pivots if p.is_high]


def swing_lows(pivots: List[Pivot]) -> List[Pivot]:
    return [p for p in pivots if not p.is_high]


def prices_near(a: float, b: float, tolerance_pct: float = 0.15) -> bool:
    """Check if two prices are within tolerance_pct of each other."""
    if a == 0 and b == 0:
        return True
    avg = (abs(a) + abs(b)) / 2
    if avg == 0:
        return True
    return abs(a - b) / avg <= tolerance_pct


def linear_regression_slope(values: List[float]) -> float:
    """Simple linear regression slope."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den


def is_converging(highs: List[float], lows: List[float]) -> bool:
    """Check if high series slopes down and low series slopes up (converging)."""
    if len(highs) < 2 or len(lows) < 2:
        return False
    h_slope = linear_regression_slope(highs)
    l_slope = linear_regression_slope(lows)
    return h_slope < 0 and l_slope > 0


def avg_body(bars: List[Bar]) -> float:
    if not bars:
        return 0.0
    return sum(b.body for b in bars) / len(bars)


def avg_range(bars: List[Bar]) -> float:
    if not bars:
        return 0.0
    return sum(b.range for b in bars) / len(bars)
