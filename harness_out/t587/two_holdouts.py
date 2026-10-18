# -*- coding: utf-8 -*-
"""T-589 step 2 (fix-agent 18.10) — BRIEF §2.6: a veto 'holds' when it passes TWO consecutive holdouts (the last 10
sessions and the 10 before them). Here the veto is ZLR_SHADOW_V1 (ZLR → shadow): un-shadowing it (t587s) vs the
reference — Δ per window; the veto holds if Δ(un-shadow) ≤ 0 in both. Read-only on harness_out/t466."""
import json, glob, os, sys
TAG = sys.argv[1] if len(sys.argv) > 1 else "t587s"; REF = sys.argv[2] if len(sys.argv) > 2 else "t567ref"
def load(tag, s):
    p = "harness_out/t466/%s_%s.json" % (tag, s)
    return json.load(open(p)) if os.path.exists(p) else None
def pnl(j): return sum(float(t.get("pnl_usd") or 0) for t in (j or {}).get("trades") or [])
sessions = sorted(f.split("%s_" % TAG)[1][:10] for f in glob.glob("harness_out/t466/%s_2026-*.json" % TAG))
d = {}
for s in sessions:
    a, r = load(TAG, s), load(REF, s)
    if a is None or r is None: continue
    d[s] = pnl(a) - pnl(r)
ss = sorted(d)
last10, prev10 = ss[-10:], ss[-20:-10]
def win(w): 
    v = [d[s] for s in w]; return sum(v), sum(1 for x in v if x > 1e-9), sum(1 for x in v if x < -1e-9)
print("%s vs %s · %d common sessions · Σ Δ %+.2f" % (TAG, REF, len(ss), sum(d.values())))
print("holdout A (last 10, %s..%s): Δ %+.2f · better %d / worse %d" % ((last10[0], last10[-1]) + win(last10)))
print("holdout B (10 before, %s..%s): Δ %+.2f · better %d / worse %d" % ((prev10[0], prev10[-1]) + win(prev10)))
print("train (the rest, %d sessions): Δ %+.2f" % (len(ss) - 20, sum(d[s] for s in ss[:-20])))
sa, sb = win(last10)[0], win(prev10)[0]
print("VETO (ZLR shadow) HOLDS in both holdouts:" if sa <= 0 and sb <= 0 else "VETO does NOT hold in both holdouts:", "A %+.2f · B %+.2f" % (sa, sb))
print("worst / best sessions:", sorted(d.items(), key=lambda x: x[1])[:3], sorted(d.items(), key=lambda x: -x[1])[:3])
