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
        # P2-9 (S1_TPO_COUNT_V1, default OFF — Dalton pp.41-45): volume-profile
        # imbalance (TPO-count proxy) as a 9th aligned-evidence item. ADDITIVE:
        # when the flag is off the list stays 8 long → scores byte-identical.
        if os.environ.get("S1_TPO_COUNT_V1", "0").lower() in ("1", "true", "yes"):
            imb = feat.get("profile_imbalance")
            ev.append(imb is not None and ((d == "UP" and imb >= 0.15)
                                           or (d == "DOWN" and imb <= -0.15)))
    else:
        # non-directional (Neutral_Center / Normal / Nontrend): how cleanly the balance holds
        ev = [
            cp is not None and cc_lo <= cp <= cc_hi,                                     # centered close
            sides in (0, 2),                                                            # balanced sides
            (rib is not None and rib <= cl["rib_normal_max"]) or sides == 2,            # contained or two-sided
        ]
    return round(sum(1 for x in ev if x) / len(ev), 2)


def _dir_bias(feat: Dict[str, Any], cl: Dict[str, Any]) -> Optional[str]:
    """The day's directional bias as a plain UP/DOWN/None read (N1 RC#4 observability,
    2026-07-17, docs/handoff/N1B_TRANSITIONS_DIAGNOSIS_2026-07-17.md §5.5): one-timeframe
    direction first, else the dominant ACCEPTED reference-break direction (P0-1 v2 key),
    else a close pressing an extreme (same 0.85/0.15 bands _confidence uses). Emitted on
    every classify() output so "Variation-DOWN" is representable in v9_day_type_state —
    before this, direction was only the plan's STRATEGY string (with_extension/...),
    which is a function of the type and carries no leg direction. Observability only:
    no gate reads it."""
    one_tf = feat.get("one_tf")
    if one_tf in ("UP", "DOWN"):
        return one_tf
    ab = feat.get("accepted_break")
    if ab in ("UP", "DOWN"):
        return ab
    cp = feat.get("close_pos")
    if cp is not None:
        if cp >= cl["close_extreme_hi"]:
            return "UP"
        if cp <= cl["close_extreme_lo"]:
            return "DOWN"
    return None


