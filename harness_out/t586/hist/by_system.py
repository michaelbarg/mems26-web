#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per producing SYSTEM (S2 five-min / S4 Woodies) and per pattern, net results of a harness tag on a session list.
usage: by_system.py <TAG> <sessions.txt> [--top=20]"""
import sys, json, os, collections
COMM = 2.6
tag, lst = sys.argv[1], sys.argv[2]; TOP = int(next((a.split("=")[1] for a in sys.argv[3:] if a.startswith("--top=")), "20"))
sessions = open(lst).read().split()
sysn = collections.defaultdict(lambda: [0, 0.0, 0]); pat = collections.defaultdict(lambda: [0, 0.0, 0, None])
for s in sessions:
    f = f"harness_out/t466/{tag}_{s}.json"
    if not os.path.exists(f): continue
    j = json.load(open(f)); sm = {}
    for r in j.get("routes") or []:
        res = r.get("result") or {}
        for k in ("live", "demo", "shadow"):
            if res.get(k): sm[res[k]] = r.get("system")
    for t in j.get("trades") or []:
        if t.get("pnl_usd") is None: continue
        net = float(t["pnl_usd"]) - COMM; sy = sm.get(t.get("trade_id"), "?"); w = int(float(t["pnl_usd"]) > 0)
        a = sysn[f"S{sy}"]; a[0] += 1; a[1] += net; a[2] += w
        p = pat[t.get("classification")]; p[0] += 1; p[1] += net; p[2] += w; p[3] = f"S{sy}"
n = sum(a[0] for a in sysn.values()); tot = sum(a[1] for a in sysn.values())
print(f"{tag} on {lst.split('/')[-1]}: {n} trades, Σ net {tot:+.0f}$")
for k, a in sorted(sysn.items()): print(f"  {k}: n={a[0]} Σ={a[1]:+.0f}$ ({a[1]/max(1,a[0]):+.1f}$/t) win {100*a[2]/max(1,a[0]):.0f}%")
print("  by pattern (worst → best):")
for k, p in sorted(pat.items(), key=lambda kv: kv[1][1])[:TOP]: print(f"    {k:26s} {p[3]} n={p[0]:3d} Σ={p[1]:+7.0f}$ ({p[1]/p[0]:+6.1f}$/t) win {100*p[2]/p[0]:3.0f}%")
print("  ...best:")
for k, p in sorted(pat.items(), key=lambda kv: -kv[1][1])[:6]: print(f"    {k:26s} {p[3]} n={p[0]:3d} Σ={p[1]:+7.0f}$ ({p[1]/p[0]:+6.1f}$/t) win {100*p[2]/p[0]:3.0f}%")
