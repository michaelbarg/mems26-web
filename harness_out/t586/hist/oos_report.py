#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-586/T-591 — structure of a harness tag's TAKEN trades: by pattern, kind×phase, opening type, day type, month.
Net = pnl_usd − 2.60$ × contracts (the harness books 2 contracts for the T-561 ZLR cell; everything else 1).
usage: oos_report.py <TAG> [--from=YYYY-MM-DD] [--to=YYYY-MM-DD] [--cand=<cand.csv>]   (cand.csv adds the tree vector)"""
import sys, json, glob, pandas as pd
tag = next(a for a in sys.argv[1:] if not a.startswith("--"))
opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
rows = []
for f in sorted(glob.glob(f"harness_out/t466/{tag}_20*.json")):
    j = json.load(open(f)); s = j["session"]
    if opt.get("from") and s < opt["from"]: continue
    if opt.get("to") and s > opt["to"]: continue
    for t in j.get("trades") or []:
        c = float(t.get("contracts") or 1)
        rows.append(dict(session=s, il=str(t.get("fired_il") or "")[:5], pattern=t["classification"], direction=t["direction"],
                         contracts=c, gross=float(t.get("pnl_usd") or 0), net=float(t.get("pnl_usd") or 0) - 2.6 * c,
                         rth=(j.get("bars") or {}).get("rth")))
df = pd.DataFrame(rows)
if opt.get("cand"):
    cd = pd.read_csv(opt["cand"]); cd = cd[cd.taken == 1][["session", "il", "pattern", "kind", "opening_type", "phase", "day_type", "rel_bias", "zone"]]
    df = df.merge(cd, on=["session", "il", "pattern"], how="left")
df["month"] = df.session.str[:7]
ns = len(set(df.session)); print(f"{tag}: {ns} sessions with trades · {len(df)} trades · Σ gross {df.gross.sum():+.2f}$ · Σ net {df.net.sum():+.2f}$ "
                                f"· win {(df.gross > 0).mean()*100:.0f}% · sessions with rth≠78: {sorted(set(df[df.rth != 78].session))}")
def tab(keys, title):
    g = df.groupby(keys).agg(n=("net", "size"), net=("net", "sum"), win=("gross", lambda x: (x > 0).mean()), contracts=("contracts", "mean"))
    print(f"\n── {title}"); print(g.sort_values("net").round(2).to_string())
tab("pattern", "by pattern")
tab("month", "by month")
if opt.get("cand"):
    for k, t in (("kind", "by kind"), (["kind", "phase"], "by kind × phase"), ("opening_type", "by opening type"), ("day_type", "by day type"),
                 (["opening_type", "kind"], "by opening type × kind"), ("rel_bias", "by rel_bias"), ("zone", "by zone")):
        tab(k, t)
