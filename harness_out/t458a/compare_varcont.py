#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-458א — VAR_CONT_V1 replay vs the live baseline (drive branch ON @1.5R = today's .env).
Baseline per session: harness_out/t458/r15_<d>.json on the 29 drive sessions (branch on, 1.5R),
else harness_out/t458/branch1_<d>.json (no drive ⇒ identical to HEAD). Day totals = daily_pnl_harness
(no commissions; the trade counts are printed so the commission delta can be judged)."""
import glob, json, os, collections, sys
TAG = sys.argv[1] if len(sys.argv) > 1 else "varcont"
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
    vcs = [t for t in (j1.get("trades") or []) if t.get("classification") == "VAR_CONT"]
    vdec = [g for g in (j1.get("gateway_decisions") or []) if (g.get("pattern") or "") == "VAR_CONT"]
    blocked = collections.Counter((g.get("blocked_by") or g.get("live_blocked_by") or g.get("outcome")) for g in vdec)
    rows.append(dict(d=d, dt=(j1.get("s1") or {}).get("day_type") if isinstance(j1.get("s1"), dict) else None,
                     day0=j0["daily_pnl_harness"], day1=j1["daily_pnl_harness"], n0=len(j0.get("trades") or []), n1=len(j1.get("trades") or []),
                     vc=[(t["direction"], t["entry"], t.get("t1_target"), t["outcome"], round(t["pnl_usd"], 1), t.get("exit_il")) for t in vcs],
                     cands=len(vdec), blocked=dict(blocked)))
print(f"{'day':10} {'base$':>8} {'varcont$':>9} {'Δ$':>8} n0 n1 cand  VAR_CONT trades (dir entry t1 outcome pnl exit) / gate outcomes")
for r in rows:
    print(f"{r['d']:10} {r['day0']:8.2f} {r['day1']:9.2f} {r['day1']-r['day0']:8.2f} {r['n0']:2d} {r['n1']:2d} {r['cands']:4d}  {r['vc'] if r['vc'] else '-'}  {r['blocked']}")
s0 = sum(r["day0"] for r in rows); s1 = sum(r["day1"] for r in rows)
vc_all = [t for r in rows for t in r["vc"]]
print(f"\n{len(rows)} sessions: baseline Σ{s0:+.2f}$ · +VAR_CONT Σ{s1:+.2f}$ · Δ {s1-s0:+.2f}$ · sessions better {sum(1 for r in rows if r['day1']>r['day0']+0.01)} / worse {sum(1 for r in rows if r['day1']<r['day0']-0.01)} / same {sum(1 for r in rows if abs(r['day1']-r['day0'])<=0.01)}")
print(f"VAR_CONT live trades: n={len(vc_all)} win={100*sum(1 for t in vc_all if t[4]>0)/max(1,len(vc_all)):.0f}% Σ{sum(t[4] for t in vc_all):+.2f}$ (before commissions) · candidates={sum(r['cands'] for r in rows)} · trades {sum(r['n0'] for r in rows)}→{sum(r['n1'] for r in rows)}")
m = collections.defaultdict(lambda: [0, 0.0, 0.0])
for r in rows: k = r["d"][:7]; m[k][0] += 1; m[k][1] += r["day0"]; m[k][2] += r["day1"]
print("by month: " + " · ".join(f"{k}: {v[0]}d base {v[1]:+.0f} varcont {v[2]:+.0f} Δ{v[2]-v[1]:+.0f}" for k, v in sorted(m.items())))
bl = collections.Counter()
for r in rows: bl.update(r["blocked"])
print("gate outcomes over all VAR_CONT candidates:", dict(bl.most_common()))
