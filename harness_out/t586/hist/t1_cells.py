#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super-agent T1 (Michael 18.10 16:5x: "כלל כניסה לעסקה תביא לנו T1 … לא יורדים מ-80 אחוז הצלחה").
Per doctrine CELL on a candidate universe (cand_sim.py output of an all_take run): n, T1-hit rate (leg 1 reaches
the system's own T1 — with the live 1.5R floor — before the stop), net$ (1 contract, leg 1). Then a WALK-FORWARD
policy: for month M the cells are chosen only from candidates BEFORE M (n >= NMIN and T1-rate >= RATE); applied to
M slot-aware (one trade at a time). Forward numbers are the only ones that count; hindsight is printed as 'ceiling'.
usage: t1_cells.py <cand.csv> [--rate=0.80] [--nmin=25] [--key=opening_type,phase,day_type,kind,zone]
                   [--maxr=20] [--from=YYYY-MM] [--to=YYYY-MM] [--out=<policy.json>] [--first=<n months warm-up>]"""
import sys, json, collections, pandas as pd
f = next(a for a in sys.argv[1:] if not a.startswith("--"))
opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
RATE = float(opt.get("rate", 0.80)); NMIN = int(opt.get("nmin", 25)); MAXR = float(opt.get("maxr", 20))
KEY = opt.get("key", "opening_type,phase,day_type,kind,zone").split(",")
df = pd.read_csv(f).fillna({"kind": "?", "opening_type": "?", "phase": "?", "day_type": "?", "rel_bias": "?", "zone": "?"})
df["month"] = df["session"].str[:7]
if opt.get("from"): df = df[df.month >= opt["from"]]
if opt.get("to"): df = df[df.month <= opt["to"]]
df["m"] = df["il"].str[:2].astype(int) * 60 + df["il"].str[3:5].astype(int)
df["xm"] = df["exit_il"].astype(str).str[:2].astype(int) * 60 + df["exit_il"].astype(str).str[3:5].astype(int)
df["gate_ok"] = df["blocked_by"].fillna("").astype(str).isin(["", "nan"])
df["t1"] = (df["exit"] == "T1").astype(int)
if "r_pts" in df: df = df[(df.r_pts > 0) & (df.r_pts <= MAXR)]          # broken setups (stop 0 / absurd R) out
df["cell"] = df[KEY].astype(str).agg("|".join, axis=1)
elig = df.gate_ok & (df.get("shadow_only", 0) == 0) & ((df.taken == 1) | (df.live_blocked_by.fillna("") == "live_slot_occupied"))
U = df[elig].sort_values(["session", "m"]).reset_index(drop=True)   # live-eligible: the gates stay, shadow-only setups and NO_LABEL routings are out
def slot_run(sub, admit):
    tot = 0.0; n = 0; t1 = 0
    for s, g in sub.groupby("session", sort=True):
        busy = -1
        for r in g.itertuples():
            if r.m < busy or not admit(r): continue
            tot += r.net; n += 1; t1 += r.t1; busy = max(r.xm, r.m + 5)
    return tot, n, t1
months = sorted(U.month.unique())
print(f"{len(df)} candidates (R<={MAXR}) · gate-passed {len(U)} · {U.session.nunique()} sessions · {months[0]}..{months[-1]} · key={KEY} rate>={RATE} nmin>={NMIN}")
print(f"{'month':8s} {'sess':>4s} | {'FIXED tree: net (n) T1%':>24s} | {'WF T1-cells: net (n) T1%':>25s} | cells")
tot = collections.defaultdict(float); cnt = collections.defaultdict(int); hit = collections.defaultdict(int); last_good = set()
for M in months:
    train = U[U.month < M]; test = U[U.month == M]
    st = train.groupby("cell").agg(n=("t1", "size"), rate=("t1", "mean"), net=("net", "mean"))
    good = set(st[(st.n >= NMIN) & (st.rate >= RATE) & (st.net > 0)].index); last_good = good
    fx = slot_run(test, lambda r: r.fixed_leaf == "TAKE") if "fixed_leaf" in U else (0, 0, 0)
    wf = slot_run(test, lambda r: r.cell in good)
    for k, v in (("fx", fx), ("wf", wf)): tot[k] += v[0]; cnt[k] += v[1]; hit[k] += v[2]
    pct = lambda v: f"{(100*v[2]/v[1]) if v[1] else 0:3.0f}%"
    print(f"{M:8s} {test.session.nunique():4d} | {fx[0]:+9.0f} ({fx[1]:3d}) {pct(fx):>5s} | {wf[0]:+9.0f} ({wf[1]:3d}) {pct(wf):>5s} | {len(good)} TAKE-cells")
p = lambda k: f"{(100*hit[k]/cnt[k]) if cnt[k] else 0:.0f}%"
print(f"TOTAL          | {tot['fx']:+9.0f} ({cnt['fx']}) {p('fx')} | {tot['wf']:+9.0f} ({cnt['wf']}) {p('wf')}")
# hindsight ceiling (NOT a result): cells over the whole period that meet the bar
st = U.groupby("cell").agg(n=("t1", "size"), rate=("t1", "mean"), net=("net", "sum")).sort_values("n", ascending=False)
ok = st[(st.n >= NMIN) & (st.rate >= RATE)]
print(f"\nhindsight ceiling (whole period, n>={NMIN}, T1>={RATE:.0%}): {len(ok)} cells, {int(ok.n.sum())} candidates, Σnet {ok.net.sum():+.0f}$ — for orientation only")
print(ok.head(25).round(2).to_string())
# what T1 distance (in R) would 80% of the candidates reach? — per cell the 20th percentile of MFE/R, with the expectancy
# at that distance (hit → +q·R, miss → −1R; commissions ignored), on the live-eligible universe.
if "mfe_r" in U:
    cc = U.groupby("cell").agg(n=("mfe_r", "size"), q20=("mfe_r", lambda x: x.quantile(0.2)), q50=("mfe_r", "median"),
                               t1_rate=("t1", "mean"), r_pts=("r_pts", "median"))
    cc = cc[cc.n >= NMIN].copy(); cc["E_at_q20_R"] = RATE * cc.q20 - (1 - RATE) * 1.0
    cc["E_at_q20_$"] = (cc.E_at_q20_R * cc.r_pts * 5.0 - 2.6).round(1)
    print(f"\nT1 distance reachable by {RATE:.0%} of the candidates, per cell (n>={NMIN}), sorted by it:")
    print(cc.sort_values("q20", ascending=False).head(20).round(2).to_string())
    print(f"all live-eligible candidates: n={len(U)} · T1(1.5R) hit {U.t1.mean():.0%} · MFE/R q20={U.mfe_r.quantile(.2):.2f} q50={U.mfe_r.median():.2f} q80={U.mfe_r.quantile(.8):.2f}")
if opt.get("out"):
    json.dump({"key": KEY, "rate": RATE, "nmin": NMIN, "cells": sorted(last_good),
               "hindsight_cells": {k: dict(n=int(v.n), rate=round(float(v.rate), 3), net=round(float(v.net), 2)) for k, v in ok.iterrows()}},
              open(opt["out"], "w"), indent=1, ensure_ascii=False)
    print("policy →", opt["out"])
