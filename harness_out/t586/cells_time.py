#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-586 — stability of the reference replay by cell over time. Read-only on harness_out/t466/<TAG>_*.json.
usage: cells_time.py [TAG=t567ref] [--by=leaf|pattern|hour|otype|daytype|phase|rel]"""
import json, glob, sys, collections
TAG = next((a for a in sys.argv[1:] if not a.startswith("--")), "t567ref")
BY = next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--by=")), "leaf")
COMM = 2.60
rows = []   # (session, key, pnl, pattern, il, dir)
for f in sorted(glob.glob(f"harness_out/t466/{TAG}_2026-*.json")):
    d = json.load(open(f)); s = d["session"]
    r_by_tid = {}
    for r in d.get("routes") or []:
        lv = (r.get("exec") or {}).get("live") or {}
        if lv.get("trade_id"):
            r_by_tid[str(lv["trade_id"])] = r
    for t in d.get("trades") or []:
        r = r_by_tid.get(str(t["trade_id"])) or {}
        tv = r.get("tree_v3") or {}; vec = tv.get("vec") or {}
        hour = int(t["fired_il"][:2])
        key = {"leaf": tv.get("id") or "?", "pattern": t["classification"], "hour": hour,
               "otype": vec.get("opening_type"), "daytype": vec.get("day_type"), "phase": vec.get("phase"),
               "rel": vec.get("rel_bias"), "kind": vec.get("kind"),
               "open": "OPEN(16:45-17:00)" if hour == 16 or (hour == 17 and int(t["fired_il"][3:5]) == 0) else "LATER"}[BY]
        rows.append((s, str(key), float(t["pnl_usd"] or 0), t["classification"], t["fired_il"][:5], t["direction"]))
months = sorted(set(r[0][:7] for r in rows))
agg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0]))
tot = collections.defaultdict(lambda: [0, 0.0, 0])
for s, k, p, *_ in rows:
    agg[k][s[:7]][0] += 1; agg[k][s[:7]][1] += p
    tot[k][0] += 1; tot[k][1] += p; tot[k][2] += (1 if p > 0 else 0)
print(f"{TAG} · by {BY} · {len(rows)} trades · months {months}")
hdr = f"{'key':58s} {'n':>3s} {'Σ$':>8s} {'win%':>5s} {'$/tr':>6s} | " + " ".join(f"{m[2:]:>9s}" for m in months) + " | months<0"
print(hdr)
for k, (n, p, w) in sorted(tot.items(), key=lambda kv: kv[1][1]):
    cells = " ".join((f"{agg[k][m][1]:+6.0f}/{agg[k][m][0]:<2d}" if agg[k][m][0] else "        -") for m in months)
    neg = sum(1 for m in months if agg[k][m][0] and agg[k][m][1] < 0)
    print(f"{k[:58]:58s} {n:3d} {p:+8.1f} {100*w/n:5.0f} {p/n:+6.1f} | {cells} | {neg}")
