"""classifier_core — pure-function core of the 7-type day-type classifier.

Extracted from classify_replay (daytype_classify_routes.py) so it can be
called from both the API endpoint (historical replay) and the live engine
(per-bar promotion in main.py::_day_type_on_bar).

NO DB reads, NO I/O, NO side effects. All inputs are passed in.
"""
from __future__ import annotations

import os
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

    # ── S1_IB_SANITY_V1 (default OFF; N1a/N1b diagnosis 2026-07-17 —
    #    docs/handoff/N1B_TRANSITIONS_DIAGNOSIS_2026-07-17.md RC#1): the
    #    Sierra-exported IB is sometimes a stale pre-open snapshot that never
    #    re-bases to the true 09:30 ET cash-session first hour (proven
    #    2026-07-15: exported ib 7591.75-7619.0 vs the true first-12-bars
    #    7601.25-7626.25, off 7.25/9.5pt — this fed a phantom UP side and
    #    forced a false Neutral mid-session while the real day was a clean
    #    Variation-DOWN leg). When enabled and >=12 RTH bars exist, sanity
    #    the passed Sierra ib_high/ib_low against the bars' own first-12-bar
    #    extremes. Inconsistent = either (a) the bars already poke >2 ticks
    #    beyond the claimed IB — impossible if the IB truly were the first
    #    hour, since by definition nothing in the first hour can exceed its
    #    own extremes — or (b) the claimed IB is >2pt wider than the bars on
    #    either side — the stale pre-open-window symptom. On inconsistency,
    #    fall back to the bars-derived IB (validation of already-ingested
    #    bars, Rule-1-compatible — the no-Sierra bars fallback already exists
    #    at relative_features.py:219-225; this is not synthesizing a new
    #    source) and tag ib_source so callers/UI can see the substitution.
    ib_source = "sierra_tpo"
    if (os.getenv("S1_IB_SANITY_V1", "").lower() in ("1", "true", "yes")
            and n >= 12 and ib_high is not None and ib_low is not None):
        _tick = 0.25
        _b12 = bars[:12]
        _b12_h = max(b.get("h", b.get("high", 0)) or 0 for b in _b12)
        _b12_l = min(b.get("l", b.get("low", 0)) or 0 for b in _b12)
        _bars_poke = (_b12_h - ib_high > 2 * _tick) or (ib_low - _b12_l > 2 * _tick)
        _ib_too_wide = (ib_high - _b12_h > 2.0) or (_b12_l - ib_low > 2.0)
        if (_bars_poke or _ib_too_wide) and _b12_h > _b12_l:
            ib_high, ib_low = _b12_h, _b12_l
            ib_source = "bars_fallback_sierra_inconsistent"

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

    # ── P2.1-2 (DEV_PLAN 02.08 §P2): delta/CVD features for classifier ──
    # Wire delta_confirms_extension (R5) and cvd_directionality (R6) from the
    # live cumulative_delta export. Computed always (pure + cheap); consumed
    # by classify() only when DELTA_FEATURES_V1 is ON → byte-identical when off.
    feat["delta_confirms_ext"] = None
    feat["cvd_directionality"] = None
    if os.getenv("DELTA_FEATURES_V1", "0").lower() in ("1", "true", "yes"):
        try:
            from backend.v9.systems.delta_features import (
                delta_confirms_extension, cvd_directionality,
            )
            import json as _dj
            from pathlib import Path as _dP
            _delta_path = _dP(os.path.expanduser(
                "~/SierraChart_Data/v9_export/cumulative_delta.json"))
            if _delta_path.exists():
                _dexport = _dj.loads(_delta_path.read_text().strip() or "{}")
                _dpts = _dexport.get("points", [])
                feat["cvd_directionality"] = cvd_directionality(_dpts)
                # delta confirms extension only when we have a break direction
                if _abrk:
                    feat["delta_confirms_ext"] = delta_confirms_extension(_dpts, _abrk)
        except Exception:
            pass  # fail-open: missing delta = None fields (Rule 1)

    # ── N3 (MULTIDAY_CONTEXT_V1 phase D): open_vs_balance7 + migration veto ──
    # Where today opens vs the 7-day composite → confidence adjustment +
    # veto sell-against-migrating-value (21.07 case: −$209 shorting upward-
    # migrating value). Computed always when flag ON; consumed by classify()
    # through feat dict → byte-identical when OFF.
    feat["open_vs_balance7"] = None
    feat["multiday_migration"] = None
    feat["multiday_veto_dir"] = None
    if os.getenv("MULTIDAY_CONTEXT_V1", "0").lower() in ("1", "true", "yes"):
        try:
            from backend.v9.systems.multiday_profile import build_context
            from backend.v9.db.read import read_all as _md_read
            # Load last 7 trading days' bars
            _md_sessions = []
            _md_rows = _md_read(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min_woodies "
                "WHERE (ts AT TIME ZONE 'America/New_York')::date < "
                "(now() AT TIME ZONE 'America/New_York')::date "
                "AND (ts AT TIME ZONE 'America/New_York')::date >= "
                "((now() AT TIME ZONE 'America/New_York')::date - interval '10 days') "
                "ORDER BY ts", {},
            )
            if _md_rows:
                from collections import defaultdict as _dd
                _by_day = _dd(list)
                for r in _md_rows:
                    d = r["ts"].date() if hasattr(r["ts"], "date") else str(r["ts"])[:10]
                    _by_day[d].append({
                        "o": float(r["open"]), "h": float(r["high"]),
                        "l": float(r["low"]), "c": float(r["close"]),
                        "vol": int(r["volume"] or 0),
                    })
                _md_sessions = [_by_day[d] for d in sorted(_by_day) if len(_by_day[d]) >= 12]

            if _md_sessions and open_price:
                _md_ctx = build_context(_md_sessions, today_open=open_price)
                feat["open_vs_balance7"] = _md_ctx.get("open_location")
                _mig = _md_ctx.get("value_migration", {})
                feat["multiday_migration"] = _mig.get("direction")
                # Veto: don't sell against upward-migrating value / don't buy
                # against downward-migrating value
                if _mig.get("direction") == "UP":
                    feat["multiday_veto_dir"] = "SHORT"  # don't sell against UP migration
                elif _mig.get("direction") == "DOWN":
                    feat["multiday_veto_dir"] = "LONG"   # don't buy against DOWN migration
        except Exception:
            pass  # fail-open

    result = classify(feat, plan, is_eod=is_eod)
    # Propagate structural features for binary classifier event detection
    result["accepted_break"] = feat.get("accepted_break")
    result["accepted_break_ref"] = feat.get("accepted_break_ref")
    result["failed_break"] = feat.get("failed_break")
    result["dd_second_dist"] = feat.get("dd_second_dist")
    result["returned_through_open"] = feat.get("returned_through_open")
    result["ib_source"] = ib_source
    result["ib_high_used"] = ib_high      # N1 observability: the IB the classifier ACTUALLY used
    result["ib_low_used"] = ib_low        # (== Sierra unless the S1_IB_SANITY_V1 fallback replaced it)
    result["measured"] = {
        "sides": feat["sides"], "rib": feat["rib"], "one_tf": feat["one_tf"],
        "close_pos": feat["close_pos"], "cvd_pos": feat["cvd_pos"],
        "ib_width": feat["ib_width"], "vol_ratio": feat["vol_ratio"],
        # P1-6 observability — emitted per bar regardless of the flag (ACCEPT criterion)
        "va_overlap_pct": feat["va_overlap_pct"], "value_migration": feat["value_migration"],
        # P2-9/11 observability (Michael 07-13)
        "profile_imbalance": feat["profile_imbalance"], "va_rule": feat["va_rule"],
        # P2.1-2 delta features (DEV_PLAN 02.08)
        "cvd_directionality": feat.get("cvd_directionality"),
        "delta_confirms_ext": feat.get("delta_confirms_ext"),
        # N3 multiday context (phase D)
        "open_vs_balance7": feat.get("open_vs_balance7"),
        "multiday_migration": feat.get("multiday_migration"),
        "multiday_veto_dir": feat.get("multiday_veto_dir"),
    }
    return result


