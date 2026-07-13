"""classifier_core — pure-function core of the 7-type day-type classifier.

Extracted from classify_replay (daytype_classify_routes.py) so it can be
called from both the API endpoint (historical replay) and the live engine
(per-bar promotion in main.py::_day_type_on_bar).

NO DB reads, NO I/O, NO side effects. All inputs are passed in.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.v9.systems.day_type.relative_features import compute_relative_features, level_acceptance
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

    # P1-7 (Dalton p.27): neck-refill invalidation — recent closes back inside
    # the single-print neck mean the 2nd distribution is rejected. Computed
    # always (cheap, pure); classify() consumes it only under S1_DD_INVALIDATION_V1.
    from backend.v9.systems.day_type.dd_features import neck_refilled
    dd_refilled = bool(dd_bar["detected"] and neck_refilled(
        bars, dd_bar.get("neck_lo"), dd_bar.get("neck_hi")))

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

    # ── P0-1 v2 (Michael 2026-07-12; Dalton pp.278-293): acceptance at ALL reference
    #    levels, not just the IB. References in OUTERMOST-first priority: prior-day
    #    range (PDH/PDL — the balance bracket; a gap-and-go holds beyond it), then the
    #    prior value-area edge (VAH/VAL), then the IB edge. Each ref gets the same
    #    acceptance test (≥2 consecutive closes + volume-accept beyond); a ref that was
    #    accepted but whose last closes are back INSIDE = rejection (failed breakout).
    #    Pure + cheap → computed always; classify() consumes accepted_break/failed_break
    #    only under S1_ACCEPTANCE_RECLASS_V1 → byte-identical when the flag is unset.
    _refs = [(nm, lv, sd) for nm, lv, sd in (
        ("PDH", pdh, "UP"), ("PDL", pdl, "DOWN"),
        ("prior_VA", prior_vah, "UP"), ("prior_VA", prior_val, "DOWN"),
        ("IB", ib_high if ibw > 0 else None, "UP"), ("IB", ib_low if ibw > 0 else None, "DOWN"),
    ) if lv is not None]
    _acc_up = _acc_dn = _failed_ref = None
    for _nm, _lv, _sd in _refs:
        _a = level_acceptance(bars, _lv, _sd)
        if _a["accepted"]:
            if _sd == "UP" and _acc_up is None:
                _acc_up = _nm
            elif _sd == "DOWN" and _acc_dn is None:
                _acc_dn = _nm
        elif _a["rejected_after_accept"] and _failed_ref is None:
            _failed_ref = _nm
    if _acc_up and _acc_dn:            # accepted BOTH ways = two-sided, no directional reclass
        _abrk, _aref = None, None
    elif _acc_up or _acc_dn:
        _abrk = "UP" if _acc_up else "DOWN"
        _aref = _acc_up or _acc_dn
    else:
        _abrk, _aref = None, None
    # failed_break only when NOTHING is currently accepted (revert, per the spec)
    _fbrk = _failed_ref is not None and _abrk is None

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
        # ── P0 wiring (Michael 2026-07-08 + v2 2026-07-12, Dalton doctrine) — ADDITIVE.
        #    Consumed only when the P0 flags are ON; classify() ignores these keys
        #    otherwise → byte-identical when unset. accepted_break now merges ALL
        #    reference acceptances (PDH/PDL, prior VA, IB) via level_acceptance —
        #    including accept-then-reject (failed_break), which the v1 IB-only holds
        #    could not express. open_dir feeds P0-2; ext_*_bars feed P0-3 confidence.
        "accepted_break": _abrk,
        "accepted_break_ref": _aref,
        "failed_break": _fbrk,
        "failed_break_ref": _failed_ref if _fbrk else None,
        "open_dir": op.get("direction"),
        "ext_up_bars": rf.ext_up_bars,
        "ext_dn_bars": rf.ext_dn_bars,
        "dd_neck_refilled": dd_refilled,
        "dd_neck_zone": (dd_bar.get("neck_lo"), dd_bar.get("neck_hi")),
        # P1-4/P1-5 (Dalton p.25): stair-step control — consumed only when
        # S1_TREND_CONTROL_V1 is ON; classify() ignores otherwise.
        "stair_steps_up": rf.stair_steps_up,
        "stair_steps_dn": rf.stair_steps_dn,
    }

    # ── P1-6 (Michael 2026-07-12; Dalton pp.49, 55): value migration — the developing
    #    70% value-area vs yesterday's. Trend = migrating value; overlap = balance.
    #    Pure + cheap → computed always; classify() consumes only under
    #    S1_VALUE_MIGRATION_V1 → byte-identical when unset. ──
    from backend.v9.systems.day_type.value_migration import value_migration as _vm
    _vmres = _vm(bars, prior_vah, prior_val)
    feat["va_overlap_pct"] = _vmres["va_overlap_pct"]
    feat["value_migration"] = _vmres["value_migration"]
    feat["dev_poc"] = _vmres["dev_poc"]

    # ── P2-9/11 (Michael 2026-07-13): volume-profile imbalance (TPO-count proxy,
    #    feeds confidence only under S1_TPO_COUNT_V1) + VA-rule read (emitted for
    #    briefing/UI; no gate yet). Pure + cheap, computed always. ──
    from backend.v9.systems.day_type.day_context_extras import profile_imbalance, va_rule_read
    feat["profile_imbalance"] = profile_imbalance(bars)
    feat["va_rule"] = va_rule_read(bars, prior_vah, prior_val, open_price)

    result = classify(feat, plan, is_eod=is_eod)
    result["measured"] = {
        "sides": feat["sides"], "rib": feat["rib"], "one_tf": feat["one_tf"],
        "close_pos": feat["close_pos"], "cvd_pos": feat["cvd_pos"],
        "ib_width": feat["ib_width"], "vol_ratio": feat["vol_ratio"],
        # P1-6 observability — emitted per bar regardless of the flag (ACCEPT criterion)
        "va_overlap_pct": feat["va_overlap_pct"], "value_migration": feat["value_migration"],
        # P2-9/11 observability (Michael 07-13)
        "profile_imbalance": feat["profile_imbalance"], "va_rule": feat["va_rule"],
    }
    return result
