#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ש5 — second part: candidates refused for BIAS (tree:bias) while AGAINST the direction state but at a DEFENDED session
extreme (turn_rel edge/with — the ש1 exception), e.g. 20.10 18:10 REACTIVE_SHORT. Secondary, candidate level.
Read-only; input cand81.json.
  python3 harness_out/t645/examiner/xlet2.py > harness_out/t645/examiner/let_in2.txt
"""
import os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "cand81.json")))
EXAM = {"2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09",
        "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"}


def st(rs):
    c = collections.Counter(r["lab"] for r in rs); n = len(rs)
    return "n=%4d good %3d (%2.0f%%) bad %3d (%2.0f%%) flat %3d" % (n, c["good"], 100.0 * c["good"] / max(n, 1),
                                                                     c["bad"], 100.0 * c["bad"] / max(n, 1), c["flat"])


B = [o for o in C if (o.get("blocked") or "") == "tree:bias"]
print("tree:bias all", st(B))
for nm, fn in (("against & turn_rel edge/with", lambda o: o["f"]["rel"] == "against" and o["f"]["turn_rel"] in ("edge", "with")),
               ("against & turn_rel edge/with & ruleA != accepted", lambda o: o["f"]["rel"] == "against" and o["f"]["turn_rel"] in ("edge", "with") and o["f"]["ruleA"] != "accepted_against"),
               ("against & passes ש1 (any exception)", lambda o: o["f"]["rel"] == "against" and "ש1" not in o["q"]),
               ("against & refused by ש1", lambda o: o["f"]["rel"] == "against" and "ש1" in o["q"]),
               ("BAL & passes all questions", lambda o: o["f"]["rel"] == "BAL" and not o["q"]),
               ("with (ש5 proper)", lambda o: o["f"]["rel"] == "with")):
    X = [o for o in B if fn(o)]
    print("%-50s 81d %s | examined %s" % (nm, st(X), st([o for o in X if o["day"] in EXAM])))
print("\nexamined days: against & turn_rel edge/with")
for o in sorted([o for o in B if o["day"] in EXAM and o["f"]["rel"] == "against" and o["f"]["turn_rel"] in ("edge", "with")], key=lambda o: o["ts"]):
    print("  %s %s %-22s %-5s @%-8s R %5.2f state %s turn %s/%s A %s pos %.2f lab %s q %s" % (
        o["day"][5:], o["il"], o["pat"][:22], o["dir"], o["entry"], o["R"] or 0, o["f"]["state"], o["f"]["turn"], o["f"]["turn_rel"],
        o["f"]["ruleA"], o["f"]["pos"], o["lab"], ",".join(o["q"]) or "pass"))
