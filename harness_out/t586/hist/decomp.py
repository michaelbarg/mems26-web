#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-590/T-591 decomposition on common sessions: A (live data, live prev-day VA rows) → B (live data, reconstructed
prev-day VA rows = pvfix) → C (reconstructed bars/studies/TPO + reconstructed VA = ctrl_sep).
B−A = the prev-day value-area fix alone; C−B = the tick reconstruction alone.   usage: decomp.py <sessions.txt> A B C"""
import sys, json, os
sess = open(sys.argv[1]).read().split(); tags = sys.argv[2:5]
def trades(tag, s):
    p = f"harness_out/t466/{tag}_{s}.json"
    if not os.path.exists(p): return None
    j = json.load(open(p)); return [(t["classification"], str(t.get("fired_il") or "")[:5], round(float(t.get("pnl_usd") or 0), 2)) for t in j["trades"]]
tot = {t: 0.0 for t in tags}; n = {t: 0 for t in tags}; same = {}; common = 0
for s in sess:
    tr = {t: trades(t, s) for t in tags}
    if any(v is None for v in tr.values()): continue
    common += 1
    for t in tags: tot[t] += sum(x[2] for x in tr[t]); n[t] += len(tr[t])
    for a, b in ((tags[0], tags[1]), (tags[1], tags[2]), (tags[0], tags[2])):
        k = (a, b); same.setdefault(k, 0)
        if {(x[0], x[1]) for x in tr[a]} == {(x[0], x[1]) for x in tr[b]}: same[k] += 1
print(f"{common} common sessions")
for t in tags: print(f"  {t:10s} Σ gross {tot[t]:+9.2f}$  trades {n[t]}")
a, b, c = tags
print(f"  VA fix alone      (B−A): {tot[b]-tot[a]:+8.2f}$   identical trade-sets {same[(a,b)]}/{common}")
print(f"  reconstruction    (C−B): {tot[c]-tot[b]:+8.2f}$   identical trade-sets {same[(b,c)]}/{common}")
print(f"  both              (C−A): {tot[c]-tot[a]:+8.2f}$   identical trade-sets {same[(a,c)]}/{common}")
