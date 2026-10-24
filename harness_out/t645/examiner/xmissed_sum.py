#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part D summary: one line per significant move (missed.json, xmissed.py) — size, when the direction state confirmed
it, how many system candidates it had while young, how many reached +1R first (bar label), the first good one and its
blocker, whether a real (demo/live) trade was in the move's direction; plus the blocker histogram of the good ones.
Read-only.  python3 harness_out/t645/examiner/xmissed_sum.py > harness_out/t645/examiner/missed_sum.txt
"""
import os, re, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, "missed.json")))
TXT = open(os.path.join(HERE, "missed.txt"), encoding="utf-8").read().splitlines()

# leg headers (also legs without candidates)
legs = []; day = None
for ln in TXT:
    m = re.match(r"^(2026-\d\d-\d\d) · סף ([\d.]+)", ln)
    if m:
        day = m.group(1); thr = m.group(2); continue
    m = re.match(r"^(לונג|שורט) ([\d.]+)@(\d\d:\d\d) → ([\d.]+)@(\d\d:\d\d) \(([-+\d.]+)\) · מצב-כיוון אישר (.+?) · 60% מהתנועה ב-(\d\d:\d\d)", ln)
    if m:
        legs.append(dict(day=day, thr=thr, d=m.group(1), a=m.group(2), ta=m.group(3), b=m.group(4), tb=m.group(5), size=m.group(6),
                         conf=m.group(7), t60=m.group(8), key="%s@%s→%s@%s" % (m.group(2), m.group(3), m.group(4), m.group(5))))
hist = collections.Counter(); hist_all = collections.Counter(); tot = collections.Counter()
print("%-10s %-5s %-30s %-8s %-18s %-6s | cands good bad flat | real trade in dir | first good candidate (blocker)" % (
    "day", "dir", "leg", "size", "state confirmed", "60%"))
for L in legs:
    rows = [r for r in M if r["day"] == L["day"] and r["leg"] == L["key"]]
    sh = [r for r in rows if r["mode"] == "shadow"]
    real = [r for r in rows if r["mode"] in ("demo", "live")]
    c = collections.Counter(r["label"] for r in sh)
    good = [r for r in sh if r["label"] == "good"]
    fg = good[0] if good else None
    for r in good:
        hist[(r["blocked"] or "— (passed the gates)")] += 1
    for r in sh:
        hist_all[(r["blocked"] or "— (passed the gates)", r["label"])] += 1
    tot["legs"] += 1; tot["with_cand"] += bool(sh); tot["with_good"] += bool(good); tot["traded"] += bool(real)
    print("%-10s %-5s %-30s %-8s %-18s %-6s | %5d %4d %3d %4d | %-17s | %s" % (
        L["day"][5:], L["d"], L["key"], L["size"], L["conf"][:18], L["t60"], len(sh), c["good"], c["bad"], c["flat"],
        ",".join("#%s %s" % (r["id"], r["hm"]) for r in real) or "—",
        ("%s %s %s (%s)" % (fg["hm"], fg["pat"], fg["entry"], fg["blocked"] or "passed")) if fg else "—"))
print("\nlegs %d · with a system candidate %d · with a good one %d · with a real trade in the move's direction %d" % (
    tot["legs"], tot["with_cand"], tot["with_good"], tot["traded"]))
print("\nblockers of the GOOD candidates (shadow twins, all legs):")
for k, n in hist.most_common():
    print("  %-40s %d" % (k, n))
print("\nblocker × label (all shadow candidates in the windows):")
by = collections.defaultdict(collections.Counter)
for (b, lab), n in hist_all.items():
    by[b][lab] += n
for b, cc in sorted(by.items(), key=lambda kv: -sum(kv[1].values())):
    print("  %-40s good %3d bad %3d flat %3d" % (b, cc["good"], cc["bad"], cc["flat"]))
