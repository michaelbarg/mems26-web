#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence test for the real-time R2 entries (thesis_rt.py rows with delta/volume): does order-flow evidence at the
open separate the drives that hold from the ones that fail?  Conditions are fixed in advance (Dalton: initiative
activity shows in the delta of the other timeframe), measured per regime, no fitting:
  E0 all · E1 Σdelta over the drive-read bars with the drive · E1s E1 and |Σdelta| >= the regime's median · E2 the
  entry bar's delta with the drive · E3 the pullback bars' Σdelta against the drive (sellers tried and lost) · E1+E2.
usage: rt_evidence.py <rt.csv> [more.csv ...] [--variants=rt3,rt4,rt6,lock]"""
import sys, pandas as pd, numpy as np
args = [a for a in sys.argv[1:] if not a.startswith("--")]; opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
VARS = opt.get("variants", "rt3,rt4,rt6,lock").split(",")
S = pd.concat([pd.read_csv(a).assign(src=a.split("/")[-1].replace(".csv", "")) for a in args], ignore_index=True)
S = S[S.variant.isin(VARS) & S.d_read.notna()].copy()
S["sgn"] = np.where(S.dir == "LONG", 1, -1)
def row(g, name):
    if len(g) == 0: return {"cond": name, "n": 0}
    return {"cond": name, "n": len(g), "T0%": round(100 * g.t0.mean()), "T1%": round(100 * g.t1hit.mean()), "stop%": round(100 * (g.exit_nt == "STOP").mean()),
            "E15$": round(g.net15.mean(), 1), "Σ15$": round(g.net15.sum()), "E3$": round(g.net3.mean(), 1)}
for (src, v), g in S.groupby(["src", "variant"]):
    med = g.d_read.abs().median()
    e1 = g.d_read_dir == 1; e2 = g.d_entry_dir == 1; e3 = (g.d_pull * g.sgn) < 0
    conds = [("E0 all", g), ("E1 open-delta with drive", g[e1]), ("¬E1 against", g[~e1]), ("E1s strong (>= median)", g[e1 & (g.d_read.abs() >= med)]),
             ("E2 entry-bar delta with drive", g[e2]), ("¬E2", g[~e2]), ("E3 pullback delta against (absorbed)", g[e3]), ("¬E3", g[~e3]),
             ("E1 & E2", g[e1 & e2]), ("E1 & E2 & E3", g[e1 & e2 & e3])]
    print(f"\n{src} / {v}  (n={len(g)}, median |Σdelta read| {med:.0f})")
    print(pd.DataFrame([row(x, n) for n, x in conds]).to_string(index=False))
