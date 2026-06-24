"""context_features.py — RELATIVE context/structure features for S1.

Pure functions, no absolute thresholds (bands live in the YAML / calibration):

  ib_width_percentile : where today's IB ranks vs trailing history → NARROW/NORMAL/WIDE
                        (the relative IB signal; the absolute seed is only a fallback)
  open_location       : open vs prior FULL-session VA & PDH/PDL
                        → in_value | out_value_in_range | out_of_range
  poc_drift           : (poc_now - poc_at_IB_close) measured in IB-widths (signed)
Not wired live. (second_distribution removed 2026-06-20 — dead POC-jump proxy, superseded by
backend/v9/systems/day_type/dd_features.py which detects DD from the bars: narrow IB + 2 POCs + neck.)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def ib_width_percentile(
    current_ib: Optional[float],
    history: List[float],
    *,
    p_lo: float = 0.33,
    p_hi: float = 0.67,
    min_history: int = 5,
) -> Dict[str, Any]:
    """Rank current IB width vs trailing history. <min_history rows → UNKNOWN (use seed)."""
    if current_ib is None or current_ib <= 0:
        return {"pctile": None, "klass": "UNKNOWN", "n": 0}
    hist = sorted(h for h in history if h is not None and h > 0)
    n = len(hist)
    if n < min_history:
        return {"pctile": None, "klass": "UNKNOWN", "n": n}
    below = sum(1 for h in hist if h < current_ib)
    pctile = below / n
    if pctile <= p_lo:
        klass = "NARROW"
    elif pctile >= p_hi:
        klass = "WIDE"
    else:
        klass = "NORMAL"
    return {"pctile": round(pctile, 3), "klass": klass, "n": n}


def open_location(
    open_price: Optional[float],
    prior_vah: Optional[float],
    prior_val: Optional[float],
    pdh: Optional[float],
    pdl: Optional[float],
) -> str:
    """Classify where the session opened relative to yesterday's value & range."""
    if open_price is None:
        return "UNKNOWN"
    if prior_val is not None and prior_vah is not None and prior_val <= open_price <= prior_vah:
        return "in_value"
    if pdh is not None and pdl is not None:
        return "out_value_in_range" if pdl <= open_price <= pdh else "out_of_range"
    return "UNKNOWN"


def poc_drift(
    poc_now: Optional[float],
    poc_at_ib: Optional[float],
    ib_width: Optional[float],
) -> Optional[float]:
    """Signed POC migration since IB close, in IB-width units (relative)."""
    if poc_now is None or poc_at_ib is None or not ib_width or ib_width <= 0:
        return None
    return round((poc_now - poc_at_ib) / ib_width, 3)
