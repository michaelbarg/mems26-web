#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ש5 (the let-in question) — secondary, candidate level: candidates the tree refused for BIAS (tree:bias, i.e. rel_bias
against the static dir_hint) while the examiner's direction state was WITH the candidate. Label = +1R before the
candidate's own stop (T-643 rule). Also: the same for tree:location / tree:kind refusals with the state WITH the candidate.
Read-only; input cand81.json (xcand81.py).
  python3 harness_out/t645/examiner/xlet.py > harness_out/t645/examiner/let_in.txt
"""
import os, sys, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "cand81.json")))
EXAM = {"2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09",
        "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"}


def st(rs):
    c = collections.Counter(r["lab"] for r in rs); n = len(rs)
    return "n=%4d good %3d (%2.0f%%) bad %3d (%2.0f%%) flat %3d" % (n, c["good"], 100.0 * c["good"] / max(n, 1),
                                                                     c["bad"], 100.0 * c["bad"] / max(n, 1), c["flat"])


print("candidates with features:", len(C))
for blk in ("tree:bias", "tree:location", "tree:kind", "tree:stand_down"):
    for rel in ("with", "BAL", "against"):
        X = [o for o in C if (o.get("blocked") or "") == blk and o["f"]["rel"] == rel]
        print("%-16s state %-7s 81d %s | examined days %s" % (blk, rel, st(X), st([o for o in X if o["day"] in EXAM])))
    print()
print("## ש5 = release tree:bias when the state is WITH the candidate — by phase and location (81 days)")
X = [o for o in C if (o.get("blocked") or "") == "tree:bias" and o["f"]["rel"] == "with"]
for ph in ("B", "C", "D"):
    for pl in ("edge", "middle", "far"):
        Y = [o for o in X if o["f"]["phase"] == ph and o["f"]["pos_lab"] == pl]
        if Y:
            print("  phase %s pos %-6s %s" % (ph, pl, st(Y)))
print("  ש5 and the other questions also pass:", st([o for o in X if not o["q"]]))
print("\n## ש5 on the examined days, one by one")
for o in sorted([o for o in X if o["day"] in EXAM], key=lambda o: o["ts"]):
    print("  %s %s %-22s %-5s @%-8s R %5.2f state %s since %s pos %.2f phase %s lab %-5s q %s" % (
        o["day"][5:], o["il"], o["pat"][:22], o["dir"], o["entry"], o["R"] or 0, o["f"]["state"], o["f"]["since"],
        o["f"]["pos"], o["f"]["phase"], o["lab"], ",".join(o["q"]) or "pass"))
