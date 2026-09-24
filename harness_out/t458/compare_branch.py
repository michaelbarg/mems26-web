#!/usr/bin/env python3
"""T-458(ג) — day-total comparison flag=1 (branch) vs flag=0 (HEAD) on the sessions where the branch put a
confirmed opening drive live. daily_pnl_harness excludes commissions; Δ is commission-neutral only when the
trade count is equal, so the trade counts are printed too."""
import json, glob, os, collections
D = os.path.dirname(os.path.abspath(__file__))
rows = []
for p in sorted(glob.glob(os.path.join(D, "branch0_*.json"))):
    d = os.path.basename(p)[8:18]
    j0 = json.load(open(p)); j1 = json.load(open(os.path.join(D, f"branch1_{d}.json")))
    def dr(j):
        t = [x for x in (j.get("trades") or []) if str(x.get("classification", "")).startswith("OPENING_")]
        return t[0] if t else None
    t0, t1 = dr(j0), dr(j1)
    rows.append(dict(d=d, day0=j0["daily_pnl_harness"], day1=j1["daily_pnl_harness"], n0=len(j0.get("trades") or []), n1=len(j1.get("trades") or []),
                     head=("%s %s tgt %.2f %s %+.1f" % (t0["classification"][8:], t0["direction"], t0.get("t1_target") or 0, t0["outcome"], t0["pnl_usd"])) if t0 else "blocked/absent",
                     br=("%s tgt %.2f %s %+.1f" % (t1["direction"], t1.get("t1_target") or 0, t1["outcome"], t1["pnl_usd"])) if t1 else "-"))
print(f"{'day':10} {'HEAD day$':>9} {'BRANCH day$':>11} {'Δ$':>8} n0 n1  HEAD opening trade                      BRANCH drive")
for r in rows:
    print(f"{r['d']:10} {r['day0']:9.2f} {r['day1']:11.2f} {r['day1']-r['day0']:8.2f} {r['n0']:2d} {r['n1']:2d}  {r['head']:38} {r['br']}")
s0 = sum(r["day0"] for r in rows); s1 = sum(r["day1"] for r in rows)
print(f"\n{len(rows)} drive sessions: HEAD Σ{s0:+.2f}$ · BRANCH Σ{s1:+.2f}$ · Δ {s1-s0:+.2f}$ · sessions better {sum(1 for r in rows if r['day1']>r['day0']+0.01)} / worse {sum(1 for r in rows if r['day1']<r['day0']-0.01)} / same {sum(1 for r in rows if abs(r['day1']-r['day0'])<=0.01)}")
print(f"HEAD opening trades present: {sum(1 for r in rows if r['head']!='blocked/absent')} · trades: HEAD {sum(r['n0'] for r in rows)} vs BRANCH {sum(r['n1'] for r in rows)}")
m = collections.defaultdict(lambda: [0.0, 0.0, 0])
for r in rows: k = r["d"][:7]; m[k][0] += r["day0"]; m[k][1] += r["day1"]; m[k][2] += 1
print("by month: " + " · ".join(f"{k}: {v[2]}d HEAD {v[0]:+.0f} BRANCH {v[1]:+.0f} Δ{v[1]-v[0]:+.0f}" for k, v in sorted(m.items())))
