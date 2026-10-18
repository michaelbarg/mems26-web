#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Frontier for thesis_rt.py rows: for each variant and target X (pts), p(+X before the stop) and the 1-contract
expectancy when ALL contracts exit at +X (else at the stop / EOD) — the "80% at a paying target" question, real time.
usage: rt_frontier.py <rt.csv> [more.csv ...] [--variant=rt4]"""
import sys, pandas as pd
args = [a for a in sys.argv[1:] if not a.startswith("--")]; opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
PT, COMM = 5.0, 2.6
S = pd.concat([pd.read_csv(a).assign(src=a.split("/")[-1].replace(".csv", "")) for a in args], ignore_index=True)
if opt.get("variant"): S = S[S.variant == opt["variant"]]
XS = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20]
def ex(g, X):
    hit = g.mfe >= X
    pts = hit * X + (~hit) * g.pts_nt          # not reached -> the no-target outcome (stop, or EOD close)
    return pd.Series({"n": len(g), f"p": 100 * hit.mean(), "E$": (pts * PT - COMM).mean(), "Σ$": (pts * PT - COMM).sum()})
for (src, v), g in S.groupby(["src", "variant"]):
    print(f"\n{src} / {v}: n={len(g)}  R median {g.R.median():.1f}  stop-outs {100 * (g.exit_nt == 'STOP').mean():.0f}%  "
          f"mean loss at stop {-(g[g.exit_nt == 'STOP'].pts_nt.mean() if (g.exit_nt == 'STOP').any() else 0) * PT:.0f}$")
    t = pd.DataFrame({X: ex(g, X) for X in XS}).T; t.index.name = "X_pts"
    print(t.round(1).to_string())
