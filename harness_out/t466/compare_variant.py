#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Day-total comparison of a night variant (harness_out/t466/<TAG>_*.json) vs the live baseline
(drive branch ON @1.5R: harness_out/t458/r15_<d>.json on drive sessions, else branch1_<d>.json).
usage: compare_variant.py <TAG> [pattern-substring to detail]"""
import glob, json, os, sys, collections
TAG = sys.argv[1]; PAT = sys.argv[2] if len(sys.argv) > 2 else None
D = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(os.path.dirname(D), "t458")
rows = []
for p in sorted(glob.glob(os.path.join(D, f"{TAG}_*.json"))):
    d = os.path.basename(p)[len(TAG) + 1:len(TAG) + 11]
    try: j1 = json.load(open(p))
    except Exception as e: print("bad", d, e); continue
    b = os.path.join(B, f"r15_{d}.json")
    if not os.path.exists(b): b = os.path.join(B, f"branch1_{d}.json")
    if not os.path.exists(b): print("no baseline", d); continue
    j0 = json.load(open(b))
    t0 = j0.get("trades") or []; t1 = j1.get("trades") or []
    new = [t for t in t1 if PAT and PAT in str(t.get("classification"))]
    changed = [(t["classification"], t["direction"], t["entry"], t["outcome"], round(t["pnl_usd"], 1)) for t in t1] != [(t["classification"], t["direction"], t["entry"], t["outcome"], round(t["pnl_usd"], 1)) for t in t0]
    rows.append(dict(d=d, day0=j0["daily_pnl_harness"], day1=j1["daily_pnl_harness"], n0=len(t0), n1=len(t1), changed=changed,
                     detail=[(t["direction"], t["entry"], t.get("t1_target"), t["outcome"], round(t["pnl_usd"], 1), t.get("exit_il")) for t in new]))
print(f"{'day':10} {'base$':>8} {'variant$':>9} {'Δ$':>8} n0 n1 chg  detail")
for r in rows:
    if r["changed"] or r["detail"]:
        print(f"{r['d']:10} {r['day0']:8.2f} {r['day1']:9.2f} {r['day1']-r['day0']:8.2f} {r['n0']:2d} {r['n1']:2d} {'*' if r['changed'] else ' '}   {r['detail'] if r['detail'] else ''}")
s0 = sum(r["day0"] for r in rows); s1 = sum(r["day1"] for r in rows); dn = sum(r["n1"] - r["n0"] for r in rows)
print(f"\n{len(rows)} sessions: baseline Σ{s0:+.2f}$ · {TAG} Σ{s1:+.2f}$ · Δ {s1-s0:+.2f}$ gross, ≈{s1-s0-2.6*dn:+.2f}$ net of {dn:+d} round-trips · better {sum(1 for r in rows if r['day1']>r['day0']+0.01)} / worse {sum(1 for r in rows if r['day1']<r['day0']-0.01)} / same {sum(1 for r in rows if abs(r['day1']-r['day0'])<=0.01)}")
m = collections.defaultdict(lambda: [0, 0.0, 0.0])
for r in rows: k = r["d"][:7]; m[k][0] += 1; m[k][1] += r["day0"]; m[k][2] += r["day1"]
print("by month: " + " · ".join(f"{k}: {v[0]}d base {v[1]:+.0f} var {v[2]:+.0f} Δ{v[2]-v[1]:+.0f}" for k, v in sorted(m.items())))
