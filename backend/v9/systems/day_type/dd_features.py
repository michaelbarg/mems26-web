"""dd_features.py — detect a Double-Distribution Trend day FROM THE BARS (S1).

Per Michael's Mind-Over-Markets characterization (2026-06-20), a Double-Distribution
Trend day is a ONE-SIDED extension that:
  1. starts from a NARROW initial balance (low early confidence — easy to break),
  2. builds TWO substantial distributions separated by a single-print NECK
     (bimodal volume-by-price with a deep low-volume valley = the single prints the
      market "flew through"),
  3. HOLDS the new value (closes at the new extreme — it trended, didn't come back).

Detected from the bars, NOT from Sierra's `profile_shape` label — Sierra marked
06-16/06-17 as "b" (a single distribution) and missed them. The narrow-IB test is what
separates a real DD (06-16/17, IB ~25) from a one-sided Variation on a wide IB (06-10,
IB ~70); the close-at-extreme test separates it from a day that built two distributions
but came back to the middle (06-09/06-15). Pure function; flag-gated when wired.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from collections import defaultdict


def _g(bar: Any, *keys: str):
    if isinstance(bar, dict):
        for k in keys:
            v = bar.get(k)
            if v is not None:
                return v
        return None
    for k in keys:
        v = getattr(bar, k, None)
        if v is not None:
            return v
    return None


def detect_double_distribution(
    bars: List[Any],
    ib_width: Optional[float],
    ib_median: Optional[float],
    *,
    bucket: float = 2.0,
    narrow_frac: float = 0.7,     # IB is "narrow" if <= narrow_frac * the recent median IB
    second_min: float = 0.45,     # the 2nd distribution must be >= 45% of the 1st (substantial, not a tail)
    neck_min: float = 0.60,       # the valley between them must be a deep single-print gap
    sep_min: float = 12.0,        # the two distributions are at least this far apart (points)
    close_extreme: float = 0.20,  # closed within 20% of an extreme (new value held)
) -> Dict[str, Any]:
    """Return {detected, narrow_ib, bimodal, neck, second_ratio, close_pos}. All RELATIVE."""
    out: Dict[str, Any] = {"detected": False, "narrow_ib": False, "bimodal": False,
                           "neck": 0.0, "second_ratio": 0.0, "close_pos": None}
    if not bars or len(bars) < 12:
        return out
    highs = [x for x in (_g(b, "h", "high") for b in bars) if x is not None]
    lows = [x for x in (_g(b, "l", "low") for b in bars) if x is not None]
    closes = [x for x in (_g(b, "c", "close") for b in bars) if x is not None]
    if not highs or not lows or not closes:
        return out
    sh, sl = max(highs), min(lows)
    rng = sh - sl
    if rng <= 0:
        return out
    cpos = (closes[-1] - sl) / rng
    out["close_pos"] = round(cpos, 3)

    # 1) NARROW IB — relative to the recent median (DD criterion 2: low early confidence).
    narrow = bool(ib_width is not None and ib_median and ib_width <= narrow_frac * ib_median)
    out["narrow_ib"] = narrow

    # 2) BIMODAL volume-by-price with a deep NECK (criteria 3+4: two distributions + single prints).
    vol: Dict[float, float] = defaultdict(float)
    for b in bars:
        bh, bl, bc = _g(b, "h", "high"), _g(b, "l", "low"), _g(b, "c", "close")
        if None in (bh, bl, bc):
            continue
        vol[round(((bh + bl + bc) / 3.0) / bucket) * bucket] += (_g(b, "v", "volume") or 0)
    prices = sorted(vol)
    if len(prices) < 3:
        return out
    v = [vol[p] for p in prices]
    sm = [(v[max(0, i - 1)] + v[i] + v[min(len(v) - 1, i + 1)]) / 3 for i in range(len(v))]
    i1 = max(range(len(sm)), key=lambda i: sm[i])                       # the dominant POC
    # The 2nd distribution must be a DISTINCT value area = a genuine LOCAL MAXIMUM (its own POC),
    # >= sep_min away — not merely the highest bucket on the SLOPE of one elongated distribution.
    # This is what keeps a Trend_Normal (single elongated profile that leaves single-prints along
    # the way) from being mistaken for a Double-Distribution (Michael 2026-06-20: "neck = a band
    # between 2 POC, not just single-print count").
    def _is_local_max(i):
        return (i == 0 or sm[i] >= sm[i - 1]) and (i == len(sm) - 1 or sm[i] >= sm[i + 1])
    far = [i for i in range(len(sm)) if abs(prices[i] - prices[i1]) >= sep_min and _is_local_max(i)]
    if not far:
        return out
    i2 = max(far, key=lambda i: sm[i])                                  # the 2nd POC (>= sep away)
    lo, hi = sorted([i1, i2])
    valley = min(sm[lo:hi + 1])
    second = sm[i2] / sm[i1] if sm[i1] else 0.0
    neck = 1 - valley / min(sm[i1], sm[i2]) if min(sm[i1], sm[i2]) else 0.0
    out["neck"], out["second_ratio"] = round(neck, 3), round(second, 3)
    bimodal = second >= second_min and neck >= neck_min
    out["bimodal"] = bimodal

    # 3) NEW VALUE HELD — closed at an extreme (criterion 5: trended, didn't come back).
    held = cpos <= close_extreme or cpos >= (1 - close_extreme)

    out["detected"] = bool(narrow and bimodal and held)
    return out
