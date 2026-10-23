# -*- coding: utf-8 -*-
"""Totals per tag over the common days: net $, trades, wins, blocked by the new gates, BE_PRE_T1 exits."""
import json, glob, os, collections
base = "harness_out/t640/days"
tags = ["live", "f1", "f6", "f7", "f167"]
days = {t: {os.path.basename(p)[len(t) + 1:-5]: p for p in glob.glob("%s/%s_2026-*.json" % (base, t))} for t in tags}
common = sorted(set.intersection(*[set(v.keys()) for v in days.values()]))
print("common days:", len(common), common[0], "→", common[-1])
rows = {}
for t in tags:
    net = 0.0; n = 0; w = 0; filled = 0; bl = collections.Counter(); bepre = 0; months = collections.defaultdict(float)
    for d in common:
        j = json.load(open(days[t][d]))
        for tr in j.get("trades", []):
            if not tr.get("filled"):
                continue
            filled += 1
            p = float(tr.get("pnl_usd") or 0)
            net += p; months[d[:7]] += p
            n += 1; w += 1 if p > 0 else 0
            if any("BE_PRE_T1" in str(l.get("exit") or l.get("reason") or l) for l in (tr.get("legs") or [])):
                bepre += 1
        for g in j.get("gateway_decisions", []) or []:
            b = str(g.get("blocked_by") or "")
            if b in ("mid_value_no_edge_test", "wait_for_test"):
                bl[b] += 1
    rows[t] = (net, n, w, dict(bl), bepre, dict(months))
    print("%-5s net %9.2f  trades %3d  win%% %4.0f  blocked %s  BE_PRE_T1-exits %d  months %s" % (
        t, net, n, (100.0 * w / n if n else 0), dict(bl), bepre, {k: round(v) for k, v in sorted(months.items())}))
