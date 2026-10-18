#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-586 — walk-forward ADOPTION test of a variant vs the reference: at each block boundary, adopt the variant for the
next block only if its cumulative Δ so far is > 0 (the decision a trader could have made then). Prints the realized
walk-forward Δ vs the hindsight Δ. usage: wf_adopt.py <TAG> [REF=t567ref] [--block=10]"""
import json, glob, os, sys
TAG = sys.argv[1]; REF = next((a for a in sys.argv[2:] if not a.startswith("--")), "t567ref")
BLOCK = int(next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--block=")), "10"))
COMM = 2.60
def net(tag, s):
    p = f"harness_out/t466/{tag}_{s}.json"
    if not os.path.exists(p): return None
    j = json.load(open(p)); return float(j.get("daily_pnl_harness") or 0) - COMM * len(j.get("trades") or [])
sessions = sorted(os.path.basename(p)[len(TAG) + 1:len(TAG) + 11] for p in glob.glob(f"harness_out/t466/{TAG}_2026-*.json"))
rows = [(s, net(TAG, s), net(REF, s)) for s in sessions]
rows = [(s, a, b) for s, a, b in rows if a is not None and b is not None]
delta = [a - b for _, a, b in rows]
print(f"{TAG} vs {REF}: {len(rows)} sessions · hindsight Δ net {sum(delta):+.2f}$")
for label, bounds in (("month", sorted({s[:7] for s, _, _ in rows})), ("block", None)):
    if bounds is None:
        blocks = [(i, min(i + BLOCK, len(rows))) for i in range(0, len(rows), BLOCK)]
    else:
        idx = {m: [k for k, (s, _, _) in enumerate(rows) if s[:7] == m] for m in bounds}
        blocks = [(idx[m][0], idx[m][-1] + 1) for m in bounds]
    real = 0.0; parts = []
    for n, (i, j) in enumerate(blocks):
        prior = sum(delta[:i]); nxt = sum(delta[i:j])
        adopt = n > 0 and prior > 0
        real += nxt if adopt else 0.0
        parts.append(f"{rows[i][0][5:]}..{rows[j-1][0][5:]} prior {prior:+.0f} → {'ADOPT' if adopt else 'skip '} realized {nxt:+.0f}")
    print(f"  by {label}{'' if bounds else f' ({BLOCK})'}: walk-forward Δ {real:+.2f}$ (first block never adopted)")
    for p in parts: print("    " + p)
