#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dead_pattern_replay.py — replay the OWN signal of every pattern that has NEVER
produced a live trade, over every live-era RTH session.

Michael (2026-08-22): "diagnose each dead-wired pattern one by one — what blocks
it, what the smallest fix is, and how much it would have been worth."

ENGINES ARE REUSED, NOT REBUILT
    scripts/oracle_study.py             -> bars, ATR, zigzag thr, sim_trade /
                                           sim_ladder, cost model
    scripts/entry_side_replay.py        -> session loader, live 19-bar detection
                                           window, causal 7-type labels, A2 dedup,
                                           one-slot sequencing
    backend/v9/systems/five_min/patterns/*      -> the LIVE S2 detectors
    backend/v9/systems/woodies/patterns/*       -> the LIVE S4 detectors
    backend/v9/systems/opening_entry.py         -> the LIVE opening triggers
    backend/v9/systems/edge_fade.py             -> the LIVE edge-fade trigger

READ-ONLY. Direct psycopg2, read-only session. Writes stdout + --json only.
Nothing here runs in, or is imported by, the live backend.

Usage:
    python3 scripts/dead_pattern_replay.py --json /tmp/dpr.json
    python3 scripts/dead_pattern_replay.py --only s4
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


# ---- load the LIVE flag set BEFORE importing any detector -----------------
def load_env(path=None):
    """Mirror .env into os.environ so every detector sees production flags."""
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
POINT_USD = 5.0
COMM_RT = 1.50
SLIP = 1                       # ticks/side — the headline slippage level
SIZES = (4, 6)                 # 4c = the replay convention; 6c = FIXED_CONTRACTS_6
WINDOW = ESR.LIVE_DET_WINDOW   # 19 = live _det_buf
DEDUP = ESR.DEDUP_COOLDOWN     # 30 bars per KIND_DIR (five_min_system A2)
IB_BARS = ESR.IB_BARS
WOODIES_BUF = 50               # woodies_system.max_buffer


def med(xs):
    return round(statistics.median(xs), 2) if xs else 0.0


# ============================================================ scanners
def _label_ok(lab):
    """chart_patterns_allowed with the live S2_CHART_ALL_DAYTYPES=1."""
    return bool(lab) and lab not in ("UNKNOWN", "Nontrend")


def scan_s2_chart(bars, labels, which, adam_fix=False):
    """Run ONE live Pkg-5a/5b detector in isolation, bar by bar, live window."""
    from backend.v9.systems.five_min.patterns import double_bt as DBT
    from backend.v9.systems.five_min.patterns import head_shoulders as HNS

    if not hasattr(DBT, "_ORIG_PEAK"):
        DBT._ORIG_PEAK = DBT._peak_width_bars
    # ADAM-FIX: give the Adam (peak) width test its own 2-tick tolerance instead
    # of sharing Eve's 0.75xATR (S2_ATR_RELATIVE=true).
    DBT._peak_width_bars = ((lambda b, i2, p, atr_5m=None: DBT._ORIG_PEAK(b, i2, p, None))
                            if adam_fix else DBT._ORIG_PEAK)

    fn = {"INVERSE_HNS": (HNS.detect_inverse_hns, False),
          "HNS_TOP": (HNS.detect_hns_top, False),
          "DOUBLE_BOTTOM_EE": (DBT.detect_double_bottom_ee, True),
          "DOUBLE_TOP_AA": (DBT.detect_double_top_aa, True)}[which]
    f, needs_atr = fn
    out, dedup = [], {}
    for i in range(12, len(bars)):
        if not _label_ok(ESR.norm_dt(labels[i])):
            continue
        a = ESR.atr5(bars, i)
        buf = bars[max(0, i - WINDOW + 1):i + 1]
        d, c, info = f(buf, atr_5m=a) if needs_atr else f(buf)
        if not d:
            continue
        key = f"{which}_{d}"
        if i - dedup.get(key, -999) < DEDUP:
            continue
        dedup[key] = i
        out.append(dict(i=i, dir=(1 if d == "LONG" else -1), kind=which,
                        conf=round(float(c), 2)))
    DBT._peak_width_bars = DBT._ORIG_PEAK
    return out


def scan_flags(bars, labels, which):
    """Pkg-5c BULL_FLAG / BEAR_FLAG, isolated."""
    from backend.v9.systems.five_min.patterns import flags as FL
    f = FL.detect_bull_flag if which == "BULL_FLAG" else FL.detect_bear_flag
    out, dedup = [], {}
    for i in range(12, len(bars)):
        if not _label_ok(ESR.norm_dt(labels[i])):
            continue
        buf = bars[max(0, i - WINDOW + 1):i + 1]
        d, c, info = f(buf)
        if not d:
            continue
        key = f"{which}_{d}"
        if i - dedup.get(key, -999) < DEDUP:
            continue
        dedup[key] = i
        out.append(dict(i=i, dir=(1 if d == "LONG" else -1), kind=which,
                        conf=round(float(c), 2)))
    return out


def scan_hlst(bars, labels):
    """HLST with HIGHER_LOW_SECOND_TEST_V1 forced ON (it is unset in .env)."""
    os.environ["HIGHER_LOW_SECOND_TEST_V1"] = "1"
    from backend.v9.systems.five_min.patterns import higher_low_second_test as H
    out, dedup = [], {}
    for i in range(12, len(bars)):
        # live chain: HLST runs in DAY_TYPE_MODE with no day-type gate of its own
        buf = bars[max(0, i - WINDOW + 1):i + 1]
        d, c, info = H.detect_higher_low_second_test_long(buf)
        if not d:
            d, c, info = H.detect_higher_low_second_test_short(buf)
        if not d:
            continue
        key = f"HLST_{d}"
        if i - dedup.get(key, -999) < DEDUP:
            continue
        dedup[key] = i
        out.append(dict(i=i, dir=(1 if d == "LONG" else -1), kind="HLST",
                        conf=round(float(c), 2)))
    return out


def scan_re_pullback(bars, labels):
    """RE_PULLBACK with the IB taken from the first 12 RTH bars (= the Sierra
    ib_high/ib_low the live path reads from tpo.json, ib_locked after 60 min)."""
    from backend.v9.systems.five_min.patterns import pullback_retest as PB
    ib = bars[:IB_BARS]
    ibh, ibl = max(b["h"] for b in ib), min(b["l"] for b in ib)
    out, dedup = [], {}
    for i in range(IB_BARS, len(bars)):
        session_min = i * 5
        buf = bars[max(0, i - WINDOW + 1):i + 1]
        d, c, info = PB.detect_pullback_retest(
            buf, ib_high=ibh, ib_low=ibl, ib_locked=True, session_min=session_min)
        if not d:
            continue
        key = f"RE_PULLBACK_{d}"
        if i - dedup.get(key, -999) < DEDUP:
            continue
        dedup[key] = i
        out.append(dict(i=i, dir=(1 if d == "LONG" else -1), kind="RE_PULLBACK",
                        conf=round(float(c), 2)))
    return out


def scan_woodies(wbars, pid):
    """Run ONE live S4 detector over the 50-bar woodies buffer, bar by bar."""
    from backend.v9.systems.woodies.patterns import tlb, tt, vegas, famir, ghost, hfe, zlr, gb100, htlb
    mod = dict(TLB=tlb, TT=tt, VEGAS=vegas, FAMIR=famir, GHOST=ghost,
               HFE=hfe, ZLR=zlr, GB100=gb100, HTLB=htlb)[pid]
    out, dedup = [], {}
    for i in range(14, len(wbars)):
        buf = wbars[max(0, i - WOODIES_BUF + 1):i + 1]
        try:
            r = mod.detect(buf, None)
        except Exception:
            continue
        if not r or not getattr(r, "detected", False):
            continue
        if r.stop is None or r.stop <= 0:      # T3 guard, woodies_system.py:464
            continue
        d = 1 if r.direction == "LONG" else -1
        key = f"{pid}_{r.direction}"
        if i - dedup.get(key, -999) < DEDUP:
            continue
        dedup[key] = i
        out.append(dict(i=i, dir=d, kind=pid,
                        conf=round(float(r.confidence or 0), 2)))
    return out


def scan_opening(bars, apply_gates=True):
    """The LIVE opening-trigger chain, bars 2..12 (OPENING_FIRE_V1=1)."""
    from backend.v9.systems.opening_entry import evaluate_opening_entry
    fired, out = set(), []
    win = 12 if os.environ.get("OPENING_FIRE_V1", "0").lower() in ("1", "true", "yes") else 6
    for n in range(2, min(win, len(bars)) + 1):
        seg = bars[:n]
        segd = [dict(o=b["o"], h=b["h"], l=b["l"], c=b["c"], v=b["v"]) for b in seg]
        t = evaluate_opening_entry(segd, fired, window_last_bar=win,
                                   enable_pullback=True, bias=None)
        if not t:
            continue
        fired.add(t["type"])
        out.append(dict(i=n - 1, dir=(1 if t["direction"] == "LONG" else -1),
                        kind="OPENING_" + t["type"], conf=0.6))
    return out


def scan_edge_fade(bars, labels):
    """The LIVE edge-fade trigger, evaluated on every closed RTH bar with the
    causal label (the live caller only reaches it inside FIRST_HOUR_TACTICAL —
    see the report; here we measure the pattern's own signal all session)."""
    from backend.v9.systems.edge_fade import evaluate_edge_fade
    fired, out = set(), []
    for i in range(6, len(bars)):
        lab = ESR.norm_dt(labels[i])
        seg = [dict(o=b["o"], h=b["h"], l=b["l"], c=b["c"], v=b["v"]) for b in bars[:i + 1]]
        t = evaluate_edge_fade(seg, lab, fired)
        if not t:
            continue
        fired.add(t.get("type", "EDGE_FADE"))
        out.append(dict(i=i, dir=(1 if t["direction"] == "LONG" else -1),
                        kind="EDGE_FADE", conf=0.6))
    return out


def scan_edge_fade_firsthour(bars, labels):
    """Same, but restricted to the window the LIVE caller can actually reach:
    FIRST_HOUR_TACTICAL == the first 12 bars of RTH."""
    return [f for f in scan_edge_fade(bars, labels) if f["i"] < 12]


# ============================================================ simulation
def sim_stream(bars, cands, thr, contracts, slip=SLIP):
    """One position at a time, chronological, MEMS ladder (1R/2R/3R + BE + trail)."""
    ORA.SLIP_TICKS = slip
    ORA.CONTRACTS = contracts
    out, busy = [], -1
    for cd in sorted(cands, key=lambda x: x["i"]):
        if cd["i"] <= busy:
            continue
        r = ORA.sim_ladder(bars, cd["i"], cd["dir"], thr, contracts)
        if not r:
            continue
        r["kind"] = cd["kind"]
        out.append(r)
        busy = r["exit_i"]
    ORA.SLIP_TICKS = 1
    ORA.CONTRACTS = 4
    return out


def agg(perday_usd, trades):
    tot = round(sum(perday_usd.values()), 2)
    wins = sum(1 for t in trades if t["usd"] > 0)
    return dict(n=len(trades), usd=tot,
                win=(round(100.0 * wins / len(trades), 1) if trades else 0.0),
                per_day=round(tot / max(1, len(perday_usd)), 2),
                median_day=med(list(perday_usd.values())),
                pos=sum(1 for v in perday_usd.values() if v > 0),
                neg=sum(1 for v in perday_usd.values() if v < 0))


# ============================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/dpr.json")
    ap.add_argument("--only", default="all")
    a = ap.parse_args()

    cn = psycopg2.connect(DSN)
    cn.set_session(readonly=True)
    cur = cn.cursor()
    days = ESR.load_bars(cur)
    ds = ESR.live_days(days)
    print(f"[env] {_N_ENV} keys from .env  |  S2_ATR_RELATIVE={os.environ.get('S2_ATR_RELATIVE')} "
          f"TLB_SPEC_V2={os.environ.get('TLB_SPEC_V2')} VEGAS_SPEC_V2={os.environ.get('VEGAS_SPEC_V2')}")
    print(f"[data] sessions={len(ds)}  {ds[0]}..{ds[-1]}")

    # woodies bars with the CCI studies straight from the canonical table
    cur.execute(
        """
        select (ts at time zone 'America/New_York') as et, open, high, low, close,
               coalesce(volume,0), coalesce(cci_14,0), coalesce(cci_6_tcci,0),
               coalesce(ema_34,0), coalesce(lsma_value,0), coalesce(swi_value,0),
               coalesce(czi_value,0), coalesce(trend_state,'GRAY'),
               coalesce(lsma_above_price,0)
        from v9_bars_5min_woodies
        where (ts at time zone 'America/New_York')::date between %s and %s
          and (ts at time zone 'America/New_York')::time >= %s
          and (ts at time zone 'America/New_York')::time <  %s
        order by ts
        """, (ESR.WARM, D1, ESR.RTH0, ESR.RTH1))
    from backend.v9.systems.woodies.schemas import WoodiesBar
    wdays = collections.OrderedDict()
    for (et, o, h, l, c, v, c14, c6, e34, lsma, swi, czi, tstate, labove) in cur.fetchall():
        wdays.setdefault(et.date(), []).append(WoodiesBar(
            ts=et.timestamp(), open=float(o), high=float(h), low=float(l),
            close=float(c), volume=float(v), cci_14=float(c14), cci_6_tcci=float(c6),
            ema_34=float(e34), lsma_value=float(lsma), swi_value=float(swi),
            czi_value=float(czi), trend_state=tstate,
            lsma_above_price=bool(labove)))

    thr = {d: ORA.thr_for(days, d) for d in ds}
    print("[labels] running the causal 7-type classifier bar-by-bar ...")
    labs = {d: ESR.causal_labels(days, d, days[d]) for d in ds}

    # ---------------- per-pattern isolated scans
    SCANS = {
        "DOUBLE_TOP_AA_SHORT (adam-fix)": lambda d: scan_s2_chart(days[d], labs[d], "DOUBLE_TOP_AA", adam_fix=True),
        "DOUBLE_TOP_AA_SHORT (as-is)":    lambda d: scan_s2_chart(days[d], labs[d], "DOUBLE_TOP_AA", adam_fix=False),
        "INVERSE_HNS_LONG":               lambda d: scan_s2_chart(days[d], labs[d], "INVERSE_HNS"),
        "HNS_TOP_SHORT":                  lambda d: scan_s2_chart(days[d], labs[d], "HNS_TOP"),
        "BULL_FLAG_LONG":                 lambda d: scan_flags(days[d], labs[d], "BULL_FLAG"),
        "HLST":                           lambda d: scan_hlst(days[d], labs[d]),
        "RE_PULLBACK":                    lambda d: scan_re_pullback(days[d], labs[d]),
        "TLB":                            lambda d: scan_woodies(wdays[d], "TLB"),
        "TT":                             lambda d: scan_woodies(wdays[d], "TT"),
        "VEGAS":                          lambda d: scan_woodies(wdays[d], "VEGAS"),
        "FAMIR":                          lambda d: scan_woodies(wdays[d], "FAMIR"),
        "HFE":                            lambda d: scan_woodies(wdays[d], "HFE"),
        "OPENING_*":                      lambda d: scan_opening(days[d]),
        "EDGE_FADE (all session)":        lambda d: scan_edge_fade(days[d], labs[d]),
        "EDGE_FADE (first hour only)":    lambda d: scan_edge_fade_firsthour(days[d], labs[d]),
    }

    res = {"sessions": [str(x) for x in ds], "iso": {}, "raw_fires": {}}
    fires_by_pat = {}
    for name, fn in SCANS.items():
        allf = {}
        for d in ds:
            try:
                allf[d] = fn(d)
            except Exception as e:
                allf[d] = []
                print(f"  !! {name} {d}: {e}")
        fires_by_pat[name] = allf
        nf = sum(len(v) for v in allf.values())
        row = {"fires": nf, "days_with_fire": sum(1 for v in allf.values() if v)}
        for c in SIZES:
            perday, trs = {}, []
            for d in ds:
                t = sim_stream(days[d], allf[d], thr[d], c)
                trs += t
                perday[str(d)] = round(sum(x["usd"] for x in t), 2)
            row[f"c{c}"] = agg(perday, trs)
            row[f"perday_c{c}"] = perday
        res["iso"][name] = row
        res["raw_fires"][name] = {str(d): [dict(i=f["i"], dir=f["dir"], kind=f["kind"],
                                                t=str(days[d][f["i"]]["t"]))
                                           for f in allf[d]] for d in ds if allf[d]}
        print(f"[ISO] {name:32s} fires={nf:4d} days={row['days_with_fire']:3d} "
              + " ".join(f"c{c}=${row[f'c{c}']['usd']:>9.2f} win={row[f'c{c}']['win']:>5.1f}% "
                         f"med/day=${row[f'c{c}']['median_day']:>7.2f}" for c in SIZES))

    # ---------------- OPENING split by trigger type
    op = collections.Counter()
    for d in ds:
        for f in fires_by_pat["OPENING_*"][d]:
            op[f["kind"]] += 1
    res["opening_split"] = dict(op)
    print("[OPENING split]", dict(op))
    for k in sorted(op):
        sub = {d: [f for f in fires_by_pat["OPENING_*"][d] if f["kind"] == k] for d in ds}
        row = {"fires": sum(len(v) for v in sub.values())}
        for c in SIZES:
            perday, trs = {}, []
            for d in ds:
                t = sim_stream(days[d], sub[d], thr[d], c)
                trs += t
                perday[str(d)] = round(sum(x["usd"] for x in t), 2)
            row[f"c{c}"] = agg(perday, trs)
        res["iso"][k] = row
        print(f"[ISO] {k:32s} fires={row['fires']:4d} "
              + " ".join(f"c{c}=${row[f'c{c}']['usd']:>9.2f} win={row[f'c{c}']['win']:>5.1f}%"
                         for c in SIZES))

    # ---------------- BASE stream = what fires TODAY
    #   S2 live Pkg-5a/5b chain (a0, chain order + dedup, the live code)
    #   + the S4 patterns that have produced live trades (ZLR / GB100 / GHOST / HTLB)
    print("[base] building today's live candidate stream ...")
    base = {}
    for d in ds:
        c = ESR.e1_scan_session(days[d], labs[d], 0.0, 2, adam_fix=False)
        for pid in ("ZLR", "GB100", "GHOST", "HTLB"):
            c += scan_woodies(wdays[d], pid)
        base[d] = sorted(c, key=lambda x: x["i"])
    nb = sum(len(v) for v in base.values())
    print(f"[base] candidates={nb}")

    def run_stream(extra_names, contracts):
        perday, trs, kinds = {}, [], collections.Counter()
        for d in ds:
            cands = list(base[d])
            for nm in extra_names:
                cands += fires_by_pat[nm][d]
            t = sim_stream(days[d], cands, thr[d], contracts)
            trs += t
            for x in t:
                kinds[x["kind"]] += 1
            perday[str(d)] = round(sum(x["usd"] for x in t), 2)
        return perday, trs, kinds

    res["joint"] = {}
    for c in SIZES:
        pd0, t0, k0 = run_stream([], c)
        res["joint"][f"base_c{c}"] = agg(pd0, t0) | {"kinds": dict(k0)}
        res["joint"][f"base_perday_c{c}"] = pd0
        print(f"[BASE] c{c} " + json.dumps(res['joint'][f'base_c{c}'], default=str))

    # ---------------- single-pattern ADD to the live stream (slot contention real)
    ADDABLE = ["DOUBLE_TOP_AA_SHORT (adam-fix)", "INVERSE_HNS_LONG", "HNS_TOP_SHORT",
               "BULL_FLAG_LONG", "HLST", "RE_PULLBACK", "TLB", "TT", "VEGAS",
               "FAMIR", "HFE", "OPENING_*", "EDGE_FADE (all session)",
               "EDGE_FADE (first hour only)"]
    res["added"] = {}
    for nm in ADDABLE:
        row = {}
        for c in SIZES:
            pdb = res["joint"][f"base_perday_c{c}"]
            pd1, t1, k1 = run_stream([nm], c)
            delta = {d: round(pd1[d] - pdb[d], 2) for d in pdb}
            row[f"c{c}"] = dict(total=round(sum(pd1.values()) - sum(pdb.values()), 2),
                                per_day=round((sum(pd1.values()) - sum(pdb.values())) / len(pdb), 2),
                                median_day=med(list(delta.values())),
                                pos=sum(1 for v in delta.values() if v > 0),
                                neg=sum(1 for v in delta.values() if v < 0),
                                n=len(t1))
        res["added"][nm] = row
        print(f"[ADD] {nm:32s} " + " ".join(
            f"c{c}=Δ${row[f'c{c}']['total']:>9.2f} med/day=${row[f'c{c}']['median_day']:>7.2f} "
            f"+/-={row[f'c{c}']['pos']}/{row[f'c{c}']['neg']}" for c in SIZES))

    # ---------------- slip sensitivity + month split on the ISO runs
    res["slip"] = {}
    res["month"] = {}
    for nm in ADDABLE:
        allf = fires_by_pat[nm]
        row_s, row_m = {}, {}
        for slip in (0, 1, 2):
            tot = 0.0
            for d in ds:
                tot += sum(x["usd"] for x in sim_stream(days[d], allf[d], thr[d], 6, slip))
            row_s[f"s{slip}"] = round(tot, 2)
        jul = aug = 0.0
        for d in ds:
            u = sum(x["usd"] for x in sim_stream(days[d], allf[d], thr[d], 6, SLIP))
            if d.month == 7:
                jul += u
            else:
                aug += u
        row_m = dict(jul=round(jul, 2), aug=round(aug, 2))
        res["slip"][nm] = row_s
        res["month"][nm] = row_m
        print(f"[SENS] {nm:32s} c6 s0=${row_s['s0']:>9.2f} s1=${row_s['s1']:>9.2f} "
              f"s2=${row_s['s2']:>9.2f} | Jul=${row_m['jul']:>9.2f} Aug=${row_m['aug']:>9.2f}")

    # ---------------- joint revivals (triples), run TOGETHER
    import itertools
    ranked = sorted(ADDABLE, key=lambda n: -res["added"][n]["c6"]["total"])
    pool = [n for n in ranked if n not in ("HFE", "INVERSE_HNS_LONG",
                                           "EDGE_FADE (first hour only)")][:6]
    print("[joint] pool =", pool)
    res["triples"] = {}
    for combo in itertools.combinations(pool, 3) if len(pool) >= 3 else []:
        row = {}
        for c in SIZES:
            pdb = res["joint"][f"base_perday_c{c}"]
            pd1, t1, k1 = run_stream(list(combo), c)
            delta = {d: round(pd1[d] - pdb[d], 2) for d in pdb}
            row[f"c{c}"] = dict(total=round(sum(pd1.values()) - sum(pdb.values()), 2),
                                per_day=round((sum(pd1.values()) - sum(pdb.values())) / len(pdb), 2),
                                median_day=med(list(delta.values())),
                                pos=sum(1 for v in delta.values() if v > 0),
                                neg=sum(1 for v in delta.values() if v < 0),
                                n=len(t1), kinds=dict(k1))
        res["triples"][" + ".join(combo)] = row
        print(f"[TRIPLE] {' + '.join(combo)[:58]:58s} "
              + " ".join(f"c{c}=Δ${row[f'c{c}']['total']:>9.2f} med=${row[f'c{c}']['median_day']:>7.2f}"
                         for c in SIZES))

    with open(a.json, "w") as f:
        json.dump(res, f, default=str)
    print("[out]", a.json)


if __name__ == "__main__":
    main()
