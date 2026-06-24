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

    def out(dt: str, status: str, reason: str, **extra) -> Dict[str, Any]:
        d = {"day_type": dt, "status": status, "direction": _direction(plan, dt),
             "reason": reason, "invalidated": oi, "opening_invalidated": oi}
        d.update(extra)
        return d

    # ── Priority 0 = INVALIDATED overlay: `invalidated`/`oi` above. A return through the
    #    opening range exits the trade + forces re-classification (oi blocks Trend below;
    #    the day_type re-forms). Not a terminal type, so the day keeps developing. ──

    # ── Priority 1 = FORMING — before the IB locks (60 min / 12 bars). Never FORMING at EOD. ──
    if n < ib_lock_bars and not is_eod:
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
