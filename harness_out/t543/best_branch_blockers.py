# -*- coding: utf-8 -*-
"""Read-only: for the strongest branches of the live tree (by candidate win%/Σ), what happened to the candidates the
tree said TAKE on — fired in the replay, blocked by which post-tree gate, shadow-only producer, or lost to the slot?
Source: harness_out/t466/t529b_*.json (routes.tree_v3.path, blocked_by, shadow_only, result) + trades."""
import collections, glob, json, os, sys
os.chdir("/Users/michael/Downloads/mems26_web_git")
PATHS = [
    "opening_type=OPEN_DRIVE/phase=C/day_type=Trend_Normal/rel_bias=with",
    "opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=*(FORMING)/rel_bias=with",
    "opening_type=OPEN_DRIVE/phase=B/day_type=*(FORMING)/rel_bias=with",
    "opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(FORMING)/kind=REVERSAL",
]
for P in PATHS:
    tot = collections.Counter(); fired = []; per_day = collections.Counter(); slot = 0
    for f in sorted(glob.glob("harness_out/t466/t529b_2026-*.json")):
        j = json.load(open(f)); d = os.path.basename(f)[6:16]
        trades_by_cls = collections.Counter((t.get("classification"), t.get("direction")) for t in j.get("trades") or [])
        for r in j.get("routes") or []:
            tv = r.get("tree_v3") or {}
            if not isinstance(tv, dict) or tv.get("path") != P:
                continue
            per_day[d] += 1
            res = r.get("result") or {}
            if res.get("live") or res.get("demo"):
                tot["FIRED (replay trade)"] += 1; fired.append((d, r.get("il", "")[:5], r.get("classification"), r.get("direction")))
            elif r.get("shadow_only"):
                tot["shadow-only producer (never fires live)"] += 1
            elif r.get("blocked_by"):
                tot["gate: " + str(r.get("blocked_by"))] += 1
            elif res.get("shadow"):
                tot["TAKE but shadow result (slot held / not live-capable)"] += 1
            else:
                tot["other: " + str(res)[:60]] += 1
    n = sum(tot.values())
    print("\n== %s\n   candidates %d on %d sessions" % (P, n, len(per_day)))
    for k, v in tot.most_common():
        print("   %4d  %s" % (v, k))
    if fired:
        print("   fired:", ", ".join("%s %s %s %s" % x for x in fired[:12]))
