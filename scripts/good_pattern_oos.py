#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
good_pattern_oos.py — the honesty pass on top of good_pattern_fix.py.

TREND_STEP's parameters were fitted on the replay window 2026-07-15..08-12
(RULED_FLAGS.yaml TREND_STEP_ENTRY_V1: "replay 07-15..08-12: NET +$2,378.75").
Any 34-session number that includes that window is therefore part in-sample.
This script re-runs the same streams from good_pattern_fix.py and splits every
result three ways: IN-SAMPLE (07-15..08-12, 21 sessions), OUT-OF-SAMPLE
(07-07..07-14 + 08-13..08-21, 13 sessions), and July/August.

READ-ONLY. Imports good_pattern_fix.py as a module (no engine is rebuilt).
"""
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

_s = _ilu.spec_from_file_location("gpf", os.path.join(ROOT, "scripts", "good_pattern_fix.py"))
M = _ilu.module_from_spec(_s)
_s.loader.exec_module(M)

from backend.v9.systems.five_min import five_min_system as _FMS       # noqa: E402
from backend.v9.config_loader import load_s2_reactive_calibration     # noqa: E402
from backend.v9.systems.woodies.schemas import WoodiesBar             # noqa: E402
import backend.v9.services.trade_context as TC                        # noqa: E402

M.FMS = _FMS
M.CAL = load_s2_reactive_calibration

IS0, IS1 = dt.date(2026, 7, 15), dt.date(2026, 8, 12)   # TREND_STEP tuning window


def med(xs):
    return round(statistics.median(xs), 2) if xs else 0.0


def main():
    cn = psycopg2.connect("postgresql://localhost/mems26")
    cn.set_session(readonly=True)
    cur = cn.cursor()
    days = M.ESR.load_bars(cur)
    ds = M.ESR.live_days(days)

    shim = M.S2Shim()
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
        order by ts""", (M.ESR.WARM, M.D1, M.ESR.RTH0, M.ESR.RTH1))
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
                "where left(ts,10) between %s and %s order by ts", (M.D0, M.D1))
    cvd = collections.defaultdict(list)
    for k, val in cur.fetchall():
        if val is not None:
            cvd[k[:10]].append((k, float(val)))

    thr = {d: M.ORA.thr_for(days, d) for d in ds}
    print("[labels] causal classifier ...")
    labs = {d: M.ESR.causal_labels(days, d, days[d]) for d in ds}

    print("[scan] one pass ...")
    s2 = {}
    for d in ds:
        shim._cvd_sorted = cvd.get(str(d), [])
        s2[d] = M.scan_s2(days[d], labs[d], shim, "LIVE")
    dbt = {d: M.scan_chart(days[d], labs[d], shim, "DOUBLE_BOTTOM_EE") for d in ds}
    s4 = {p: {d: M.scan_woodies(wdays[d], p) for d in ds}
          for p in ("ZLR", "GB100", "GHOST", "HTLB")}
    tsl = {d: M.scan_trend_step(tsdays[d]) for d in ds}

    def with_trend(bars, labels, cd):
        if cd["kind"] not in ("REACTIVE", "INITIATIVE"):
            return True
        lab = M.ESR.norm_dt(labels[cd["i"]]) or ""
        if lab == "Trend_Normal":
            return cd["dir"] > 0
        if lab == "Trend_DD":
            return cd["dir"] < 0
        return True

    def build(drop=(), wt=False):
        out = {}
        for d in ds:
            c = [x for x in s2[d] if x["kind"] not in drop]
            c += [x for x in dbt[d] if "DOUBLE_BOTTOM_EE" not in drop]
            for p in ("ZLR", "GB100", "GHOST", "HTLB"):
                if p not in drop:
                    c += s4[p][d]
            if "TREND_STEP" not in drop:
                c += tsl[d]
            if wt:
                c = [x for x in c if with_trend(days[d], labs[d], x)]
            out[d] = sorted(c, key=lambda x: x["i"])
        return out

    # additive (2026-08-23): keep the per-trade rows so a caller can build a
    # per-DAY / per-TRADE table without re-running the engine. Pure capture —
    # no arm, threshold or stream is changed by it.
    TRADE_LOG = {}

    def run(stream, c=6, slots=1, slip=1, log_as=None):
        pd = {}
        kusd = collections.Counter()
        n = 0
        for d in ds:
            t = M.sim_stream(days[d], stream[d], thr[d], c, slip=slip, slots=slots)
            pd[d] = round(sum(x["usd"] for x in t), 2)
            n += len(t)
            for x in t:
                kusd[x["kind"]] += x["usd"]
            if log_as:
                TRADE_LOG.setdefault(log_as, {})[str(d)] = [
                    {k: v for k, v in x.items()
                     if k in ("kind", "dir", "usd", "entry", "stop", "exit",
                              "reason", "i", "pts", "risk", "mfe",
                              "t_in", "t_out")} for x in t]
        return pd, n, {k: round(v, 2) for k, v in kusd.items()}

    ARMS = collections.OrderedDict([
        ("BASE (live producer set)", dict()),
        ("D1 drop GHOST", dict(drop=("GHOST",))),
        ("D2 drop GHOST+ZLR", dict(drop=("GHOST", "ZLR"))),
        ("G1 -GHOST-ZLR-INIT", dict(drop=("GHOST", "ZLR", "INITIATIVE"))),
        ("G2 -GHOST-ZLR-INIT-HTLB", dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB"))),
        ("G2b G2 + with-day-trend", dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB"), wt=True)),
        ("G4 G1 + with-day-trend", dict(drop=("GHOST", "ZLR", "INITIATIVE"), wt=True)),
        ("G8 TS+GB100+REACT", dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB",
                                         "DOUBLE_BOTTOM_EE"))),
        ("G9 TS+GB100", dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB",
                                   "DOUBLE_BOTTOM_EE", "REACTIVE"))),
        ("X1 BASE no TREND_STEP", dict(drop=("TREND_STEP",))),
        ("X2 G2b no TREND_STEP", dict(drop=("GHOST", "ZLR", "INITIATIVE", "HTLB",
                                            "TREND_STEP"), wt=True)),
        ("X3 BASE - TS - GHOST", dict(drop=("TREND_STEP", "GHOST"))),
        ("X4 BASE - TS + with-trend", dict(drop=("TREND_STEP",), wt=True)),
        ("Y1 BASE 2 slots", dict(slots=2)),
        ("Y2 BASE-TS 2 slots", dict(drop=("TREND_STEP",), slots=2)),
        ("Y3 BASE 3 slots", dict(slots=3)),
        ("L-GB100", dict(drop=("GB100",))),
        ("L-HTLB", dict(drop=("HTLB",))),
        ("L-INITIATIVE", dict(drop=("INITIATIVE",))),
        ("L-ZLR", dict(drop=("ZLR",))),
        ("L-REACTIVE", dict(drop=("REACTIVE",))),
        ("L-DBT", dict(drop=("DOUBLE_BOTTOM_EE",))),
        ("D4 with-day-trend only", dict(wt=True)),
        ("X5 -TS -GB100", dict(drop=("TREND_STEP", "GB100"))),
        ("X6 -TS -GB100 +wt", dict(drop=("TREND_STEP", "GB100"), wt=True)),
        ("X7 -TS -GHOST +wt", dict(drop=("TREND_STEP", "GHOST"), wt=True)),
    ])
    base_pd = None
    out = {}
    hdr = (f"{'arm':<26}{'n':>4}{'total':>10}{'Δ':>10}{'IS(21)':>10}{'OOS(13)':>10}"
           f"{'Jul':>10}{'Aug':>10}{'medDay':>9}{'medΔ':>8}{'+/-':>8}{'worst':>10}")
    print("\n" + hdr)
    for nm, kw in ARMS.items():
        slots = kw.pop("slots", 1)
        st = build(**kw)
        pd6, n6, ku = run(st, 6, slots=slots,
                          log_as=(nm if nm.split()[0] in
                                  ("BASE", "X1", "X4", "D4") else None))
        if base_pd is None:
            base_pd = pd6
        delta = {d: round(pd6[d] - base_pd[d], 2) for d in pd6}
        IS = round(sum(v for d, v in pd6.items() if IS0 <= d <= IS1), 2)
        OOS = round(sum(v for d, v in pd6.items() if not (IS0 <= d <= IS1)), 2)
        dIS = round(sum(v for d, v in delta.items() if IS0 <= d <= IS1), 2)
        dOOS = round(sum(v for d, v in delta.items() if not (IS0 <= d <= IS1)), 2)
        jul = round(sum(v for d, v in pd6.items() if d.month == 7), 2)
        aug = round(sum(v for d, v in pd6.items() if d.month == 8), 2)
        worst = min(pd6.items(), key=lambda x: x[1])
        pd4, n4, _ = run(st, 4, slots=slots)
        s0 = sum(run(st, 6, slots=slots, slip=0)[0].values())
        s2s = sum(run(st, 6, slots=slots, slip=2)[0].values())
        out[nm] = dict(slots=slots, n=n6, total=round(sum(pd6.values()), 2),
                       delta=round(sum(delta.values()), 2),
                       IS=IS, OOS=OOS, dIS=dIS, dOOS=dOOS, jul=jul, aug=aug,
                       median_day=med(list(pd6.values())),
                       median_delta=med(list(delta.values())),
                       pos=sum(1 for v in delta.values() if v > 0),
                       neg=sum(1 for v in delta.values() if v < 0),
                       worst=[str(worst[0]), worst[1]],
                       c4_total=round(sum(pd4.values()), 2), c4_n=n4,
                       s0=round(s0, 2), s2=round(s2s, 2), usd_by_kind=ku,
                       perday={str(k): v for k, v in pd6.items()})
        r = out[nm]
        print(f"{nm:<26}{r['n']:>4}{r['total']:>10.2f}{r['delta']:>10.2f}"
              f"{r['IS']:>10.2f}{r['OOS']:>10.2f}{r['jul']:>10.2f}{r['aug']:>10.2f}"
              f"{r['median_day']:>9.2f}{r['median_delta']:>8.2f}"
              f"{str(r['pos'])+'/'+str(r['neg']):>8}{r['worst'][1]:>10.2f}")
        print(f"{'':26}Δ IS={r['dIS']:+.2f}  Δ OOS={r['dOOS']:+.2f} | "
              f"c4=${r['c4_total']:.2f} | s0=${r['s0']:.2f} s2=${r['s2']:.2f} | {ku}")

    # per-producer isolated IS/OOS
    print("\n[iso] per-producer, isolated, 6c, slip 1 — IS vs OOS")
    isols = {"TREND_STEP": tsl, "GB100": s4["GB100"], "HTLB": s4["HTLB"],
             "ZLR": s4["ZLR"], "GHOST": s4["GHOST"], "DOUBLE_BOTTOM_EE": dbt,
             "S2 (REACT+INIT)": s2}
    out["iso"] = {}
    for nm, f in isols.items():
        pd = {}
        n = 0
        w = 0
        for d in ds:
            t = M.sim_stream(days[d], f[d], thr[d], 6)
            pd[d] = round(sum(x["usd"] for x in t), 2)
            n += len(t)
            w += sum(1 for x in t if x["usd"] > 0)
        IS = round(sum(v for d, v in pd.items() if IS0 <= d <= IS1), 2)
        OOS = round(sum(v for d, v in pd.items() if not (IS0 <= d <= IS1)), 2)
        out["iso"][nm] = dict(n=n, total=round(sum(pd.values()), 2), IS=IS, OOS=OOS,
                              win=round(100.0 * w / max(1, n), 1),
                              jul=round(sum(v for d, v in pd.items() if d.month == 7), 2),
                              aug=round(sum(v for d, v in pd.items() if d.month == 8), 2),
                              median_day=med(list(pd.values())))
        r = out["iso"][nm]
        print(f"  {nm:<18} n={r['n']:4d} tot=${r['total']:>9.2f} IS=${r['IS']:>9.2f} "
              f"OOS=${r['OOS']:>9.2f} win={r['win']:>5.1f}% med/d=${r['median_day']:>7.2f} "
              f"Jul=${r['jul']:>8.2f} Aug=${r['aug']:>8.2f}")

    out["trade_log"] = TRADE_LOG
    with open("/tmp/gpf_oos.json", "w") as f:
        json.dump(out, f, default=str)
    print("\n[out] /tmp/gpf_oos.json")


if __name__ == "__main__":
    main()
