"""Bar integrity validator — Python mirror of frontend looksOk().

Single source of truth for OHLC sanity checks. Used by:
- bars.py POST /api/v9/bars/5min (HTTP push path, primary gate)
- bars_5min_history.py GET /api/v9/chart/bars5min (query-time filter)

The heuristic mirrors frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx
function looksOk(b) plus an additional bar-range check that catches
displaced-body outliers the wick check alone cannot detect.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger("mems26.bar_integrity")

# Maximum wick-to-body ratio (2% — matches frontend looksOk)
MAX_WICK_RATIO = 0.02

# Maximum bar range (high-low)/low.  For MES 5-min bars, 2% = ~148 pts at
# price 7400 — far beyond normal volatility (typical ATR ~10-20 pts/bar).
# Require both ratio and absolute range so low-price unit tests do not become
# false positives.
MAX_BAR_RANGE_RATIO = 0.02
MAX_BAR_RANGE_POINTS = 20.0


def bar_is_valid(
    open: float,
    high: float,
    low: float,
    close: float,
) -> Tuple[bool, Optional[str]]:
    """Check whether an OHLC bar passes integrity checks.

    Returns (True, None) if valid, or (False, reason_string) if invalid.
    """
    # Null / non-positive checks
    if open is None or high is None or low is None or close is None:
        return False, "null_ohlc"
    if open <= 0 or high <= 0 or low <= 0 or close <= 0:
        return False, "non_positive_ohlc"

    # Basic ordering: low must not exceed high
    if low > high:
        return False, "low_gt_high"

    # Body-cliff check: low wick > 2% of body bottom
    body = min(open, close)
    if body > 0 and (body - low) / body > MAX_WICK_RATIO:
        return False, "low_wick_exceeds_2pct"

    # Body-cliff check: high wick > 2% of body top
    body_top = max(open, close)
    if body_top > 0 and (high - body_top) / body_top > MAX_WICK_RATIO:
        return False, "high_wick_exceeds_2pct"

    # Bar range check: (high - low) / low must not exceed MAX_BAR_RANGE_RATIO
    # when the absolute span is also large. Catches displaced-body outliers
    # where wick checks pass but the full candle range is impossible.
    bar_range = high - low
    if low > 0 and bar_range > MAX_BAR_RANGE_POINTS and bar_range / low > MAX_BAR_RANGE_RATIO:
        return False, "bar_range_exceeds_2pct"

    return True, None
