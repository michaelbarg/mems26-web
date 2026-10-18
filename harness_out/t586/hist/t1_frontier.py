#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super-agent T1 — the T1 FRONTIER: with the system's own (structural) stop, what share of live-eligible candidates
reach +X points before the stop, for X = 2..8 pts and for the system's T1 (1.5R floor)? And what does leg 1 earn at
each X (hit → +X, miss → the recorded STOP/EOD result)? Per doctrine cell (n >= nmin) and overall. Also the ladder
after the system's T1: share that reaches T2 before coming back to break-even.
usage: t1_frontier.py <cand.csv> [--nmin=25] [--key=opening_type,phase,day_type,kind,zone] [--maxr=20] [--rate=0.8]"""
import sys, pandas as pd, numpy as np
f = next(a for a in sys.argv[1:] if not a.startswith("--"))
opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
NMIN = int(opt.get("nmin", 25)); MAXR = float(opt.get("maxr", 20)); RATE = float(opt.get("rate", 0.8))
KEY = opt.get("key", "opening_type,phase,day_type,kind,zone").split(",")
XS = [2, 3, 4, 6, 8]
df = pd.read_csv(f).fillna({"kind": "?", "opening_type": "?", "phase": "?", "day_type": "?", "rel_bias": "?", "zone": "?"})
df = df[(df.r_pts > 0) & (df.r_pts <= MAXR)]
elig = df.blocked_by.fillna("").astype(str).isin(["", "nan"]) & (df.shadow_only == 0) & ((df.taken == 1) | (df.live_blocked_by.fillna("") == "live_slot_occupied"))
U = df[elig].copy(); U["cell"] = U[KEY].astype(str).agg("|".join, axis=1)
U["mfe_pts"] = U.mfe_r * U.r_pts; U["t1"] = (U.exit == "T1").astype(int)
for X in XS:
    hit = U.mfe_pts >= X
    U[f"h{X}"] = hit.astype(int)
    U[f"e{X}"] = np.where(hit, X * 5.0 - 2.6, U.pts * 5.0 - 2.6)      # leg-1 $ at target X; miss = the recorded stop/EOD outcome
def summarize(g):
    out = {"n": len(g), "R_pts": g.r_pts.median(), "T1sys%": 100 * g.t1.mean(), "E_T1sys$": g.net.mean()}
    for X in XS: out[f"p{X}"] = 100 * g[f"h{X}"].mean(); out[f"E{X}$"] = g[f"e{X}"].mean()
    t = g[g.t1 == 1]; out["T2|T1%"] = 100 * t.t2_hit.mean() if len(t) else np.nan; out["BE|T1%"] = 100 * t.be_after_t1.mean() if len(t) else np.nan
    return pd.Series(out)
print(f"live-eligible candidates: {len(U)} · sessions {U.session.nunique()} · {U.session.min()}..{U.session.max()}")
print("\nALL (one row): hit-rate p(X) = share reaching +X pts before the stop; E(X)$ = mean leg-1 $ with T1 at X")
print(summarize(U).round(1).to_string())
by = U.groupby("cell").apply(summarize); by = by[by.n >= NMIN]
for X in XS:
    ok = by[(by[f"p{X}"] >= 100 * RATE) & (by[f"E{X}$"] > 0)]
    print(f"\ncells with p({X} pts) >= {RATE:.0%} and positive leg-1 expectancy: {len(ok)} of {len(by)} (n>={NMIN})")
    if len(ok): print(ok[["n", "R_pts", f"p{X}", f"E{X}$", "T1sys%", "T2|T1%", "BE|T1%"]].sort_values(f"p{X}", ascending=False).head(12).round(1).to_string())
print(f"\ntop cells by p(4 pts) (n>={NMIN}):")
print(by.sort_values("p4", ascending=False).head(15)[["n", "R_pts", "p2", "p3", "p4", "p6", "p8", "T1sys%", "E4$", "E_T1sys$", "T2|T1%", "BE|T1%"]].round(1).to_string())
print(f"\nby kind:"); print(U.groupby("kind").apply(summarize)[["n", "R_pts", "p2", "p4", "p6", "T1sys%", "E4$", "E_T1sys$", "T2|T1%"]].round(1).to_string())
print(f"\nby kind x phase:"); print(U.groupby(["kind", "phase"]).apply(summarize)[["n", "R_pts", "p2", "p4", "p6", "T1sys%", "E4$", "E_T1sys$", "T2|T1%"]].round(1).to_string())
