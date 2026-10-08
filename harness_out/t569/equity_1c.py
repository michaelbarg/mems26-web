# -*- coding: utf-8 -*-
"""T-569 (08.10): one-contract equity curve of the live-config replay (t564ref, tree 3.4.0, 67 sessions).
Read-only. Numbers for the account-growth ladder: per-session net, max DD, worst day, streaks, months.
Usage: python3 harness_out/t569/equity_1c.py [TAG]   (default t564ref)"""
import json, glob, sys, os, statistics as st
TAG = sys.argv[1] if len(sys.argv) > 1 else "t564ref"
COMM = 2.60  # round-trip, as in cmp_vs_live.py
rows = []
for f in sorted(glob.glob(f"harness_out/t466/{TAG}_*.json")):
    d = json.load(open(f))
    tr = d.get("trades") or []
    gross = float(d.get("daily_pnl_harness") or 0)
    n = len([t for t in tr if t.get("filled")])
    rows.append((d["session"], gross, gross - COMM * n, n))
print(f"{TAG}: {len(rows)} sessions · Σ gross {sum(r[1] for r in rows):+.2f}$ · Σ net {sum(r[2] for r in rows):+.2f}$ · trades {sum(r[3] for r in rows)}")
nets = [r[2] for r in rows]
pos = [x for x in nets if x > 0]; neg = [x for x in nets if x < 0]; zero = [x for x in nets if x == 0]
print(f"days: +{len(pos)} / -{len(neg)} / 0:{len(zero)} · mean/day {st.mean(nets):+.2f}$ · median {st.median(nets):+.2f}$ · best {max(nets):+.2f}$ · worst {min(nets):+.2f}$")
print(f"mean win-day {st.mean(pos):+.2f}$ · mean loss-day {st.mean(neg):+.2f}$ · stdev/day {st.pstdev(nets):.2f}$")
# equity + max drawdown (sequential, closed-day)
eq = 0.0; peak = 0.0; dd = 0.0; dd_start = dd_end = None; cur_start = rows[0][0]
for s, g, n_, k in rows:
    eq += n_
    if eq > peak: peak = eq; cur_start = s
    if peak - eq > dd: dd = peak - eq; dd_start, dd_end = cur_start, s
print(f"final equity {eq:+.2f}$ · max closed-day DD {dd:.2f}$ ({dd_start} → {dd_end})")
# streaks
ls = ws = cl = cw = 0
for x in nets:
    if x < 0: cl += 1; cw = 0
    elif x > 0: cw += 1; cl = 0
    ls = max(ls, cl); ws = max(ws, cw)
print(f"longest losing streak {ls} days · longest winning streak {ws} days")
for w in (5, 10):
    worst = min(sum(nets[i:i+w]) for i in range(len(nets)-w+1))
    print(f"worst {w}-day window {worst:+.2f}$")
m = {}
for s, g, n_, k in rows:
    m.setdefault(s[:7], [0.0, 0, 0]); m[s[:7]][0] += n_; m[s[:7]][1] += 1; m[s[:7]][2] += k
for k_, v in sorted(m.items()):
    print(f"  {k_}: {v[0]:+.2f}$ net over {v[1]} sessions · {v[2]} trades · {v[0]/v[1]:+.2f}$/day")
h = rows[-10:]
print(f"holdout-10 ({h[0][0]}..{h[-1][0]}): Σ net {sum(r[2] for r in h):+.2f}$ · +{sum(1 for r in h if r[2]>0)} / -{sum(1 for r in h if r[2]<0)}")
# per-trade stats
import itertools
alltr = [t for f in sorted(glob.glob(f"harness_out/t466/{TAG}_*.json")) for t in (json.load(open(f)).get("trades") or []) if t.get("filled")]
p = [float(t.get("pnl_usd") or 0) for t in alltr]
w = [x for x in p if x > 0]; l = [x for x in p if x <= 0]
print(f"trades {len(p)} · win-rate {len(w)/len(p):.0%} · avg win {st.mean(w):+.2f}$ · avg loss {st.mean(l):+.2f}$ · avg/trade gross {st.mean(p):+.2f}$ · net {st.mean(p)-COMM:+.2f}$ · worst trade {min(p):+.2f}$")
