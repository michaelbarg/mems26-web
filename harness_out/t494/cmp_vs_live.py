#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-494 (27.09): day-total of a variant vs the LIVE configuration replay (live0927), on the common sessions.
usage: cmp_vs_live.py <TAG> [REF=live0927] [--days]   (harness_out/t466/<TAG>_<d>.json)"""
import collections, glob, json, os, sys
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "t466")
TAG = sys.argv[1]; REF = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "live0927"
COMM = 2.60


def load(tag):
    out = {}
    for p in glob.glob(os.path.join(D, f"{tag}_*.json")):
        d = os.path.basename(p)[len(tag) + 1:len(tag) + 11]
        try:
            j = json.load(open(p))
        except Exception:
            continue
        out[d] = (float(j.get("daily_pnl_harness") or 0), j.get("trades") or [])
    return out


v, r = load(TAG), load(REF)
common = sorted(set(v) & set(r))
rows = []
for d in common:
    (p1, t1), (p0, t0) = v[d], r[d]
    rows.append((d, p0, p1, len(t0), len(t1)))
s0 = sum(x[1] for x in rows); s1 = sum(x[2] for x in rows); dn = sum(x[4] - x[3] for x in rows)
better = sum(1 for x in rows if x[2] > x[1] + 0.01); worse = sum(1 for x in rows if x[2] < x[1] - 0.01)
print(f"{TAG} vs {REF}: {len(common)} sessions · {REF} Σ{s0:+.2f}$ · {TAG} Σ{s1:+.2f}$ · Δ {s1 - s0:+.2f}$ gross, "
      f"≈{s1 - s0 - COMM * dn:+.2f}$ net of {dn:+d} round-trips · better {better} / worse {worse} / same {len(rows) - better - worse}")
m = collections.defaultdict(lambda: [0, 0.0])
for d, p0, p1, *_ in rows:
    m[d[:7]][0] += 1; m[d[:7]][1] += p1 - p0
print("by month Δ: " + " · ".join(f"{k} {v_[1]:+.0f} ({v_[0]}d)" for k, v_ in sorted(m.items())))
if "--days" in sys.argv:
    for d, p0, p1, n0, n1 in rows:
        if abs(p1 - p0) > 0.01 or n0 != n1:
            print(f"  {d} {REF} {p0:+8.2f} ({n0}) → {TAG} {p1:+8.2f} ({n1})  Δ{p1 - p0:+8.2f}")
def key(t):
    return (t.get("classification"), t.get("direction"), round(float(t.get("entry") or 0), 2))


added, removed = [], []
for d in common:
    k1 = collections.Counter(key(t) for t in v[d][1]); k0 = collections.Counter(key(t) for t in r[d][1])
    for t in v[d][1]:
        if k1[key(t)] > k0.get(key(t), 0):
            added.append((d, t)); k1[key(t)] -= 1
    k1 = collections.Counter(key(t) for t in v[d][1])
    for t in r[d][1]:
        if k0[key(t)] > k1.get(key(t), 0):
            removed.append((d, t)); k0[key(t)] -= 1
sa = sum(float(t.get("pnl_usd") or 0) for _, t in added); sr = sum(float(t.get("pnl_usd") or 0) for _, t in removed)
print(f"trades: added {len(added)} (wins {sum(1 for _, t in added if float(t.get('pnl_usd') or 0) > 0)}, Σ{sa:+.2f}$) · "
      f"removed {len(removed)} (Σ{sr:+.2f}$) · the rest of Δ is changed exits/targets of the same trades")
if "--trades" in sys.argv:
    for d, t in added:
        print(f"  + {d} {t.get('entry_il', '')} {t.get('classification')} {t.get('direction')} {t.get('entry')} {t.get('outcome')} {float(t.get('pnl_usd') or 0):+.2f}")
    for d, t in removed:
        print(f"  - {d} {t.get('entry_il', '')} {t.get('classification')} {t.get('direction')} {t.get('entry')} {t.get('outcome')} {float(t.get('pnl_usd') or 0):+.2f}")
missing = sorted(set(r) - set(v))
if missing:
    print("missing in", TAG, ":", " ".join(missing))
