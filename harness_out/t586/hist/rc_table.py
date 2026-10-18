#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RC-1 table: one row per (harness TAG, session list) — the whole-day replay numbers the ruling needs, side by side.
Σ net (2.60$/trade), trades, win%, +/- days, months >= 0, max drawdown, worst 10-session window, share of negative
20-session windows, and the per-kind net.  usage: rc_table.py --lists=oos:/path/166.txt,is:/path/70.txt TAG [TAG ...]"""
import json, os, sys, collections
COMM = 2.60
tags = [a for a in sys.argv[1:] if not a.startswith("--")]
lists = {}
for spec in next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--lists=")), "").split(","):
    if spec: name, path = spec.split(":", 1); lists[name] = open(path).read().split()
def load(tag, sessions):
    out = {}
    for s in sessions:
        f = f"harness_out/t466/{tag}_{s}.json"
        if not os.path.exists(f): continue
        j = json.load(open(f)); tr = j.get("trades") or []
        kind_of = {}
        for r in j.get("routes") or []:
            res = r.get("result") or {}
            for k in ("live", "demo", "shadow"):
                if res.get(k): kind_of[res[k]] = ((r.get("tree_v3") or {}).get("vec") or {}).get("kind") or "?"
        for t in tr: t["kind"] = kind_of.get(t.get("trade_id"), "?")
        out[s] = (float(j.get("daily_pnl_harness") or 0) - COMM * len(tr), tr)
    return out
def stats(A):
    ses = sorted(A); nets = [A[s][0] for s in ses]; tr = [t for s in ses for t in A[s][1]]
    if not ses: return None
    eq = 0.0; peak = 0.0; dd = 0.0
    for n in nets: eq += n; peak = max(peak, eq); dd = max(dd, peak - eq)
    w10 = min((sum(nets[i:i + 10]) for i in range(0, max(1, len(nets) - 9))), default=0.0)
    w20 = [sum(nets[i:i + 20]) for i in range(0, max(1, len(nets) - 19))]
    months = collections.defaultdict(float)
    for s, n in zip(ses, nets): months[s[:7]] += n
    kinds = collections.defaultdict(float)
    for t in tr: kinds[(t.get("kind") or t.get("entry_kind") or "?")] += float(t.get("pnl_usd") or 0) - COMM
    return dict(n=len(ses), first=ses[0], last=ses[-1], net=sum(nets), trades=len(tr), win=100 * sum(1 for t in tr if float(t.get("pnl_usd") or 0) > 0) / max(1, len(tr)),
                pos=sum(1 for n in nets if n > 0), neg=sum(1 for n in nets if n < 0), m_ok=sum(1 for v in months.values() if v >= 0), m=len(months),
                dd=dd, w10=w10, w20neg=100 * sum(1 for v in w20 if v < 0) / len(w20), kinds=dict(kinds), per_day=sum(nets) / len(nets))
hdr = f"{'tag':10s} {'list':5s} {'n':>4s} {'Σnet$':>9s} {'$/day':>6s} {'trades':>6s} {'win%':>5s} {'+/-':>8s} {'mon≥0':>6s} {'maxDD':>7s} {'w10':>8s} {'w20<0%':>6s}  per kind (net$)"
print(hdr)
for tag in tags:
    for name, sessions in lists.items():
        st = stats(load(tag, sessions))
        if not st: print(f"{tag:10s} {name:5s}    - (no files)"); continue
        kinds = " · ".join(f"{k} {v:+.0f}" for k, v in sorted(st["kinds"].items(), key=lambda kv: -abs(kv[1])))
        miss = len(sessions) - st["n"]
        print(f"{tag:10s} {name:5s} {st['n']:4d}{'*' if miss else ' '}{st['net']:+9.2f} {st['per_day']:+6.1f} {st['trades']:6d} {st['win']:5.0f} "
              f"{st['pos']:3d}/{st['neg']:<3d} {st['m_ok']:2d}/{st['m']:<2d} {st['dd']:7.0f} {st['w10']:+8.0f} {st['w20neg']:6.0f}  {kinds}")
        if miss: print(f"{'':10s} {'':5s}      * {miss} of {len(sessions)} sessions have no file yet")
