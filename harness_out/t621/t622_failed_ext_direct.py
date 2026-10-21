# -*- coding: utf-8 -*-
"""T-622d direct effect: which trades in a variant's 78 sessions went through T-529's take_failed_ext_responsive
leaf on the Normal responsive row in mid_value (the trades the POC rule refuses) — and what they made.
Usage: python3 harness_out/t621/t622_failed_ext_direct.py [tag ...]"""
import glob
import json
import os
import sys
from collections import defaultdict

OUT = "/Users/michael/Downloads/mems26_web_git/harness_out/t621/days"
for tag in (sys.argv[1:] or ["base"]):
    rows, by_leaf = [], defaultdict(lambda: [0, 0.0])
    for f in sorted(glob.glob(os.path.join(OUT, f"{tag}_2026-*.json"))):
        d = json.load(open(f))
        routes = {}
        for r in d.get("routes") or []:
            routes[(r.get("il"), r.get("classification"), r.get("direction"))] = r
        for t in d.get("trades") or []:
            if not t.get("filled"):
                continue
            r = routes.get((t.get("fired_il"), t.get("classification"), t.get("direction")))
            tv = (r or {}).get("tree_v3") or {}
            v = tv.get("vec") or {}
            k = (tv.get("id"), v.get("day_type"), v.get("structure"), v.get("zone"))
            by_leaf[k][0] += 1
            by_leaf[k][1] += float(t.get("pnl_usd") or 0)
            if tv.get("id") == "take_failed_ext_responsive":
                rows.append((d.get("session"), t.get("fired_il"), t.get("classification"), t.get("direction"),
                             v.get("day_type"), v.get("structure"), v.get("zone"), float(t.get("pnl_usd") or 0)))
    print(f"=== {tag}: trades through take_failed_ext_responsive (T-529)")
    tot = defaultdict(lambda: [0, 0.0])
    for x in rows:
        hit = x[4] == "Normal" and x[6] == "mid_value" and x[5] not in ("up", "down", "two_sided")
        tot["POC-rule refuses" if hit else "kept"][0] += 1
        tot["POC-rule refuses" if hit else "kept"][1] += x[7]
        print(("  * " if hit else "    ") + " ".join(str(y) for y in x))
    for k, (n, s) in tot.items():
        print(f"  {k}: n={n} usd={s:+.2f}")
EOF_MARK = None
