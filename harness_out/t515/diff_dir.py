#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-515 (29.09): what a variant added / removed vs the same-day reference, split by direction (the double top vs the
double bottom are not the same signal). usage: diff_dir.py TAG [REF=t515ref]"""
import collections, glob, json, os, sys
D = "harness_out/t466"; TAG = sys.argv[1]; REF = sys.argv[2] if len(sys.argv) > 2 else "t515ref"


def load(tag):
    out = {}
    for p in glob.glob(f"{D}/{tag}_2026-*.json"):
        try:
            out[os.path.basename(p)[len(tag) + 1:len(tag) + 11]] = json.load(open(p))["trades"]
        except Exception:
            pass
    return out


v, r = load(TAG), load(REF)
key = lambda t: (t.get("classification"), t.get("direction"), round(float(t.get("entry") or 0), 2), str(t.get("fired_il", ""))[:5])
agg = collections.defaultdict(lambda: [0, 0, 0.0])
for d in sorted(set(v) & set(r)):
    kv = collections.Counter(key(t) for t in v[d]); kr = collections.Counter(key(t) for t in r[d])
    for t in v[d]:
        if kv[key(t)] > kr.get(key(t), 0):
            kv[key(t)] -= 1; a = agg[("added", t.get("direction"))]; u = float(t.get("pnl_usd") or 0); a[0] += 1; a[1] += u > 0; a[2] += u
    kv = collections.Counter(key(t) for t in v[d])
    for t in r[d]:
        if kr[key(t)] > kv.get(key(t), 0):
            kr[key(t)] -= 1; a = agg[("removed", t.get("direction"))]; u = float(t.get("pnl_usd") or 0); a[0] += 1; a[1] += u > 0; a[2] += u
    # same trade, different outcome (exit changed)
    same = collections.Counter(key(t) for t in v[d]) & collections.Counter(key(t) for t in r[d])
    pv = {}; pr = {}
    for t in v[d]:
        pv.setdefault(key(t), []).append(float(t.get("pnl_usd") or 0))
    for t in r[d]:
        pr.setdefault(key(t), []).append(float(t.get("pnl_usd") or 0))
    for k, n in same.items():
        for i in range(n):
            dlt = pv[k][i] - pr[k][i]
            if abs(dlt) > .01:
                a = agg[("exit-changed", k[1])]; a[0] += 1; a[1] += dlt > 0; a[2] += dlt
for k, (n, w, s) in sorted(agg.items()):
    lab = "better" if k[0] == "exit-changed" else "wins"
    print(f"{TAG} vs {REF} · {k[0]:12s} {k[1]:5s} n={n:3d} {lab} {w:3d} Σ{s:+9.2f}$")
