"""T-466 STRUCTURE_BEFORE_LABEL_V1 — the pure predicate the gateway uses (24.09).

A ONE-SIDED IB extension: the session has pushed at least max(2 pts, 10% of the IB width) beyond
one IB edge while the other edge was never exceeded by more than a tick. That is the structural
definition of a Variation day (same as var_cont.detect's one_sided) and it exists 2-3 bars before the
day-type LABEL says so — and unlike the label it does not flip-flop.
"""
from __future__ import annotations

from typing import Optional

TICK = 0.25
NON_TREND_LABELS = ("", "UNKNOWN", "None", "Normal", "Neutral_Center", "Neutral_Extreme", "Nontrend", "Nonconviction")


def one_sided_extension(ib_high: float, ib_low: float, session_high: float, session_low: float,
                        min_frac: float = 0.10, min_pts: float = 2.0, other_tol: float = TICK) -> Optional[str]:
    """'LONG' / 'SHORT' when the session shows a one-sided extension beyond the completed IB, else None."""
    try:
        ibh, ibl, sh, sl = float(ib_high or 0), float(ib_low or 0), float(session_high or 0), float(session_low or 0)
    except (TypeError, ValueError):
        return None
    if not (ibh > ibl > 0 and sh > 0 and sl > 0):
        return None
    need = max(min_pts, min_frac * (ibh - ibl))
    up = sh - ibh
    dn = ibl - sl
    if up >= need and dn <= other_tol:
        return "LONG"
    if dn >= need and up <= other_tol:
        return "SHORT"
    return None


def effective_day_type(label: Optional[str], ext: Optional[str]) -> str:
    """The day type the tree should see: Variation when a one-sided extension exists and the label is
    non-trend/unknown; otherwise the label itself (Trend_* and Variation labels are never overridden)."""
    lab = str(label or "").strip()
    if ext and lab in NON_TREND_LABELS:
        return "Variation"
    return lab
