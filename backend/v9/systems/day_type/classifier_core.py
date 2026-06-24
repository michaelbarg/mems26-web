"""classifier_core — pure-function core of the 7-type day-type classifier.

Extracted from classify_replay (daytype_classify_routes.py) so it can be
called from both the API endpoint (historical replay) and the live engine
(per-bar promotion in main.py::_day_type_on_bar).

NO DB reads, NO I/O, NO side effects. All inputs are passed in.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.v9.systems.day_type.relative_features import compute_relative_features
from backend.v9.systems.day_type.cvd_features import compute_cvd_features
from backend.v9.systems.day_type.context_features import ib_width_percentile
from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type
from backend.v9.systems.day_type.dd_features import detect_double_distribution
from backend.v9.systems.day_type.daytype_classifier import classify, load_plan


def classify_session(
    *,
    bars: List[Dict],
    ib_high: float,
    ib_low: float,
    open_price: Optional[float] = None,
    ib_width_hist: Optional[List[float]] = None,
    profile_shape: Optional[str] = None,
    vol_ratio: Optional[float] = None,
    prior_vah: Optional[float] = None,
    prior_val: Optional[float] = None,
    pdh: Optional[float] = None,
    pdl: Optional[float] = None,
    poc_now: Optional[float] = None,
    poc_at_ib: Optional[float] = None,
    is_eod: bool = False,
) -> Dict[str, Any]:
    """Classify the current session from in-memory data. Pure function.

    Args:
        bars: RTH 5-min bars [{o,h,l,c,v,cum(optional)}], ordered by time.
        ib_high/ib_low: locked IB (Sierra source of truth).
        open_price: first RTH trade (defaults to bars[0]["o"]).
        ib_width_hist: list of prior days' IB widths for percentile calc.
        profile_shape: Sierra TPO profile shape ("D"/"b"/"P"/etc).
        vol_ratio: session_volume / median_daily_volume (None if unavailable).
        prior_vah/val/pdh/pdl: previous day levels for opening_type.
        poc_now/poc_at_ib: POC migration (current vs at IB lock).
        is_eod: True on last bar → forces terminal type.

    Returns:
        {day_type, status, direction, reason, invalidated, ...}
    """
    if not bars:
        return {"day_type": "FORMING", "status": "FORMING", "direction": None,
                "reason": "no bars", "invalidated": False}

    n = len(bars)
    if open_price is None:
        open_price = bars[0].get("o", bars[0].get("open", 0))

    ibw = ib_high - ib_low
    ib_hist = ib_width_hist or []
    ibp = ib_width_percentile(ibw, ib_hist)

    # IB median for dd_features narrow-IB check
    sorted_hist = sorted(ib_hist) if ib_hist else []
    ib_median = sorted_hist[len(sorted_hist) // 2] if sorted_hist else None

    # Opening type from first 6 bars
    op = detect_opening_type(
        bars[:min(6, n)], open_price,
        prior_vah=prior_vah, prior_val=prior_val,
        pdh=pdh, pdl=pdl,
    )
    opening_type = op.get("opening_type")

    # POC drift
    from backend.v9.systems.day_type.context_features import poc_drift, open_location
    pocdrift = poc_drift(poc_now, poc_at_ib, ibw)
    open_loc = open_location(open_price, prior_vah, prior_val, pdh, pdl)

    # Double-distribution detection
    dd_bar = detect_double_distribution(bars, ibw, ib_median)
    sierra_dd = (profile_shape or "").strip() in ("B", "DD")
    dd_detected = sierra_dd or dd_bar["detected"]

    # CVD from cumulative_delta field on bars
    cum_all = [b.get("cum", b.get("cum_delta", b.get("cumulative_delta"))) for b in bars]

    plan = load_plan()

    # Compute features on full bar set
    rf = compute_relative_features(bars, ib_high, ib_low, open_price)
    cvd = compute_cvd_features([c for c in cum_all if c is not None])

    # Session range for Nontrend width-floor (FIX A)
    _sr = None
    if rf.session_high is not None and rf.session_low is not None:
        _sr = round(rf.session_high - rf.session_low, 2)

    feat = {
        "returned_through_open": rf.returned_through_open,
        "n_bars": n,
        "sides": rf.sides,
        "rib": rf.rib,
        "one_tf": rf.one_tf,
        "cvd_pos": cvd["cvd_pos"],
        "close_pos": rf.close_pos,
        "ib_pctile": ibp["pctile"],
        "ib_width": round(ibw, 2),
        "ib_narrow": bool(ib_median and ib_median > 0 and ibw <= 0.7 * ib_median),
        "vol_ratio": vol_ratio,
        "opening_type": opening_type,
        "open_location": open_loc,
        "poc_drift": pocdrift,
        "dd_second_dist": dd_detected,
        "session_range": _sr,
    }

    result = classify(feat, plan, is_eod=is_eod)
    result["measured"] = {
        "sides": feat["sides"], "rib": feat["rib"], "one_tf": feat["one_tf"],
        "close_pos": feat["close_pos"], "cvd_pos": feat["cvd_pos"],
        "ib_width": feat["ib_width"], "vol_ratio": feat["vol_ratio"],
    }
    return result
