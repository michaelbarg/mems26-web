#!/usr/bin/env python3
"""F17b/T-412 — compare the harness under S2_TRIGGER_QUALITY_V1 shadow vs 1.

Field-scoped like harness_out/night_0916/cmp_routes.py: routes / live_cmds /
Σ$ (the fixed model's daily_pnl_harness) are the decision-bearing fields; a
whole-file checksum would break on wall-clock fields that carry no meaning.

Usage: python3 harness_out/t412/cmp_t412.py 20260915 20260911 ...
"""
import json
import sys

SESS = sys.argv[1:] or ["20260915", "20260911", "20260910", "20260909", "20260908"]


def load(p):
    with open(p) as f:
        return json.load(f)


def live_cmds(d):
    return sum(1 for r in d["routes"]
               if (r["exec"].get("live", {}) or {}).get("command")
               and not ((r["exec"]["live"]["command"] or {}).get("rejected")))


def canon(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


print("session   | routes sh/tq | blocked sh/tq | live_cmds sh/tq | trades sh/tq | Sum$ shadow | Sum$ tq1 | delta")
print("-" * 118)
tot_s = tot_t = 0.0
ident = True
for s in SESS:
    try:
        a, b = load("harness_out/t412/%s_shadow.json" % s), load("harness_out/t412/%s_tq1.json" % s)
    except IOError as e:
        print("%s | MISSING (%s)" % (s, e))
        continue
    ra, rb = len(a["routes"]), len(b["routes"])
    ba = sum(1 for r in a["routes"] if r.get("blocked_by"))
    bb = sum(1 for r in b["routes"] if r.get("blocked_by"))
    pa, pb = a["daily_pnl_harness"], b["daily_pnl_harness"]
    tot_s += pa
    tot_t += pb
    if canon(a["routes"]) != canon(b["routes"]):
        ident = False
    print("%s  |   %3d / %3d  |    %3d / %3d   |      %2d / %2d     |    %2d / %2d    |  %9.2f | %8.2f | %+8.2f"
          % (s, ra, rb, ba, bb, live_cmds(a), live_cmds(b),
             len(a["trades"]), len(b["trades"]), pa, pb, pb - pa))
print("-" * 118)
print("TOTAL Sum$: shadow %.2f | tq1 %.2f | delta %+.2f" % (tot_s, tot_t, tot_t - tot_s))
print("routes byte-identical across all sessions:", ident)

# S2 producer fires only (the ones the flag can touch)
for s in SESS:
    try:
        a, b = load("harness_out/t412/%s_shadow.json" % s), load("harness_out/t412/%s_tq1.json" % s)
    except IOError:
        continue
    fa = [r for r in a["routes"] if str(r.get("classification", "")).startswith(("REACTIVE", "INITIATIVE"))]
    fb = [r for r in b["routes"] if str(r.get("classification", "")).startswith(("REACTIVE", "INITIATIVE"))]
    if fa or fb:
        print("%s  REACTIVE/INITIATIVE routes: shadow=%d tq1=%d  %s"
              % (s, len(fa), len(fb),
                 sorted(set(r.get("classification") for r in fa) ^
                        set(r.get("classification") for r in fb)) or "same set"))