def smooth_confidence(prev: Optional[float], raw: Optional[float], day_type: str = "") -> Optional[float]:
    """N1 RC#3 (flag `S1_CONF_SMOOTH_V1`, default OFF — 2026-07-17,
    docs/handoff/N1B_TRANSITIONS_DIAGNOSIS_2026-07-17.md): the persisted confidence
    flapped 0.12↔0.67↔1.00 on adjacent bars because `_confidence()` switches between
    the 8-item directional evidence list and the 3-item balance list whenever its
    direction-basis `d` flips — no market change required. This helper is a per-bar
    SLEW CAP applied at the sequence layer (live promoter in backend/main.py + the
    classify_replay timeline loop): the published confidence moves at most
    `S1_CONF_SMOOTH_MAX_DELTA` (default 0.25) per bar toward the raw score, which
    guarantees the T2 acceptance bound (adjacent-bar delta <= 0.35) while converging
    to the raw value within a few bars. Type decisions are NEVER touched — only the
    confidence number. Stateless-pure: callers keep `prev` (the previous smoothed
    value for THIS session; None at session start / after FORMING).

    Flag OFF (unset/0) → returns `raw` unchanged → byte-identical behavior.
    """
    if raw is None:
        return None
    if os.environ.get("S1_CONF_SMOOTH_V1", "0").lower() not in ("1", "true", "yes"):
        return raw
    if day_type == "FORMING" or prev is None:
        # FORMING is honest-zero (no conviction yet) and carries no smoothing state;
        # the first classified bar takes its raw score so the lock isn't lagged.
        return raw
    try:
        max_d = float(os.environ.get("S1_CONF_SMOOTH_MAX_DELTA", "0.25"))
    except (TypeError, ValueError):
        max_d = 0.25
    step = max(-max_d, min(max_d, raw - prev))
    return round(prev + step, 2)


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
    # N1b (2026-07-17, docs/handoff/N1B_TRANSITIONS_DIAGNOSIS_2026-07-17.md RC#2):
    # acceptance-reclass (below) returns EARLY on any held accepted break, before
    # the sides==2 Neutral check (Priority 3) ever runs — so a day that extended
    # BOTH sides but still holds one stale acceptance cannot be named Neutral
    # until that acceptance is rejected (proven: live 07-15 flip to Neutral_Center
    # lagged to 20:46 IL vs the mechanically-correct ~19:05 IL). Doctrine ruling
    # (06-20): "נייטרלי = יום מבולגן עם פריצה משני הצדדים" — sides==2 should
    # outrank a held one-side acceptance. Default OFF → byte-identical when unset.
    _neutral_precedence_on = os.environ.get("S1_NEUTRAL_PRECEDENCE_V1", "0").lower() in ("1", "true", "yes")

    _dbias = _dir_bias(feat, cl)   # N1 RC#4: emitted on every output (observability, no gate)

    def out(dt: str, status: str, reason: str, **extra) -> Dict[str, Any]:
        d = {"day_type": dt, "status": status, "direction": _direction(plan, dt),
             "dir_bias": _dbias,
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
    if _reclass_on and not _failed_break and not oi and not (_neutral_precedence_on and sides == 2):
        _abrk = feat.get("accepted_break")           # "UP" | "DOWN" | None (dominant accepted side)
        _aref = feat.get("accepted_break_ref") or "ref"
        # S1_RECLASS_REQUIRES_IB_EXT_V1 (2026-07-31, Michael: "הזיהוי לא נכון" —
        # verified against the candles): the ratified MP rule says EXTENSION =
        # post-B breaks TODAY'S IB. 07-31: IB 7427.5-7515.25, the entire
        # afternoon traded INSIDE it (post-IB 7449-7501, zero extension bars),
        # yet a prior-VA break promoted the day to "Variation with_extension
        # UP" — a Variation whose extension never existed. Once the IB is
        # LOCKED, an accepted break may only reclass to extension-class types
        # (Variation/Trend) if the day actually extended beyond its own IB in
        # the break direction (ext_up_hold/ext_dn_hold). Before IB lock the
        # gap-and-go early-naming path is preserved unchanged.
        if (_abrk in ("UP", "DOWN")
                and os.environ.get("S1_RECLASS_REQUIRES_IB_EXT_V1", "0").lower()
                in ("1", "true", "yes")
                and n >= ib_lock_bars):
            _ib_ext_ok = bool(feat.get("ext_up_hold")) if _abrk == "UP" \
                else bool(feat.get("ext_dn_hold"))
            if not _ib_ext_ok:
                _abrk = None   # no IB extension => no extension-class reclass;
                # fall through to the structural ladder (Normal/Neutral by shape)
        # P2.1 (DEV_PLAN 02.08): delta_confirms_extension (R5) — an extension
        # WITHOUT delta confirmation is a failed-auction candidate → do NOT
        # promote to Variation/Trend. Only vetoes when DELTA_FEATURES_V1 is ON
        # and the data is available (False, not None). None = no data → pass.
        if _abrk in ("UP", "DOWN"):
            _delta_ext = feat.get("delta_confirms_ext")
            if _delta_ext is False and os.environ.get(
                "DELTA_FEATURES_V1", "0"
            ).lower() in ("1", "true", "yes"):
                _abrk = None  # extension not delta-confirmed → no reclass
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

    # ── Priority 1.9 = P1-8 Nonconviction (S1_NONCONVICTION_V1, default OFF —
    #    Dalton pp.300-302, doctrine contradiction-8): looks like Normal/NV/
    #    Neutral but carries NO OTF footprints at all — Open-Auction rotating
    #    INSIDE prior value, zero range-extension bars, mid close. No reference
    #    points → stand aside entirely (NO_TRADE via position-gate + playbook).
    #    Checked BEFORE Nontrend: Nontrend still requires low participation;
    #    a Nonconviction day can have normal volume with zero conviction. ──
    if os.environ.get("S1_NONCONVICTION_V1", "0").lower() in ("1", "true", "yes"):
        _oa = str(feat.get("opening_type") or "").startswith("OPEN_AUCTION")
        _in_val = feat.get("open_location") == "in_value"
        _no_re = (feat.get("ext_up_bars") or 0) == 0 and (feat.get("ext_dn_bars") or 0) == 0
        _mid = cp is not None and cc_lo <= cp <= cc_hi
        if _oa and _in_val and sides == 0 and _no_re and _mid:
            return out("Nonconviction", "CLASSIFIED" if is_eod else "PROVISIONAL",
                       "OA-in-prior-value + zero RE bars + sides=0 + mid close — "
                       "no OTF footprints, stand aside (Dalton pp.300-302)")

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
        # P2-8 hysteresis: prevent oscillation between Neutral_Extreme↔Center.
        # Once classified as one sub-type, require the close to move CLEARLY
        # into the other zone (beyond a buffer band) before switching.
        # Without this, #647 oscillated every bar at the zone boundary.
        _hysteresis_pts = float(os.environ.get("NEUTRAL_HYSTERESIS_PTS", "0.05"))
        _prev_neutral = feat.get("_prev_neutral_subtype")
        if cp is not None and (cp >= ce_hi or cp <= ce_lo):
            _want = "Neutral_Extreme"
        elif cp is not None and cc_lo <= cp <= cc_hi:
            _want = "Neutral_Center"
        else:
            _want = "Neutral_Center"  # default provisional

        # Hysteresis: if switching sub-type, require close position to be
        # clearly in the new zone (not at the boundary)
        if _prev_neutral and _want != _prev_neutral and cp is not None:
            # At the boundary — stick with previous classification
            in_buffer = (abs(cp - ce_hi) < _hysteresis_pts or
                         abs(cp - ce_lo) < _hysteresis_pts or
                         abs(cp - cc_hi) < _hysteresis_pts or
                         abs(cp - cc_lo) < _hysteresis_pts)
            if in_buffer:
                _want = _prev_neutral

        _reason = ("2-sided, close at an extreme (one side won late)" if _want == "Neutral_Extreme"
                   else "2-sided, close at center (balanced)")
        return out(_want, "CLASSIFIED" if is_eod else "PROVISIONAL", _reason)

    # ── P1 (2026-07-29): Neutral round-trip reclass (NEUTRAL_ROUNDTRIP_V1) ──
    # sides==1 but expansion returned through the open AND close is mid-range
    # → Neutral, not Normal_Variation. This is Dalton's "expansion that failed +
    # return to value" = the market tried to trend, gave up, and came back.
    # 07-29: 80pt drop then full V-reversal → should be Neutral, was Normal_Variation.
    # Flag OFF → skips this block → byte-identical to before.
    if (sides == 1 and oi
            and os.environ.get("NEUTRAL_ROUNDTRIP_V1", "0").lower() in ("1", "true", "yes")
            and cp is not None and cc_lo <= cp <= cc_hi):
        return out("Neutral_Center", "CLASSIFIED",
                   "1-sided expansion returned through open + close at center = "
                   "failed expansion → Neutral (V-reversal round-trip)")

    # ── sides == 1 → Trend_DD (4) / Trend_Normal (5) / Normal_Variation (6) ──
    if sides == 1:
        at_extreme = cp is not None and (cp >= ce_hi or cp <= ce_lo)
        # 4) Trend_DD — narrow IB + 2-POC single-print neck + new value held (from dd_features).
        if feat.get("dd_second_dist"):
            # P1-7 (S1_DD_INVALIDATION_V1, default OFF — Dalton p.27, doctrine
            # contradiction-5): recent closes back INSIDE the neck singles =
            # the 2nd distribution is rejected, "conditions changed" — the DD
            # label must FALL (falls through to Variation/other branches) and
            # the invalidation is surfaced for gates/S6.
            if (os.environ.get("S1_DD_INVALIDATION_V1", "0").lower() in ("1", "true", "yes")
                    and feat.get("dd_neck_refilled")):
                pass  # invalidated — do NOT return Trend_DD; continue to 5/5b/5c/6
            else:
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
            # P1-6 (S1_VALUE_MIGRATION_V1, default OFF — Dalton pp.49,55): Trend
            # requires MIGRATING value. When the developing 70% VA still overlaps
            # yesterday's VA almost fully (>= S1_VM_OVERLAP_MAX, default 0.8) and
            # no migration direction exists, the "trend" is geometry inside old
            # value = balance → the control-path promotion is vetoed. A day with
            # value_migration UP/DOWN (or low overlap) passes untouched.
            _vm_veto = False
            if os.environ.get("S1_VALUE_MIGRATION_V1", "0").lower() in ("1", "true", "yes"):
                _ovl = feat.get("va_overlap_pct")
                _vm_veto = (feat.get("value_migration") is None and _ovl is not None
                            and _ovl >= float(os.environ.get("S1_VM_OVERLAP_MAX", "0.8")))
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
            if rib is not None and rib >= _min_rib and (_up_ok or _dn_ok) and not _vm_veto:
                _dirlbl = "UP" if _up_ok else "DOWN"
                _steps = feat.get("stair_steps_up") if _up_ok else feat.get("stair_steps_dn")
                _vm = feat.get("value_migration")
                return out("Trend_Normal", "CLASSIFIED",
                           f"control-path: {_steps} stair-steps {_dirlbl} + "
                           f"close pressing extreme + rib {rib}>={_min_rib} "
                           f"(rib>={rib_tn} floor waived per Dalton p.25)"
                           + (f" + value migrating {_vm}" if _vm else "")
                           + (" + CVD-confirmed" if cvd_dir else ""),
                           cvd_confirms=cvd_dir, trend_control_path=True)
        # 5d) K6 Trend-elongation path (S1_TREND_ELONGATION_V1, default OFF — 08-09).
        #     Research (08-08): days 08-03 (rib 1.67<1.8 control-floor) and 08-05
        #     (rib 2.92 but no 3 stair-steps) classified NV when Michael saw Trend.
        #     Dalton's range-magnitude criterion: rib >= 2.5 + close pressing the
        #     extreme (cp ≤ 0.15 or ≥ 0.85) = the market moved far enough AND held
        #     the edge. This is the STRUCTURAL complement to the control-path's
        #     process measure (stair-steps). Flag OFF → byte-identical, falls through.
        if os.environ.get("S1_TREND_ELONGATION_V1", "0").lower() in ("1", "true", "yes"):
            _elon_min_rib = float(os.environ.get("S1_TREND_ELON_MIN_RIB", "2.5"))
            _elon_cp_hi = float(os.environ.get("S1_TREND_ELON_CP_HI", "0.85"))
            _elon_cp_lo = float(os.environ.get("S1_TREND_ELON_CP_LO", "0.15"))
            if (rib is not None and rib >= _elon_min_rib
                    and cp is not None
                    and (cp >= _elon_cp_hi or cp <= _elon_cp_lo)):
                _elon_dir = "UP" if cp >= _elon_cp_hi else "DOWN"
                return out("Trend_Normal", "CLASSIFIED",
                           f"elongation-path: rib {rib}>={_elon_min_rib} + "
                           f"close-at-extreme (cp {cp:.2f}) = Trend {_elon_dir} "
                           f"(stair-steps waived per range magnitude)"
                           + (" + CVD-confirmed" if cvd_dir else ""),
                           cvd_confirms=cvd_dir, trend_elongation_path=True)

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
