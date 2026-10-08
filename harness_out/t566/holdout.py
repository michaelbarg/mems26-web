# -*- coding: utf-8 -*-
"""T-566 — per-session Δ of t566 (STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1) vs the reference, holdout-10 = the last 10
sessions, months, and the list of tightened trades (what the rule actually did). Read-only on harness_out/t466."""
import json, glob, os, sys, collections
TAG = sys.argv[1] if len(sys.argv) > 1 else "t566"
REF = sys.argv[2] if len(sys.argv) > 2 else "t564ref"
def load(tag, s):
    p = "harness_out/t466/%s_%s.json" % (tag, s)
    return json.load(open(p)) if os.path.exists(p) else None
sessions = sorted(f.split("%s_" % TAG)[1][:10] for f in glob.glob("harness_out/t466/%s_2026-*.json" % TAG))
hold = sessions[-10:]
dsum = hsum = 0.0; months = collections.Counter(); better = worse = same = 0
tight = []; stats = collections.Counter()
for s in sessions:
    a, r = load(TAG, s), load(REF, s)
    if not a or not r:
        print("missing", s); continue
    pa = sum(float(t.get("pnl_usd") or 0) for t in a.get("trades") or [])
    pr = sum(float(t.get("pnl_usd") or 0) for t in r.get("trades") or [])
    d = pa - pr; dsum += d; months[s[:7]] += d
    if s in hold: hsum += d
    if d > 1e-9: better += 1
    elif d < -1e-9: worse += 1
    else: same += 1
    st = a.get("se_tighten") or {}
    for k in ("checked", "signals", "tightened"): stats[k] += int(st.get(k) or 0)
    for t in a.get("trades") or []:
        for tg in t.get("tightened") or []:
            tight.append((s, t["fired_il"], t["classification"], t["direction"], tg["il"], tg["from"], tg["to"], t.get("pnl_usd"), [l.get("exit") for l in t.get("legs", [])]))
    if abs(d) > 1e-9:
        print("%s Δ %+8.2f   (ref %+8.2f → %+8.2f)" % (s, d, pr, pa))
print("sessions %d · Σ Δ %+.2f gross · holdout-10 (%s..%s) Δ %+.2f · better %d / worse %d / same %d" % (len(sessions), dsum, hold[0], hold[-1], hsum, better, worse, same))
print("months:", " · ".join("%s %+.0f" % (m, v) for m, v in sorted(months.items())))
print("mechanism:", dict(stats), "· tightened trades:", len(tight))
for row in tight:
    print("  TIGHTENED", row)