def state_row_extras(last_cls_result: Optional[Dict[str, Any]], today_iso: str) -> Dict[str, Any]:
    """N1 RC#4 (2026-07-17, docs/handoff/N1B_TRANSITIONS_DIAGNOSIS_2026-07-17.md §5.5):
    map the canonical classify_session result onto the ADDITIVE v9_day_type_state
    observability columns (migration 022): direction / reason / sides / rib.

    `direction` combines the plan STRATEGY string with the day's leg-direction read so
    "Variation-DOWN" is finally representable: e.g. "with_extension(DOWN)". Strategy
    without a directional read stays bare ("fade_both"); a leg read without a strategy
    (shouldn't happen) would be the bare "UP"/"DOWN".

    Rule 1 (honest failure): when the result is absent, or stamped with a DIFFERENT
    session_date than today (stale cross-session app.state), every field is None —
    the columns must never carry yesterday's read as if it were today's.
    Pure function, no I/O — unit-tested without a DB.
    """
    out: Dict[str, Any] = {"direction": None, "reason": None, "sides": None, "rib": None}
    r = last_cls_result or {}
    if not r or r.get("session_date") != today_iso:
        return out
    strategy = r.get("direction")
    bias = r.get("dir_bias")
    if strategy and bias:
        out["direction"] = f"{strategy}({bias})"
    else:
        out["direction"] = strategy or bias or None
    out["reason"] = r.get("reason") or None
    m = r.get("measured") or {}
    out["sides"] = m.get("sides")
    out["rib"] = m.get("rib")
    return out
