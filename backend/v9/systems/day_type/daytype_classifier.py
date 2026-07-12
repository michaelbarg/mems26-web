"""daytype_classifier.py — RELATIVE day-type classifier (S1, reads the dynamic table).

Combines the computed relative features into a day-type, using the thresholds +
precedence tree from config/daytype_trading_plan.yaml. Continuous: call each bar.
Emits FORMING (don't force a type) and INVALIDATED per Michael's closed spec (A5/A6).
Returns the day-type AND its firing `direction` (read from the table).

Pure logic; flag-gated when wired into the live engine (no behavior change yet).
The classifier reaches ALL 7 types (the old matrix could only produce 3).
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

try:
    import yaml  # PyYAML
except Exception:  # pragma: no cover
    yaml = None

_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "config", "daytype_trading_plan.yaml"))

_PLAN_CACHE: Optional[Dict[str, Any]] = None


def load_plan(path: str = CONFIG_PATH) -> Dict[str, Any]:
    global _PLAN_CACHE
    if _PLAN_CACHE is not None and path == CONFIG_PATH:
        return _PLAN_CACHE
    if yaml is None:
        raise RuntimeError("PyYAML not available")
    with open(path, "r", encoding="utf-8") as fh:
        plan = yaml.safe_load(fh)
    if path == CONFIG_PATH:
        _PLAN_CACHE = plan
    return plan


def _direction(plan: Dict[str, Any], day_type: str) -> Optional[str]:
    return (plan.get("day_types", {}).get(day_type) or {}).get("direction")


def _provisional_from_open(feat: Dict[str, Any], plan: Dict[str, Any], out) -> Optional[Dict[str, Any]]:
    """P0-2 (flag S1_COMMITTED_PROVISIONAL_V1) — committed provisional day-type from the OPEN.

    Dalton pp.63-74 (§3.1 table): the open foreshadows the day; conviction is readable in the
    first minutes. By 30 min we COMMIT a provisional (not bare FORMING) from
    {opening_type × open_location}. `one_tf` needs >=2 periods (>=12 bars) so it is None at 30 min
    → provisional direction comes from the opening detector's `open_dir`. Always returns a
    provisional (never None) so no session sits bare-FORMING past 30 min (ruling D1)."""
    ot = feat.get("opening_type")
    loc = feat.get("open_location")
    od = feat.get("open_dir")
    d = od if od in ("UP", "DOWN") else (feat.get("one_tf") if feat.get("one_tf") in ("UP", "DOWN") else None)

    def p(dt: str, why: str) -> Dict[str, Any]:
        tag = f"[{ot or 'no-open'}" + (f"/{loc}" if loc and loc != "UNKNOWN" else "") + "]"
        return out(dt, "PROVISIONAL", f"@30m provisional {tag} -> {why}",
                   provisional_from_open=True, prov_dir=d)

    if ot in ("OPEN_DRIVE", "OPEN_TEST_DRIVE"):
        if loc == "out_of_range":
            return p("Trend_Normal", "drive + open out of balance -> Trend (pp.63-65,84)")
        return p("Normal_Variation", "drive in range -> Variation/Trend watch (pp.65-67)")
    if ot == "OPEN_AUCTION_OUT":
        return p("Normal_Variation", "auction out of balance -> DD/Trend watch (pp.70-71)")
    if ot == "OPEN_REJECTION_REVERSE":
        return p("Neutral_Center", "rejection-reverse -> two-sided; Trend unlikely (p.68)")
    if ot == "OPEN_AUCTION_IN":
        return p("Normal", "auction in range -> rotational; big day unlikely (p.71)")
    return p("Normal", "open unresolved -> provisional Normal-leaning")


def _confidence(feat: Dict[str, Any], day_type: str, direction: Optional[str], cl: Dict[str, Any]) -> float:
    """P0-3 (flag S1_CONFIDENCE_V2) — ONE canonical confidence in [0,1] = fraction of the
    day's evidence that ALIGNS with its directional/balance read. Dalton conviction continuum
    (p.29); 3-1 confluence (pp.273-275). Uses the evidence available in `feat` today
    (open type, one_tf, RE persistence, CVD, close_pos, rib, open-held, DD/one-sided); tails,
    TPO-count and elongation are wired later (doctrine P1/P2)."""
    if day_type == "FORMING":
        return 0.0                    # FORMING = no classification yet = no conviction (honest)
    one_tf = feat.get("one_tf")
    cp = feat.get("close_pos")
    cvd = feat.get("cvd_pos")
    rib = feat.get("rib")
    sides = feat.get("sides", 0) or 0
    ce_hi, ce_lo = cl["close_extreme_hi"], cl["close_extreme_lo"]
    cvd_lo, cvd_hi = cl["cvd_dir_short"], cl["cvd_dir_long"]
    cc_lo, cc_hi = cl["close_center"]
    rib_tn = cl["rib_trend_min"]
    # the day's directional bias: one_tf, else the reclass break dir, else a close at an extreme
    d = one_tf if one_tf in ("UP", "DOWN") else feat.get("break_dir")
    if d not in ("UP", "DOWN") and cp is not None:
        d = "UP" if cp >= ce_hi else ("DOWN" if cp <= ce_lo else None)
    # FIXED denominator = the FULL evidence checklist (fraction of ALL evidence that aligns, per
    # doctrine p.29 / pp.273-275). Missing/None evidence counts as NOT aligned → early/degenerate
    # bars get a LOW confidence (not a misleading 1.0 from 1-of-1 applicable). Rises as evidence accrues.
    if d in ("UP", "DOWN"):
        ub, db = feat.get("ext_up_bars"), feat.get("ext_dn_bars")
        ot = feat.get("opening_type")
        ev = [
            one_tf == d,                                                                # one-timeframe
            cp is not None and ((d == "UP" and cp >= ce_hi) or (d == "DOWN" and cp <= ce_lo)),  # close at extreme
            cvd is not None and ((d == "UP" and cvd >= cvd_hi) or (d == "DOWN" and cvd <= cvd_lo)),  # CVD aligned
            (d == "UP" and (ub or 0) >= 2) or (d == "DOWN" and (db or 0) >= 2),          # RE persistence
            rib is not None and rib >= rib_tn,                                          # trend-grade range
            ot in ("OPEN_DRIVE", "OPEN_TEST_DRIVE"),                                     # drive open
            not bool(feat.get("returned_through_open")),                                # open held
            bool(feat.get("dd_second_dist")) or sides == 1,                             # one-sided / DD
        ]
    else:
        # non-directional (Neutral_Center / Normal / Nontrend): how cleanly the balance holds
        ev = [
            cp is not None and cc_lo <= cp <= cc_hi,                                     # centered close
            sides in (0, 2),                                                            # balanced sides
            (rib is not None and rib <= cl["rib_normal_max"]) or sides == 2,            # contained or two-sided
        ]
    return round(sum(1 for x in ev if x) / len(ev), 2)


def classify(feat: Dict[str, Any], plan: Optional[Dict[str, Any]] = None, *, is_eod: bool = False) -> Dict[str, Any]:
    """Locked S1 table (Michael 2026-06-20), first-match-wins state machine.

    feat keys (all relative): returned_through_open, n_bars, sides, rib, one_tf, cvd_pos,
      close_pos, vol_ratio, dd_second_dist, ib_narrow (bool, IB<=0.7×median) / ib_width
      (fallback), tails_both (confirm), close_at_poc (confirm).
    Returns {day_type, status, direction, reason, invalidated}. status ∈
      CLASSIFIED | PROVISIONAL | FORMING.  `invalidated`=True is the priority-0 overlay
      (returned through the opening range → exit + reclassify). `is_eod` forces a terminal
      type — no day ends FORMING/PROVISIONAL.
    """
    plan = plan or load_plan()
    cl = plan["classify"]
    rib_tn = cl["rib_trend_min"]            # 2.5  — Trend floor
    rib_nt = cl["rib_nontrend_max"]          # 1.15 — truly-compressed ceiling (Nontrend)
    rib_norm = cl["rib_normal_max"]          # 1.30 — contained ceiling (Normal)
    cvd_lo, cvd_hi = cl["cvd_dir_short"], cl["cvd_dir_long"]   # 0.25 / 0.75 (CVD confirm)
    ce_hi, ce_lo = cl["close_extreme_hi"], cl["close_extreme_lo"]  # 0.85 / 0.15
    cc_lo, cc_hi = cl["close_center"]        # 0.33 / 0.67
    vol_low = cl.get("vol_low_ratio", 0.5)
    ib_lock_bars = int(cl.get("ib_lock_minutes", 60) / 5)    # 12 bars = 60 min = IB locks

    oi = bool(feat.get("returned_through_open"))     # priority-0 INVALIDATED overlay
    sides = feat.get("sides", 0)
    rib = feat.get("rib")
    cp = feat.get("close_pos")
    cvd_pos = feat.get("cvd_pos")
    vr = feat.get("vol_ratio")
    n = feat.get("n_bars", 0)
    cvd_dir = cvd_pos is not None and (cvd_pos >= cvd_hi or cvd_pos <= cvd_lo)

    # ── P0 flags (Michael 2026-07-08, Dalton doctrine). ALL default OFF → byte-identical when unset. ──
    _reclass_on = os.environ.get("S1_ACCEPTANCE_RECLASS_V1", "0").lower() in ("1", "true", "yes")
    _conf_on = os.environ.get("S1_CONFIDENCE_V2", "0").lower() in ("1", "true", "yes")
    _failed_break = _reclass_on and bool(feat.get("failed_break"))

    def out(dt: str, status: str, reason: str, **extra) -> Dict[str, Any]:
        d = {"day_type": dt, "status": status, "direction": _direction(plan, dt),
             "reason": reason, "invalidated": oi, "opening_invalidated": oi}
        if _failed_break:                       # P0-1: a prior accepted break returned inside → rejection
            d["failed_breakout"] = True
        d.update(extra)
        if _conf_on:                            # P0-3: one canonical confidence on every output
            d["confidence"] = _confidence(feat, dt, d.get("direction"), cl)
        return d

    # ── Priority 0 = INVALIDATED overlay: `invalidated`/`oi` above. A return through the
    #    opening range exits the trade + forces re-classification (oi blocks Trend below;
    #    the day_type re-forms). Not a terminal type, so the day keeps developing. ──

    # ── P0-1 acceptance-driven prompt reclassification (Michael 2026-07-08; Dalton pp.37-38,288-292) ──
    # A committed reference breakout (IB edge / prior-day range / balance area) that is ACCEPTED
    # (>=2 closed bars beyond + volume-accept, computed in relative_features) reclassifies the day
    # IMMEDIATELY in the break direction — WITHOUT waiting for the rib>=2.5 Trend floor ("structure
    # lags", p.37; balance-breakout = "a trade you almost have to do", pp.288-292). A return back
    # inside the reference = rejection → the `failed_breakout` tag (out()) + no promotion (revert).
    # Runs BEFORE the FORMING gate so a gap-and-go beyond prior range names the trend early.
    # Flag S1_ACCEPTANCE_RECLASS_V1, default OFF → byte-identical when unset.
    if _reclass_on and not _failed_break and not oi:
        _abrk = feat.get("accepted_break")           # "UP" | "DOWN" | None (dominant accepted side)
        _aref = feat.get("accepted_break_ref") or "ref"
        if _abrk in ("UP", "DOWN"):
            if feat.get("dd_second_dist"):
                return out("Trend_DD", "CLASSIFIED",
                           f"acceptance-reclass: 1-sided + DD ({_aref} break {_abrk})",
                           reclass=True, reclass_ref=_aref, break_dir=_abrk)
            if feat.get("one_tf") == _abrk:
                return out("Trend_Normal", "CLASSIFIED",
                           f"acceptance-reclass: accepted {_aref} break {_abrk} + one_tf -> Trend (rib floor waived)",
                           reclass=True, reclass_ref=_aref, break_dir=_abrk, cvd_confirms=cvd_dir)
            return out("Normal_Variation", "CLASSIFIED" if is_eod else "PROVISIONAL",
                       f"acceptance-reclass: accepted {_aref} break {_abrk} (one_tf pending)",
                       reclass=True, reclass_ref=_aref, break_dir=_abrk)

    # ── Priority 1 = FORMING — before the IB locks (60 min / 12 bars). Never FORMING at EOD. ──
    if n < ib_lock_bars and not is_eod:
        # P0-2 (Dalton pp.63-74, ruling D1): the open foreshadows the day. Once 30 min is in
        # (forming_lock_minutes), COMMIT a provisional day-type from {opening_type × open_location}
        # instead of a bare FORMING that discards the open's forecast for the first hour.
        # Flag S1_COMMITTED_PROVISIONAL_V1, default OFF → byte-identical (bare FORMING) when unset.
        forming_lock_bars = int(cl.get("forming_lock_minutes", 30) / 5)
        if (os.environ.get("S1_COMMITTED_PROVISIONAL_V1", "0").lower() in ("1", "true", "yes")
                and n >= forming_lock_bars):
            prov = _provisional_from_open(feat, plan, out)
            if prov is not None:
                return prov
        return out("FORMING", "FORMING", f"before IB lock ({n}/{ib_lock_bars} bars)")

    # ── Priority 2 = Nontrend (Sideways): 0 sides, low participation, TRULY compressed (rib<=1.15) ──
    # FIX A: Nontrend width-floor — session range > NONTREND_MAX_RANGE_PTS (default 18)
    # disqualifies Nontrend (falls to ≥Normal). Flag NONTREND_WIDTH_FLOOR, default OFF.
    _nt_floor_on = os.environ.get("NONTREND_WIDTH_FLOOR", "0").lower() in ("1", "true", "yes")
    _nt_max_range = float(os.environ.get("NONTREND_MAX_RANGE_PTS", "18"))
    _session_range = feat.get("session_range")  # high−low so far (passed from caller)
    _nt_range_ok = not _nt_floor_on or _session_range is None or _session_range <= _nt_max_range

    if sides == 0 and vr is not None and vr <= vol_low and rib is not None and rib <= rib_nt and _nt_range_ok:
        return out("Nontrend", "CLASSIFIED",
                   f"0-sided + low participation (vol_ratio {round(vr,2)}<= {vol_low}) + compressed (rib {rib}<= {rib_nt})"
                   + (f" + range {_session_range}pt <= {_nt_max_range}" if _nt_floor_on and _session_range else ""))

    # ── Priority 3 = Neutral: extension BOTH sides (each side volume-accepted) ──
    if sides == 2:
        if cp is not None and (cp >= ce_hi or cp <= ce_lo):
            return out("Neutral_Extreme", "CLASSIFIED", "2-sided, close at an extreme (one side won late)")
        if cp is not None and cc_lo <= cp <= cc_hi:
            return out("Neutral_Center", "CLASSIFIED", "2-sided, close at center (balanced)")
        return out("Neutral_Center", "CLASSIFIED" if is_eod else "PROVISIONAL",
                   "2-sided, close resolving" + (" (EOD-committed)" if is_eod else " (provisional)"))

    # ── sides == 1 → Trend_DD (4) / Trend_Normal (5) / Normal_Variation (6) ──
    if sides == 1:
        at_extreme = cp is not None and (cp >= ce_hi or cp <= ce_lo)
        # 4) Trend_DD — narrow IB + 2-POC single-print neck + new value held (from dd_features).
        if feat.get("dd_second_dist"):
            return out("Trend_DD", "CLASSIFIED",
                       "1-sided + double-distribution (narrow IB + 2-POC single-print neck + new value held)")
        # 5) Trend_Normal — STRICT signature, ALL four. CVD CONFIRMS (confidence), it is NOT a gate
        #    (06-05 trended down yet CVD diverged up — structure still makes it a trend).
        if (not oi) and (feat.get("one_tf") in ("UP", "DOWN")) and at_extreme and rib is not None and rib >= rib_tn:
            return out("Trend_Normal", "CLASSIFIED",
                       f"1-sided: open held + one_tf + close opposite extreme + rib>={rib_tn}"
                       + (" + CVD-confirmed" if cvd_dir else " (CVD divergent — trend by structure)"),
                       cvd_confirms=cvd_dir)
        # 5b) Trend_Normal via OPEN_DRIVE — waive the rib>=2.5 floor when the day OPENED with a
        #     drive (Michael 2026-06-30). OPEN_DRIVE + one_tf + close-at-extreme IS a trend even
        #     if the range extension is modest (the drive substitutes for range magnitude).
        #     Flag S1_OPEN_DRIVE_TREND, default OFF → byte-identical when unset.
        if (os.environ.get("S1_OPEN_DRIVE_TREND", "0").lower() in ("1", "true", "yes")
                and (not oi)
                and (feat.get("one_tf") in ("UP", "DOWN"))
                and at_extreme
                and feat.get("opening_type") in ("OPEN_DRIVE", "OPEN_TEST_DRIVE")):
            return out("Trend_Normal", "CLASSIFIED",
                       f"1-sided: {feat.get('opening_type')} + one_tf + close-at-extreme → Trend "
                       f"(rib {rib} floor waived)"
                       + (" + CVD-confirmed" if cvd_dir else ""),
                       cvd_confirms=cvd_dir, open_drive_trend=True)
        # 5c) P1-5 (S1_TREND_CONTROL_V1, default OFF — Dalton pp.22-25, doctrine
        #     contradiction-2): a Trend day is defined by CONTROL — one-timeframe
        #     stair-steps with an elongating range — not by a range multiple.
        #     rib>=2.5 made mid-day recognition late (the 07-08 down-day sat as
        #     Variation while stair-stepping lower all session). Control-path:
        #     >=N consecutive stair-steps in the one_tf direction + rib past a
        #     modest floor + close pressing the matching extreme.
        if os.environ.get("S1_TREND_CONTROL_V1", "0").lower() in ("1", "true", "yes"):
            _min_steps = int(os.environ.get("S1_TREND_CTRL_MIN_STEPS", "3"))
            _min_rib = float(os.environ.get("S1_TREND_CTRL_MIN_RIB", "1.8"))
            # NOTE: full-session one_tf is deliberately NOT required — one
            # violated period early in the day kills it forever, which is the
            # exact structure-lag Dalton warns about (p.37). The CURRENT
            # stair-step run IS the running one-timeframe/control measure
            # (p.25: "each period ≥/≤ prior" during the trend leg). Replay
            # evidence: with one_tf required the 07-08 stair-collapse never
            # flagged; without it, it flags at 18:30 (↓3 steps, cp .21).
            _up_ok = ((feat.get("stair_steps_up") or 0) >= _min_steps
                      and cp is not None and cp >= 0.75)
            _dn_ok = ((feat.get("stair_steps_dn") or 0) >= _min_steps
                      and cp is not None and cp <= 0.25)
            # `oi` (returned-through-open) is deliberately NOT a veto here: an
            # early open-return invalidates the OPENING conviction (p.65), not a
            # NEW stair-run that formed after it — on 07-08 the morning return
            # blocked recognition of the 18:30 three-period collapse entirely.
            if rib is not None and rib >= _min_rib and (_up_ok or _dn_ok):
                _dirlbl = "UP" if _up_ok else "DOWN"
                _steps = feat.get("stair_steps_up") if _up_ok else feat.get("stair_steps_dn")
                return out("Trend_Normal", "CLASSIFIED",
                           f"control-path: {_steps} stair-steps {_dirlbl} + "
                           f"close pressing extreme + rib {rib}>={_min_rib} "
                           f"(rib>={rib_tn} floor waived per Dalton p.25)"
                           + (" + CVD-confirmed" if cvd_dir else ""),
                           cvd_confirms=cvd_dir, trend_control_path=True)
        # 6) Normal_Variation (Expanded Typical) — catch-all. PROVISIONAL until EOD: a 1-sided day
        #    can still get side-2 (→ Neutral) or build DD/Trend structure as it extends.
        return out("Normal_Variation", "CLASSIFIED" if is_eod else "PROVISIONAL",
                   f"1-sided extension = Expanded Typical (rib {rib})")

    # ── Priority 7 = Normal (Typical): 0 sides, contained, normal participation, IB not-narrow ──
    ib_narrow = feat.get("ib_narrow")
    if ib_narrow is None:                                   # fallback when the relative flag isn't passed
        ib_w = feat.get("ib_width")
        ib_narrow = ib_w is not None and ib_w <= cl.get("ib_narrow_pts", 7.0)
    normal_vol = vr is None or vr > vol_low
    if rib is not None and rib <= rib_norm and normal_vol and not ib_narrow:
        conf = []
        if feat.get("tails_both"):
            conf.append("tails@2edges")
        if feat.get("close_at_poc"):
            conf.append("close@POC")
        return out("Normal", "CLASSIFIED",
                   "0-sided, contained (rib<=%s) + normal vol + IB not-narrow%s"
                   % (rib_norm, (" [+" + ",".join(conf) + "]") if conf else ""))
    # 0-sided that fits neither Nontrend nor Normal (narrow IB + normal vol, or rib 1.3-1.5):
    # provisional Normal-leaning; committed at EOD so no day ends FORMING (Michael 2026-06-20).
    return out("Normal", "CLASSIFIED" if is_eod else "PROVISIONAL",
               f"0-sided, {'EOD-resolved to Normal' if is_eod else 'developing (Normal-leaning)'} (rib {rib})")
