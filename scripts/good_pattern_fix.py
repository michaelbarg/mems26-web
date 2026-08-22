#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
good_pattern_fix.py — why the patterns that MAKE money don't fire enough, and
what a relaxed version would have been worth.

Michael (2026-08-22): "אם הבעיה בתבניות הטובות אני רוצה שנמצא דרך לפתור את זה".

SCOPE = the money-makers only (confirmed from v9_trades first, never assumed):
    REACTIVE_LONG/SHORT · INITIATIVE_LONG/SHORT · GB100 · TREND_STEP ·
    DOUBLE_BOTTOM_EE · ZLR · HTLB.   The dead/losing patterns are out of scope
    (see DEAD_PATTERNS_REVIVAL_2026-08-22).

ENGINES ARE REUSED, NOT REBUILT
    scripts/oracle_study.py       -> bars, ATR, zigzag thr, sim_ladder, cost model
    scripts/entry_side_replay.py  -> session loader, 19-bar live detection window,
                                     causal 7-type labels, one-slot sequencing
    five_min_system::_detect_reactive/_detect_initiative -> THE LIVE DETECTORS,
                                     invoked with a duck-typed `self` shim
    five_min/patterns/*, woodies/patterns/*, trend_step/detector.py -> live
    config/s2_reactive_calibration.yaml, config/s2_firing.yaml -> live configs

Every relaxation arm is an ADDITIVE post-pass: the live detector runs first and
only if it says "no" is the relaxed conjunction evaluated.  The relaxed
conjunction is a mirror of the live one and is VERIFIED against the live method
(arm `RV0` must reproduce the live fire set exactly — printed as [selfcheck]).

READ-ONLY. Direct psycopg2, read-only session. Writes stdout + --json only.
Nothing here is imported by any runtime path.

Usage:  python3 scripts/good_pattern_fix.py --json /tmp/gpf.json
"""

import argparse
import collections
import datetime as dt
import importlib.util as _ilu
import json
import os
import statistics
import sys

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def load_env(path=None):
    path = path or os.path.join(ROOT, ".env")
    n = 0
    for raw in open(path, errors="ignore"):
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.split(" #")[0].strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
            n += 1
    return n


_N_ENV = load_env()

_spec = _ilu.spec_from_file_location(
    "oracle_study", os.path.join(ROOT, "scripts", "oracle_study.py"))
ORA = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(ORA)

_spec2 = _ilu.spec_from_file_location(
    "entry_side_replay", os.path.join(ROOT, "scripts", "entry_side_replay.py"))
ESR = _ilu.module_from_spec(_spec2)
_spec2.loader.exec_module(ESR)

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
D0, D1 = ESR.D0, ESR.D1
TICK = 0.25
SLIP = 1
SIZES = (4, 6)
WINDOW = ESR.LIVE_DET_WINDOW      # 19 = live _det_buf
WOODIES_BUF = 50                  # woodies_system.max_buffer
ET_UTC = dt.timedelta(hours=4)
S4_DEDUP = 30
DEDUP = {"DOUBLE_TOP_AA": 30, "DOUBLE_BOTTOM_EE": 30, "INVERSE_HNS": 30,
         "HNS_TOP": 30, "BULL_FLAG": 20, "BEAR_FLAG": 20}   # A2, five_min:323
FMS = None
CAL = None


def med(xs):
    return round(statistics.median(xs), 2) if xs else 0.0


def _label_ok(lab):
    return bool(lab) and lab not in ("UNKNOWN", "Nontrend")


# ==================================================================== S2 shim
class S2Shim:
    """Duck-typed `self` for the LIVE _detect_reactive / _detect_initiative."""

    def __init__(self):
        self._current_atr_5m = None
        self.current_day_type = None
        self._cvd_sorted = []

    def _get_cot_from_footprint(self):
        return None              # S3 muted; S2_REQUIRE_COT_AMT unset -> never a gate

    def _get_amt_from_footprint(self):
        return None

    def _get_belly_from_footprint(self):
        return None              # None passes, same as live with S3 muted

    def _get_belly_ratio_from_footprint(self, direction):
        return None

    def _poc_vol_rising(self, bars, n=3):
        return FMS.FiveMinSystem._poc_vol_rising(self, bars, n)

    def _poc_vol_falling(self, bars, n=3):
        return FMS.FiveMinSystem._poc_vol_falling(self, bars, n)

    def _compute_setup_cvd(self, bars_5m, window=4):
        keys = [b.get("ts") for b in bars_5m[-window:] if b.get("ts")]
        if len(keys) < 2:
            return None
        t0, t1 = keys[0], keys[-1]
        cums = [v for k, v in self._cvd_sorted if t0 <= k <= t1]
        if len(cums) < 2:
            return None
        perbar = [cums[i] - cums[i - 1] for i in range(1, len(cums))]
        return {"net_delta": cums[-1] - cums[0], "perbar_deltas": perbar,
                "cumulatives": cums}


def _mk_bar(b):
    d = dict(o=b["o"], h=b["h"], l=b["l"], c=b["c"], v=b["v"])
    d["ts"] = (b["t"] + ET_UTC).isoformat() + "+00:00"
    return d


# ============================================== live-faithful mirror of S2
def _vol_flags(buf):
    """The three D-RVX variants exactly as five_min_system.py:811-819 builds them."""
    b1, b2 = buf[-4], buf[-3]
    b0v = buf[-5]["v"] if len(buf) >= 5 else 0
    b1v, b2v = b1["v"], b2["v"]
    volbuf = [b["v"] for b in buf[:-3] if b["v"] > 0]
    ravg = sum(volbuf[-20:]) / max(len(volbuf[-20:]), 1) if volbuf else b1v
    vsa = (b2v < b1v and b2v < b0v and b2v <= 0.7 * ravg) if b1v > 0 else False
    rvol = (b2v <= 0.5 * ravg) if ravg > 0 else False
    return vsa, rvol, ravg, b1v, b2v


def _b2_drop(buf, rule, cal):
    """rule: 'live' (config variant, = UNION today) | 'daytype' | 'drop_only'."""
    from backend.v9.config_loader import load_s2_firing
    vsa, rvol, ravg, b1v, b2v = _vol_flags(buf)
    b2 = buf[-3]
    atr = _b2_drop.atr or 2.0
    strict = vsa and (abs(b2["h"] - b2["l"]) < 0.7 * atr)
    if rule == "live":
        v = load_s2_firing()
        if v == "B_RVOL":
            return rvol
        if v == "C_STRICT":
            return strict
        if v == "UNION":
            return vsa or rvol or strict
        if v == "INTERSECTION":
            return vsa and rvol and strict
        return vsa
    if rule == "daytype":
        # the RULED-BUT-SHADOWED branch: five_min_system.py:830-848 is an `elif`
        # under `if S2_VSA_VOLUME` (=1 live) so it can never run today.
        k = float(cal.get("volume", {}).get("b2_avg_k", 0.8))
        kb = float(cal.get("volume", {}).get("b2_vs_b1", 1.0))
        return (b2v < b1v * kb and b2v <= k * ravg) if b1v > 0 else False
    if rule == "drop_only":
        return (b2v < b1v) if b1v > 0 else False
    raise ValueError(rule)


_b2_drop.atr = None


def react_mirror(shim, buf, b2_rule="live", tol_atr=None, confirm75=False):
    """Mirror of the LIVE _detect_reactive conjunction, with one knob replaced.

    tol_atr  : override for geometry.confirm_tol_atr (None -> the live YAML value)
    confirm75: use the volatile-regime 75%-of-b3-range threshold on every day
    """
    if len(buf) < FMS.MIN_BARS_REQUIRED:
        return (None, 0, {})
    b1, b2, b3, b4 = buf[-4], buf[-3], buf[-2], buf[-1]
    atr = shim._current_atr_5m or 2.0
    _b2_drop.atr = atr
    cal = CAL(shim.current_day_type)
    drop = _b2_drop(buf, b2_rule, cal)
    if not drop:
        return (None, 0, {})
    vad = FMS.vol_adaptive_active(buf) or confirm75
    tol = (float(cal.get("geometry", {}).get("confirm_tol_atr", 0.0))
           if tol_atr is None else float(tol_atr)) * atr
    thrL = FMS.reactive_confirm_threshold(b3["h"], b3["l"], "LONG", vad)
    thrS = FMS.reactive_confirm_threshold(b3["h"], b3["l"], "SHORT", vad)
    b1v = b1["v"]

    def _cvd_ok(direction):
        if os.environ.get("S2_CVD_DETECTION_V1", "").lower() not in ("1", "true", "yes"):
            return True
        c = shim._compute_setup_cvd(buf, window=4)
        if c is None:
            return True
        pb, cums = c["perbar_deltas"], c["cumulatives"]
        if direction == "LONG":
            entry_buy = pb[-1] > 0 if pb else False
            div = (b3["l"] < b1["l"] and cums[-2] > cums[0]) if len(cums) >= 3 else False
            return entry_buy or div
        entry_sell = pb[-1] < 0 if pb else False
        net_sell = c["net_delta"] < 0
        div = (b3["h"] > b1["h"] and cums[-2] < cums[0]) if len(cums) >= 3 else False
        return entry_sell or net_sell or div

    if (b1["c"] < b1["o"] and b1v > 0 and b3["c"] > b3["o"]
            and b4["c"] > b4["o"] and b4["c"] >= (thrL - tol)):
        if _cvd_ok("LONG"):
            return ("LONG", 0.75, {"kind": "REACTIVE", "stage": 4,
                                   "structural_anchor": min(b1["l"], b2["l"], b3["l"])})
        return (None, 0, {})
    if (b1["c"] > b1["o"] and b1v > 0 and b3["c"] < b3["o"]
            and b4["c"] < b4["o"] and b4["c"] <= (thrS + tol)):
        if _cvd_ok("SHORT"):
            return ("SHORT", 0.75, {"kind": "REACTIVE", "stage": 4,
                                    "structural_anchor": max(b1["h"], b2["h"], b3["h"])})
        return (None, 0, {})
    return (None, 0, {})


def init_mirror(shim, buf, exp_mult=1.0, beyond_frac=1.0):
    """Mirror of the LIVE _detect_initiative conjunction.

    exp_mult    : multiplier on the adaptive expansion floor (1.0 = live)
    beyond_frac : 1.0 = b4 must close fully beyond b1's extreme (live);
                  0.75 = beyond 75% of b1's range
    """
    if len(buf) < FMS.MIN_BARS_REQUIRED:
        return (None, 0, {})
    b1, b2, b3, b4 = buf[-4], buf[-3], buf[-2], buf[-1]
    atr = shim._current_atr_5m
    b1r, b3r = b1["h"] - b1["l"], b3["h"] - b3["l"]
    vad = FMS.vol_adaptive_active(buf)
    emin, emax = FMS.get_expansion_range(buf)
    if vad:
        emin = min(emin, FMS._VOL_EXP_FLOOR_CAP_PT)
    exp_ok = emin <= b1r <= emax
    if FMS.s2_adaptive_thresholds_on():
        fl = FMS.adaptive_expansion_floor(buf, atr14=atr, day_type=shim.current_day_type)
        if fl is not None:
            exp_ok = b1r >= fl * exp_mult
    join_req = b1r * (FMS._VOL_JOIN_FACTOR if vad else 1.0)
    if os.environ.get("S2_INITIATIVE_JOIN_ATR_CAP_V1", "").lower() in ("1", "true", "yes"):
        join_req = min(join_req, 0.55 * (atr or 5.0))
    if not (exp_ok and b3r > join_req):
        return (None, 0, {})
    tolL = b1["h"] - (1.0 - beyond_frac) * b1r
    tolS = b1["l"] + (1.0 - beyond_frac) * b1r

    def _cvd_ok(direction):
        if os.environ.get("S2_CVD_DETECTION_V1", "").lower() not in ("1", "true", "yes"):
            return True
        c = shim._compute_setup_cvd(buf, window=4)
        if c is None:
            return True
        return c["net_delta"] >= 0 if direction == "LONG" else c["net_delta"] <= 0

    if (b1["c"] > b1["o"] and b2["l"] > b1["l"] and b4["l"] >= b2["l"]
            and b4["c"] > tolL and _cvd_ok("LONG")):
        return ("LONG", 0.80, {"kind": "INITIATIVE", "stage": 4,
                               "structural_anchor": min(b1["l"], b2["l"], b3["l"])})
    if (b1["c"] < b1["o"] and b2["h"] < b1["h"] and b4["h"] <= b2["h"]
            and b4["c"] < tolS and _cvd_ok("SHORT")):
        return ("SHORT", 0.80, {"kind": "INITIATIVE", "stage": 4,
                                "structural_anchor": max(b1["h"], b2["h"], b3["h"])})
    return (None, 0, {})


# ==================================================================== scanners
ARM_DEFS = collections.OrderedDict([
    # name              (react kwargs or None, init kwargs or None)
    ("LIVE",            (None, None)),
    ("RV1 daytype-vol", (dict(b2_rule="daytype"), None)),
    ("RV2 b2<b1 only",  (dict(b2_rule="drop_only"), None)),
    ("RG1 tol 0.15ATR", (dict(tol_atr=0.15), None)),
    ("RG2 confirm75",   (dict(confirm75=True), None)),
    ("RV2+RG1",         (dict(b2_rule="drop_only", tol_atr=0.15), None)),
    ("IE1 exp x0.85",   (None, dict(exp_mult=0.85))),
    ("IE2 exp x0.70",   (None, dict(exp_mult=0.70))),
    ("IG1 b4 75%",      (None, dict(beyond_frac=0.75))),
    ("S2-ALL",          (dict(b2_rule="drop_only", tol_atr=0.15),
                         dict(exp_mult=0.85, beyond_frac=0.75))),
])


def scan_s2(bars, labels, shim, arm="LIVE", selfcheck=None):
    """LIVE REACTIVE->INITIATIVE chain + the arm's additive post-pass."""
    rk, ik = ARM_DEFS[arm]
    out = []
    for i in range(6, len(bars)):
        shim._current_atr_5m = ESR.atr5(bars, i)
        shim.current_day_type = ESR.norm_dt(labels[i])
        buf = [_mk_bar(b) for b in bars[max(0, i - WINDOW + 1):i + 1]]
        d, c, info = FMS.FiveMinSystem._detect_reactive(shim, buf)
        src = "live_R"
        if not d:
            d, c, info = FMS.FiveMinSystem._detect_initiative(shim, buf)
            src = "live_I"
        if selfcheck is not None:
            m, _, _ = react_mirror(shim, buf, b2_rule="live")
            live_r, _, _ = FMS.FiveMinSystem._detect_reactive(shim, buf)
            selfcheck["bars"] += 1
            if bool(m) != bool(live_r) or (m and m != live_r):
                selfcheck["mismatch"] += 1
        if not d and rk:
            d, c, info = react_mirror(shim, buf, **rk)
            src = "arm_R"
        if not d and ik:
            d, c, info = init_mirror(shim, buf, **ik)
            src = "arm_I"
        if not d:
            continue
        out.append(dict(i=i, dir=(1 if d == "LONG" else -1),
                        kind=info.get("kind", "?"), conf=round(float(c), 2), src=src))
    return out


def scan_chart(bars, labels, shim, which, window=None):
    from backend.v9.systems.five_min.patterns import double_bt as DBT
    from backend.v9.systems.five_min.patterns import head_shoulders as HNS
    tbl = {"DOUBLE_BOTTOM_EE": (DBT.detect_double_bottom_ee, True),
           "INVERSE_HNS": (HNS.detect_inverse_hns, False),
           "HNS_TOP": (HNS.detect_hns_top, False)}
    f, needs_atr = tbl[which]
    w = window or WINDOW
    out, dd = [], {}
    for i in range(12, len(bars)):
        if not _label_ok(ESR.norm_dt(labels[i])):
            continue
        a = ESR.atr5(bars, i)
        buf = [_mk_bar(b) for b in bars[max(0, i - w + 1):i + 1]]
        d, c, info = f(buf, atr_5m=a) if needs_atr else f(buf)
        if not d:
            continue
        key = f"{which}_{d}"
        if i - dd.get(key, -999) < DEDUP.get(which, 0):
            continue
        dd[key] = i
        out.append(dict(i=i, dir=(1 if d == "LONG" else -1), kind=which,
                        conf=round(float(c), 2), src="live"))
    return out


def scan_woodies(wbars, pid, reasons=None):
    from backend.v9.systems.woodies.patterns import ghost, zlr, gb100, htlb
    mod = dict(GHOST=ghost, ZLR=zlr, GB100=gb100, HTLB=htlb)[pid]
    out, dd = [], {}
    for i in range(14, len(wbars)):
        buf = wbars[max(0, i - WOODIES_BUF + 1):i + 1]
        try:
            r = mod.detect(buf, None)
        except Exception:
            continue
        if not r:
            continue
        if reasons is not None and not r.detected:
            rr = (r.details or {}).get("reject_reason")
            if rr:
                reasons[str(rr).split(":")[0][:44]] += 1
        if not r.detected:
            continue
        if r.stop is None or r.stop <= 0:
            if reasons is not None:
                reasons["T3_no_stop"] += 1
            continue
        key = f"{pid}_{r.direction}"
        if i - dd.get(key, -999) < S4_DEDUP:
            continue
        dd[key] = i
        out.append(dict(i=i, dir=(1 if r.direction == "LONG" else -1), kind=pid,
                        conf=round(float(r.confidence or 0), 2), src="live"))
    return out


def scan_trend_step(tsbars, stage=None, relax=None):
    from backend.v9.systems.trend_step import detector as TS
    p = dict(TS._p())
    if relax:
        p.update(relax)
    out, seen = [], set()
    for i in range(5, len(tsbars)):
        if stage is not None:
            _ts_stage(tsbars, i, p, stage)
        d = TS.detect_trend_step(tsbars, i, p)
        if not d:
            continue
        sid = d.get("step_id")
        if sid in seen:
            continue
        seen.add(sid)
        out.append(dict(i=i, dir=(1 if d["direction"] == "LONG" else -1),
                        kind="TREND_STEP", conf=0.75, src="live"))
    return out


def _ts_stage(bars, i, p, cnt):
    from backend.v9.systems.trend_step import detector as TS
    if i < 4:
        cnt["i<4"] += 1
        return
    if bars[i].get("hhmm") and bars[i]["hhmm"] > p["CUTOFF"]:
        cnt["cutoff"] += 1
        return
    piv = TS.zigzag(bars[:i + 1], float(p["ZZ_REV"]))
    if len(piv) < 2:
        cnt["no_pivots"] += 1
        return
    best = None
    for direction in ("SHORT", "LONG"):
        want = "L" if direction == "SHORT" else "H"
        k = None
        for j in range(len(piv) - 1, -1, -1):
            if piv[j][2] == want:
                k = j
                break
        if k is None or k == 0:
            best = best or "no_leg"
            continue
        ext_i, ext_p, _ = piv[k]
        org_i, org_p, org_k = piv[k - 1]
        if org_k == want:
            best = best or "no_leg"
            continue
        imp = (org_p - ext_p) if direction == "SHORT" else (ext_p - org_p)
        if not (p["IMP_MIN"] <= imp <= p["IMP_MAX"]):
            best = best or "impulse_size"
            continue
        if ext_i - org_i > p["IMP_BARS_MAX"] or ext_i <= org_i:
            best = best or "impulse_bars"
            continue
        stair = None
        if k >= 3:
            stair = ((ext_p < piv[k - 2][1] and org_p < piv[k - 3][1]) if direction == "SHORT"
                     else (ext_p > piv[k - 2][1] and org_p > piv[k - 3][1]))
        if p["SESSION_EXT_TOL"] >= 0 and not (TS._stair_or_session() and stair):
            if direction == "SHORT":
                if ext_p > min(bars[j]["l"] for j in range(0, i + 1)) + p["SESSION_EXT_TOL"]:
                    best = best or "not_session_extreme"
                    continue
            else:
                if ext_p < max(bars[j]["h"] for j in range(0, i + 1)) - p["SESSION_EXT_TOL"]:
                    best = best or "not_session_extreme"
                    continue
        pause = i - ext_i
        if not (p["PAUSE_MIN"] <= pause <= p["PAUSE_MAX"]):
            best = best or "pause_bars"
            continue
        if direction == "SHORT":
            pe = max(bars[j]["h"] for j in range(ext_i, i + 1))
            retr = (pe - ext_p) / imp
        else:
            pe = min(bars[j]["l"] for j in range(ext_i, i + 1))
            retr = (ext_p - pe) / imp
        if not (p["RETR_MIN"] <= retr <= p["RETR_MAX"]):
            best = best or "retracement"
            continue
        ln, lp = bars[i].get("lsma"), bars[max(0, i - 3)].get("lsma")
        if ln is None or lp is None:
            best = best or "no_lsma"
            continue
        slope = (ln - lp) / 3.0
        if (direction == "SHORT" and slope > -p["LSMA_SLOPE_MIN"]) or \
           (direction == "LONG" and slope < p["LSMA_SLOPE_MIN"]):
            best = best or "lsma_slope"
            continue
        iv = [bars[j].get("v", 0) for j in range(org_i + 1, ext_i + 1)]
        pv = [bars[j].get("v", 0) for j in range(ext_i + 1, i + 1)]
        if iv and pv and sum(iv) and (sum(pv) / len(pv)) / (sum(iv) / len(iv)) > p["VOL_RATIO_MAX"]:
            best = best or "vol_ratio"
            continue
        cnt["PASS"] += 1
        return
    cnt[best or "no_leg"] += 1


# ==================================================================== sim
TIER = {"TREND_STEP": 0, "GB100": 1, "HTLB": 1, "DOUBLE_BOTTOM_EE": 1,
        "REACTIVE": 2, "ZLR": 3, "INITIATIVE": 3, "GHOST": 4}


def sim_stream(bars, cands, thr, contracts, slip=SLIP, tier_priority=False, slots=1):
    """N positions at a time (default 1), chronological, MEMS ladder.

    tier_priority: when two candidates land on the SAME bar the higher tier wins
    (causal — no look-ahead).  Otherwise pure chronological, as the live gateway.
    slots: how many concurrent positions are allowed (1 = today's rule).
    """
    ORA.SLIP_TICKS = slip
    ORA.CONTRACTS = contracts
    cs = sorted(cands, key=(lambda x: (x["i"], TIER.get(x["kind"], 9)))
                if tier_priority else (lambda x: x["i"]))
    out, busy, seen_bar = [], [], -1
    for cd in cs:
        busy = [b for b in busy if b >= cd["i"]]
        if len(busy) >= slots:
            continue
        if tier_priority and cd["i"] == seen_bar:
            continue
        r = ORA.sim_ladder(bars, cd["i"], cd["dir"], thr, contracts)
        if not r:
            continue
        r["kind"] = cd["kind"]
        out.append(r)
        busy.append(r["exit_i"])
        seen_bar = cd["i"]
    ORA.SLIP_TICKS = 1
    ORA.CONTRACTS = 4
    return out


def agg(perday, trades):
    tot = round(sum(perday.values()), 2)
    wins = sum(1 for t in trades if t["usd"] > 0)
    return dict(n=len(trades), usd=tot,
                win=(round(100.0 * wins / len(trades), 1) if trades else 0.0),
                per_day=round(tot / max(1, len(perday)), 2),
                median_day=med(list(perday.values())),
                pos=sum(1 for v in perday.values() if v > 0),
                neg=sum(1 for v in perday.values() if v < 0))


# ==================================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/gpf.json")
    ap.add_argument("--fast", action="store_true",
                    help="skip the funnel + the detector arms; run the "
                         "contention/leave-one-out block only")
    a = ap.parse_args()
    if a.fast:
        for k in list(ARM_DEFS):
            if k not in ("LIVE", "RG1 tol 0.15ATR"):
                ARM_DEFS.pop(k)

    global FMS, CAL
    from backend.v9.systems.five_min import five_min_system as _FMS
    FMS = _FMS
    from backend.v9.config_loader import load_s2_reactive_calibration, load_s2_firing
    CAL = load_s2_reactive_calibration

    cn = psycopg2.connect(DSN)
    cn.set_session(readonly=True)
    cur = cn.cursor()
    days = ESR.load_bars(cur)
    ds = ESR.live_days(days)
    print(f"[env] {_N_ENV} keys | S2_VSA_VOLUME={os.environ.get('S2_VSA_VOLUME')} "
          f"variant={load_s2_firing()} S2_ADAPTIVE={os.environ.get('S2_ADAPTIVE_THRESHOLDS_V1')} "
          f"S2_REACTIVE_DAYTYPE={os.environ.get('S2_REACTIVE_DAYTYPE_V1')} "
          f"CVD={os.environ.get('S2_CVD_DETECTION_V1')} "
          f"TREND_STEP={os.environ.get('TREND_STEP_ENTRY_V1')}/"
          f"{os.environ.get('TREND_STEP_STAIR_OR_V1')}")
    print(f"[data] sessions={len(ds)}  {ds[0]}..{ds[-1]}")

    # make the live day-type source causal, so S2_REACTIVE_DAYTYPE_V1 geometry
    # tolerance is evaluated with the label the system would have carried.
    import backend.v9.services.trade_context as TC
    shim = S2Shim()
    _cur_lab = {"v": None}
    # the live get_live_day_type() must track the SAME causal label the shim
    # carries on every bar — otherwise S2_REACTIVE_DAYTYPE_V1's geometry
    # tolerance is evaluated against a stale label (fidelity bug, found 08-22).
    TC.get_live_day_type = lambda: shim.current_day_type

    cur.execute("""
        select (ts at time zone 'America/New_York') as et, open, high, low, close,
               coalesce(volume,0), coalesce(cci_14,0), coalesce(cci_6_tcci,0),
               coalesce(ema_34,0), coalesce(lsma_value,0), coalesce(swi_value,0),
               coalesce(czi_value,0), coalesce(trend_state,'GRAY'),
               coalesce(lsma_above_price,0), lsma_value
        from v9_bars_5min_woodies
        where (ts at time zone 'America/New_York')::date between %s and %s
          and (ts at time zone 'America/New_York')::time >= %s
          and (ts at time zone 'America/New_York')::time <  %s
        order by ts""", (ESR.WARM, D1, ESR.RTH0, ESR.RTH1))
    from backend.v9.systems.woodies.schemas import WoodiesBar
    wdays, tsdays = collections.OrderedDict(), collections.OrderedDict()
    for (et, o, h, l, c, v, c14, c6, e34, lsma, swi, czi, tstate, labove, lraw) in cur.fetchall():
        wdays.setdefault(et.date(), []).append(WoodiesBar(
            ts=et.timestamp(), open=float(o), high=float(h), low=float(l),
            close=float(c), volume=float(v), cci_14=float(c14), cci_6_tcci=float(c6),
            ema_34=float(e34), lsma_value=float(lsma), swi_value=float(swi),
            czi_value=float(czi), trend_state=tstate, lsma_above_price=bool(labove)))
        tsdays.setdefault(et.date(), []).append(dict(
            o=float(o), h=float(h), l=float(l), c=float(c), v=float(v),
            lsma=(float(lraw) if lraw is not None else None),
            hhmm=et.strftime("%H:%M")))

    cur.execute("select ts, cumulative from v9_bars_cumulative_delta "
                "where left(ts,10) between %s and %s order by ts", (D0, D1))
    cvd_by_day = collections.defaultdict(list)
    ncvd = 0
    for k, val in cur.fetchall():
        if val is None:
            continue
        cvd_by_day[k[:10]].append((k, float(val)))
        ncvd += 1
    print(f"[cvd] rows={ncvd} days={len(cvd_by_day)} (S2_CVD_DETECTION_V1 source)")

    thr = {d: ORA.thr_for(days, d) for d in ds}
    print("[labels] causal 7-type classifier, bar by bar ...")
    labs = {d: ESR.causal_labels(days, d, days[d]) for d in ds}

    res = {"sessions": [str(x) for x in ds]}

    # =================================================== 1 · detector funnel
    print("\n[funnel] condition census + leave-one-out (live thresholds) ...")
    RC, LOO, TOT = collections.Counter(), collections.Counter(), collections.Counter()
    nums = collections.defaultdict(list)
    for d in (ds if not a.fast else []):
        shim._cvd_sorted = cvd_by_day.get(str(d), [])
        bars = days[d]
        for i in range(6, len(bars)):
            shim._current_atr_5m = ESR.atr5(bars, i)
            lab = ESR.norm_dt(labs[d][i])
            shim.current_day_type = lab
            buf = [_mk_bar(b) for b in bars[max(0, i - WINDOW + 1):i + 1]]
            if len(buf) < 7:
                continue
            b1, b2, b3, b4 = buf[-4], buf[-3], buf[-2], buf[-1]
            atr = shim._current_atr_5m or 2.0
            _b2_drop.atr = atr
            cal = CAL(lab)
            drop = _b2_drop(buf, "live", cal)
            vad = FMS.vol_adaptive_active(buf)
            tol = float(cal.get("geometry", {}).get("confirm_tol_atr", 0.0)) * atr
            thrL = FMS.reactive_confirm_threshold(b3["h"], b3["l"], "LONG", vad)
            thrS = FMS.reactive_confirm_threshold(b3["h"], b3["l"], "SHORT", vad)
            b1r, b3r = b1["h"] - b1["l"], b3["h"] - b3["l"]
            emin, emax = FMS.get_expansion_range(buf)
            if vad:
                emin = min(emin, FMS._VOL_EXP_FLOOR_CAP_PT)
            exp_ok = emin <= b1r <= emax
            floor = emin
            if FMS.s2_adaptive_thresholds_on():
                fl = FMS.adaptive_expansion_floor(buf, atr14=shim._current_atr_5m,
                                                  day_type=lab)
                if fl is not None:
                    exp_ok, floor = b1r >= fl, fl
            jreq = b1r * (FMS._VOL_JOIN_FACTOR if vad else 1.0)
            if os.environ.get("S2_INITIATIVE_JOIN_ATR_CAP_V1", "").lower() in ("1", "true", "yes"):
                jreq = min(jreq, 0.55 * (shim._current_atr_5m or 5.0))
            vecs = {
                "REACTIVE_LONG": dict(b1_sellers=(b1["c"] < b1["o"] and b1["v"] > 0),
                                      b2_drop=drop, b3_buyers=(b3["c"] > b3["o"]),
                                      b4_confirm=(b4["c"] > b4["o"]),
                                      b4_beyond=(b4["c"] >= thrL - tol)),
                "REACTIVE_SHORT": dict(b1_buyers=(b1["c"] > b1["o"] and b1["v"] > 0),
                                       b2_drop=drop, b3_sellers=(b3["c"] < b3["o"]),
                                       b4_confirm=(b4["c"] < b4["o"]),
                                       b4_beyond=(b4["c"] <= thrS + tol)),
                "INITIATIVE_LONG": dict(b1_bull=(b1["c"] > b1["o"]), b1_exp=exp_ok,
                                        b2_test=(b2["l"] > b1["l"]), b3_join=(b3r > jreq),
                                        b4_test=(b4["l"] >= b2["l"]),
                                        b4_beyond=(b4["c"] > b1["h"])),
                "INITIATIVE_SHORT": dict(b1_bear=(b1["c"] < b1["o"]), b1_exp=exp_ok,
                                         b2_test=(b2["h"] < b1["h"]), b3_join=(b3r > jreq),
                                         b4_test=(b4["h"] <= b2["h"]),
                                         b4_beyond=(b4["c"] < b1["l"])),
            }
            for tag, vec in vecs.items():
                TOT[tag] += 1
                fails = [k for k, v in vec.items() if not v]
                for k, v in vec.items():
                    if v:
                        RC[f"{tag}.{k}"] += 1
                if len(fails) == 1:
                    LOO[f"{tag}.{fails[0]}"] += 1
                elif not fails:
                    LOO[f"{tag}.PASS_ALL"] += 1
            nums["b1_range"].append(b1r)
            nums["exp_floor"].append(floor)
            nums["b3_range"].append(b3r)
            nums["join_req"].append(jreq)
            nums["confirm_tol_pt"].append(tol)
    res["cond_pass"], res["cond_sole"], res["cond_tot"] = dict(RC), dict(LOO), dict(TOT)
    res["nums"] = {k: dict(p10=round(statistics.quantiles(v, n=10)[0], 2),
                           med=round(statistics.median(v), 2),
                           p90=round(statistics.quantiles(v, n=10)[8], 2))
                   for k, v in nums.items() if len(v) > 20}
    for tag in ("REACTIVE_LONG", "REACTIVE_SHORT", "INITIATIVE_LONG", "INITIATIVE_SHORT"):
        row = {k.split(".")[-1]: v for k, v in RC.items() if k.startswith(tag + ".")}
        sole = {k.split(".")[-1]: v for k, v in LOO.items() if k.startswith(tag + ".")}
        print(f"  {tag:<17} bars={TOT[tag]:5d} pass={dict(sorted(row.items(), key=lambda x: x[1]))}")
        print(f"  {'':17} SOLE={dict(sorted(sole.items(), key=lambda x: -x[1]))}")
    print("  nums:", json.dumps(res["nums"]))

    # =================================================== 2 · arms
    print("\n[scan] S2 arms (live detector first, arm as additive post-pass) ...")
    sc = {"bars": 0, "mismatch": 0}
    s2 = {}
    for arm in ARM_DEFS:
        allf = {}
        for d in ds:
            shim._cvd_sorted = cvd_by_day.get(str(d), [])
            allf[d] = scan_s2(days[d], labs[d], shim, arm,
                              selfcheck=(sc if arm == "LIVE" else None))
        s2[arm] = allf
        kk = collections.Counter(f["kind"] for v in allf.values() for f in v)
        extra = sum(1 for v in allf.values() for f in v if f["src"].startswith("arm"))
        print(f"  {arm:<17} fires={sum(len(v) for v in allf.values()):4d} "
              f"(+{extra} from the arm)  {dict(kk)}")
    print(f"[selfcheck] mirror vs LIVE _detect_reactive: bars={sc['bars']} "
          f"mismatches={sc['mismatch']}")
    res["selfcheck"] = sc

    dbt19 = {d: scan_chart(days[d], labs[d], shim, "DOUBLE_BOTTOM_EE") for d in ds}
    dbt32 = {d: scan_chart(days[d], labs[d], shim, "DOUBLE_BOTTOM_EE", window=32) for d in ds}
    print(f"  DOUBLE_BOTTOM_EE win19={sum(len(v) for v in dbt19.values())} "
          f"win32={sum(len(v) for v in dbt32.values())}")

    s4, s4r = {}, {}
    for pid in ("ZLR", "GB100", "GHOST", "HTLB"):
        rr = collections.Counter()
        s4[pid] = {d: scan_woodies(wdays[d], pid, rr) for d in ds}
        s4r[pid] = dict(rr.most_common(8))
        print(f"  S4 {pid:<6} fires={sum(len(v) for v in s4[pid].values()):4d} "
              f"rejects={list(rr.most_common(3))}")
    res["s4_rejects"] = s4r

    tstage = collections.Counter()
    TSA = collections.OrderedDict([
        ("LIVE", None),
        ("TSA imp>=6", dict(IMP_MIN=6.0)),
        ("TSB pause<=4", dict(PAUSE_MAX=4)),
        ("TSC retr .15-.65", dict(RETR_MIN=0.15, RETR_MAX=0.65)),
        ("TSD cutoff 15:30", dict(CUTOFF="15:30")),
        ("TSE zz 4.0", dict(ZZ_REV=4.0)),
        ("TSB+TSD", dict(PAUSE_MAX=4, CUTOFF="15:30")),
        ("TSA+TSB+TSD", dict(IMP_MIN=6.0, PAUSE_MAX=4, CUTOFF="15:30")),
    ])
    if a.fast:
        for k in list(TSA):
            if k not in ("LIVE", "TSB+TSD"):
                TSA.pop(k)
    ts = {}
    for nm, rl in TSA.items():
        ts[nm] = {d: scan_trend_step(tsdays[d], tstage if nm == "LIVE" else None, rl)
                  for d in ds}
        print(f"  TREND_STEP {nm:<18} fires={sum(len(v) for v in ts[nm].values()):4d}")
    res["ts_stage"] = dict(tstage.most_common(14))
    print("  TREND_STEP first-failing-condition census:", dict(tstage.most_common(9)))

    # =================================================== 3 · isolated $
    def iso(allf, label):
        row = {"fires": sum(len(v) for v in allf.values())}
        for c in SIZES:
            perday, trs = {}, []
            for d in ds:
                t = sim_stream(days[d], allf[d], thr[d], c)
                trs += t
                perday[str(d)] = round(sum(x["usd"] for x in t), 2)
            row[f"c{c}"] = agg(perday, trs)
            if c == 6:
                row["jul"] = round(sum(v for k, v in perday.items() if k[5:7] == "07"), 2)
                row["aug"] = round(sum(v for k, v in perday.items() if k[5:7] == "08"), 2)
        for s in (0, 2):
            row[f"s{s}"] = round(sum(
                sum(x["usd"] for x in sim_stream(days[d], allf[d], thr[d], 6, s))
                for d in ds), 2)
        print(f"[ISO] {label:<22} n={row['fires']:4d} c4=${row['c4']['usd']:>9.2f} "
              f"c6=${row['c6']['usd']:>9.2f} win={row['c6']['win']:>5.1f}% "
              f"med/d=${row['c6']['median_day']:>7.2f} Jul=${row['jul']:>8.2f} "
              f"Aug=${row['aug']:>8.2f} s0=${row['s0']:>8.2f} s2=${row['s2']:>8.2f}")
        return row

    print("\n[iso] isolated economics, 34 sessions, one slot, MEMS ladder ...")
    res["iso"] = {}
    for arm in ARM_DEFS:
        res["iso"][f"S2 {arm}"] = iso(s2[arm], f"S2 {arm}")
    res["iso"]["DBT win19"] = iso(dbt19, "DBT win19 (live)")
    res["iso"]["DBT win32"] = iso(dbt32, "DBT win32 (F5)")
    for pid in ("ZLR", "GB100", "GHOST", "HTLB"):
        res["iso"][f"S4 {pid}"] = iso(s4[pid], f"S4 {pid}")
    for nm in TSA:
        res["iso"][f"TS {nm}"] = iso(ts[nm], f"TS {nm}")

    # =================================================== 4 · joint, one slot
    print("\n[joint] base = the live producer set, one slot, real contention ...")

    def build(s2arm, dbtset, tsset, drop=(), with_trend=False):
        out = {}
        for d in ds:
            c = [x for x in s2[s2arm][d] if x["kind"] not in drop]
            c += [x for x in dbtset[d] if "DOUBLE_BOTTOM_EE" not in drop]
            for pid in ("ZLR", "GB100", "GHOST", "HTLB"):
                if pid in drop:
                    continue
                c += s4[pid][d]
            if "TREND_STEP" not in drop:
                c += tsset[d]
            if with_trend:
                c = [x for x in c if _with_trend(days[d], labs[d], x)]
            out[d] = sorted(c, key=lambda x: x["i"])
        return out

    def _with_trend(bars, labels, cand):
        """RESPONSIVE_WITH_DAY_TREND-style filter on the S2 4-bar family only:
        skip REACTIVE/INITIATIVE taken against the causal day-type direction."""
        if cand["kind"] not in ("REACTIVE", "INITIATIVE"):
            return True
        lab = ESR.norm_dt(labels[cand["i"]]) or ""
        if lab == "Trend_Normal":
            return cand["dir"] > 0
        if lab == "Trend_DD":
            return cand["dir"] < 0
        return True

    def run(stream, c, tier=False, slots=1):
        perday, trs, kinds, kusd = {}, [], collections.Counter(), collections.Counter()
        for d in ds:
            t = sim_stream(days[d], stream[d], thr[d], c, tier_priority=tier, slots=slots)
            trs += t
            for x in t:
                kinds[x["kind"]] += 1
                kusd[x["kind"]] += x["usd"]
            perday[str(d)] = round(sum(x["usd"] for x in t), 2)
        return perday, trs, kinds, {k: round(v, 2) for k, v in kusd.items()}

    base_stream = build("LIVE", dbt19, ts["LIVE"])
    base_pd = {}
    res["joint"] = {}
    for c in SIZES:
        pd0, t0, k0, u0 = run(base_stream, c)
        base_pd[c] = pd0
        res["joint"][f"base_c{c}"] = agg(pd0, t0) | {"kinds": dict(k0), "usd_by_kind": u0}
        res["joint"][f"base_perday_c{c}"] = pd0
        print(f"[BASE] c{c} " + json.dumps(res["joint"][f"base_c{c}"], default=str))
    res["joint"]["base_jul"] = round(sum(v for k, v in base_pd[6].items() if k[5:7] == "07"), 2)
    res["joint"]["base_aug"] = round(sum(v for k, v in base_pd[6].items() if k[5:7] == "08"), 2)
    res["joint"]["base_worst"] = min(base_pd[6].items(), key=lambda x: x[1])
    for s in (0, 2):
        res["joint"][f"base_s{s}"] = round(sum(
            sum(x["usd"] for x in sim_stream(days[d], base_stream[d], thr[d], 6, s))
            for d in ds), 2)
    print(f"[BASE] c6 Jul=${res['joint']['base_jul']} Aug=${res['joint']['base_aug']} "
          f"s0=${res['joint']['base_s0']} s2=${res['joint']['base_s2']} "
          f"worst={res['joint']['base_worst']}")

    LOO_DROPS = collections.OrderedDict([
        ("L-ZLR", ("ZLR",)), ("L-GHOST", ("GHOST",)), ("L-HTLB", ("HTLB",)),
        ("L-GB100", ("GB100",)), ("L-INITIATIVE", ("INITIATIVE",)),
        ("L-REACTIVE", ("REACTIVE",)), ("L-DBT", ("DOUBLE_BOTTOM_EE",)),
        ("L-TREND_STEP", ("TREND_STEP",)),
    ])
    COMBOS = collections.OrderedDict(
        [(f"{k} leave-one-out", dict(drop=v)) for k, v in LOO_DROPS.items()])
    COMBOS.update([
        ("A1 RV1 daytype-vol",  dict(s2arm="RV1 daytype-vol")),
        ("A2 RV2 b2<b1",        dict(s2arm="RV2 b2<b1 only")),
        ("A3 RG1 tol .15ATR",   dict(s2arm="RG1 tol 0.15ATR")),
        ("A4 RG2 confirm75",    dict(s2arm="RG2 confirm75")),
        ("A5 RV2+RG1",          dict(s2arm="RV2+RG1")),
        ("A6 IE1 exp x0.85",    dict(s2arm="IE1 exp x0.85")),
        ("A7 IG1 b4 75%",       dict(s2arm="IG1 b4 75%")),
        ("A8 S2-ALL",           dict(s2arm="S2-ALL")),
        ("B1 DBT win32",        dict(dbtset=dbt32)),
        ("C1 TS pause<=4",      dict(tsset=ts.get("TSB pause<=4", ts["LIVE"]))),
        ("C2 TS cutoff 15:30",  dict(tsset=ts.get("TSD cutoff 15:30", ts["LIVE"]))),
        ("C3 TS imp>=6",        dict(tsset=ts.get("TSA imp>=6", ts["LIVE"]))),
        ("C4 TS B+D",           dict(tsset=ts["TSB+TSD"])),
        ("C5 TS A+B+D",         dict(tsset=ts.get("TSA+TSB+TSD", ts["LIVE"]))),
        ("D1 drop GHOST",       dict(drop=("GHOST",))),
        ("D2 drop GHOST+ZLR",   dict(drop=("GHOST", "ZLR"))),
        ("D3 drop GHOST+INIT",  dict(drop=("GHOST", "INITIATIVE"))),
        ("D4 with-day-trend",   dict(with_trend=True)),
        ("E1 tier-priority",    dict(tier=True)),
        ("F1 D1+C4",            dict(drop=("GHOST",), tsset=ts["TSB+TSD"])),
        ("F2 D1+C4+E1",         dict(drop=("GHOST",), tsset=ts["TSB+TSD"], tier=True)),
        ("F3 D1+C4+B1",         dict(drop=("GHOST",), tsset=ts["TSB+TSD"], dbtset=dbt32)),
        ("F4 D1+C4+A3",         dict(drop=("GHOST",), tsset=ts["TSB+TSD"],
                                     s2arm="RG1 tol 0.15ATR")),
        ("F5 D1+C4+E1+A3",      dict(drop=("GHOST",), tsset=ts["TSB+TSD"], tier=True,
                                     s2arm="RG1 tol 0.15ATR")),
        ("F6 D3+C4+E1",         dict(drop=("GHOST", "INITIATIVE"),
                                     tsset=ts["TSB+TSD"], tier=True)),
        ("F7 D1+C4+E1+D4",      dict(drop=("GHOST",), tsset=ts["TSB+TSD"], tier=True,
                                     with_trend=True)),
        # --- G: contention / slot allocation, the lever the arms said matters
        ("G1 TS+GB100+HTLB+DBT+REACT",
         dict(drop=("GHOST", "ZLR", "INITIATIVE"))),
        ("G2 TS+GB100+DBT+REACT",
         dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB"))),
        ("G3 G1 + TS B+D", dict(drop=("GHOST", "ZLR", "INITIATIVE"),
                                tsset=ts["TSB+TSD"])),
        ("G4 G1 + with-trend", dict(drop=("GHOST", "ZLR", "INITIATIVE"),
                                    with_trend=True)),
        ("G5 G1 + tier", dict(drop=("GHOST", "ZLR", "INITIATIVE"), tier=True)),
        ("G6 G1 + RG1", dict(drop=("GHOST", "ZLR", "INITIATIVE"),
                             s2arm="RG1 tol 0.15ATR")),
        ("G7 G1 + TSB+TSD + with-trend",
         dict(drop=("GHOST", "ZLR", "INITIATIVE"), tsset=ts["TSB+TSD"],
              with_trend=True)),
        ("H1 BASE, 2 slots", dict(slots=2)),
        ("H2 G1, 2 slots", dict(drop=("GHOST", "ZLR", "INITIATIVE"), slots=2)),
        ("H3 G3, 2 slots", dict(drop=("GHOST", "ZLR", "INITIATIVE"),
                                tsset=ts["TSB+TSD"], slots=2)),
        ("G2b G2 + with-trend", dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB"),
                                     with_trend=True)),
        ("G2c G2 + TSB+TSD", dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB"),
                                  tsset=ts["TSB+TSD"])),
        ("G2d G2, 2 slots", dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB"),
                                 slots=2)),
        ("G8 TS+GB100+REACT", dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB",
                                         "DOUBLE_BOTTOM_EE"))),
        ("G9 TS+GB100 only", dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB",
                                        "DOUBLE_BOTTOM_EE", "REACTIVE"))),
    ])
    if a.fast:
        for nm in list(COMBOS):
            if nm[:2] in ("A1", "A2", "A4", "A5", "A6", "A7", "A8"):
                COMBOS.pop(nm)
    res["combos"] = {}
    for nm, kw in COMBOS.items():
        tier = kw.pop("tier", False)
        slots = kw.pop("slots", 1)
        st = build(kw.get("s2arm", "LIVE"), kw.get("dbtset", dbt19),
                   kw.get("tsset", ts["LIVE"]), kw.get("drop", ()),
                   kw.get("with_trend", False))
        row = {"slots": slots}
        for c in SIZES:
            pd1, t1, k1, u1 = run(st, c, tier, slots)
            delta = {d: round(pd1[d] - base_pd[c][d], 2) for d in pd1}
            row[f"c{c}"] = dict(
                total=round(sum(pd1.values()) - sum(base_pd[c].values()), 2),
                per_day=round((sum(pd1.values()) - sum(base_pd[c].values())) / len(pd1), 2),
                median_day=med(list(delta.values())),
                pos=sum(1 for v in delta.values() if v > 0),
                neg=sum(1 for v in delta.values() if v < 0),
                n=len(t1), abs_total=round(sum(pd1.values()), 2),
                abs_median_day=med(list(pd1.values())),
                worst_day=list(min(pd1.items(), key=lambda x: x[1])),
                jul=round(sum(v for k, v in delta.items() if k[5:7] == "07"), 2),
                aug=round(sum(v for k, v in delta.items() if k[5:7] == "08"), 2),
                abs_jul=round(sum(v for k, v in pd1.items() if k[5:7] == "07"), 2),
                abs_aug=round(sum(v for k, v in pd1.items() if k[5:7] == "08"), 2),
                kinds=dict(k1), usd_by_kind=u1)
        for s in (0, 2):
            tot = sum(sum(x["usd"] for x in sim_stream(days[d], st[d], thr[d], 6, s,
                                                       tier_priority=tier, slots=slots))
                      for d in ds)
            row[f"s{s}_delta"] = round(tot - res["joint"][f"base_s{s}"], 2)
        res["combos"][nm] = row
        r = row["c6"]
        print(f"[JOINT] {nm:<28} Δ=${r['total']:>9.2f} $/d={r['per_day']:>7.2f} "
              f"med=${r['median_day']:>7.2f} +/-={r['pos']}/{r['neg']} "
              f"|abs=${r['abs_total']:>9.2f} medAbs=${r['abs_median_day']:>7.2f} "
              f"Jul=${r['abs_jul']:>8.2f} Aug=${r['abs_aug']:>8.2f} "
              f"worst={r['worst_day'][0]}:{r['worst_day'][1]}")

    with open(a.json, "w") as f:
        json.dump(res, f, default=str)
    print("[out]", a.json)


if __name__ == "__main__":
    main()
