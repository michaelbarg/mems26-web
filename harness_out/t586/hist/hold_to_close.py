#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Management alternative on the harness trades: 'hold to the close with the initial stop' instead of the T1/T2 ladder.
From each trade's mae_pts (max adverse) and hold_to_close_pts: if the adverse excursion reached the initial stop the trade
is a stop-out, else it ends at the session close. Per regime (session lists) and per kind. usage:
  hold_to_close.py <TAG> --lists=name:/path.txt,...   (COMM 2.60/trade)"""
import sys, json, os, collections
COMM = 2.6
tag = next(a for a in sys.argv[1:] if not a.startswith("--"))
lists = {}
for spec in next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--lists=")), "").split(","):
    if spec: n, p = spec.split(":", 1); lists[n] = open(p).read().split()
def kinds_of(j):
    m = {}
    for r in j.get("routes") or []:
        res = r.get("result") or {}
        for k in ("live", "demo", "shadow"):
            if res.get(k): m[res[k]] = ((r.get("tree_v3") or {}).get("vec") or {}).get("kind") or "?"
    return m
for name, sessions in lists.items():
    agg = collections.defaultdict(lambda: [0, 0.0, 0.0, 0, 0])   # kind -> n, actual$, hold$, stopped, trend-day-holds
    for s in sessions:
        f = f"harness_out/t466/{tag}_{s}.json"
        if not os.path.exists(f): continue
        j = json.load(open(f)); km = kinds_of(j)
        for t in j.get("trades") or []:
            if t.get("pnl_usd") is None or t.get("hold_to_close_pts") is None or t.get("mae_pts") is None: continue
            r = abs(float(t["entry"]) - float(t["stop_initial"])); mae = -float(t["mae_pts"]) if float(t["mae_pts"]) < 0 else 0.0
            n_c = int(t.get("contracts") or 1)
            hold = (-r if mae >= r else float(t["hold_to_close_pts"])) * 5.0 * n_c - COMM
            a = agg[km.get(t.get("trade_id"), "?")]; a[0] += 1; a[1] += float(t["pnl_usd"]) - COMM; a[2] += hold; a[3] += int(mae >= r)
            z = agg["ALL"]; z[0] += 1; z[1] += float(t["pnl_usd"]) - COMM; z[2] += hold; z[3] += int(mae >= r)
    print(f"\n{tag} / {name}: {len(sessions)} sessions")
    print(f"{'kind':12s} {'n':>5s} {'actual Σ$':>10s} {'$/t':>6s} {'hold-to-close Σ$':>16s} {'$/t':>6s} {'stopped%':>8s}")
    for k, a in sorted(agg.items(), key=lambda kv: -kv[1][0]):
        if a[0]: print(f"{k:12s} {a[0]:5d} {a[1]:+10.0f} {a[1]/a[0]:+6.1f} {a[2]:+16.0f} {a[2]/a[0]:+6.1f} {100*a[3]/a[0]:8.0f}")
