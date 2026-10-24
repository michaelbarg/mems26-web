#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ש2-C refinement check (REPORT.md §ה): the phase-C balance question refuses (a) entries against an ACCEPTED IB extension
(rule A) and (b) entries into EFFORT against the trade. Two flaws seen in the move windows (07.10 18:00–18:15 longs after the
down-extension had already failed; 08.10 19:20 short after a buying spike that closed back down; 23.10 19:51/19:55 shorts).
Variant ש2-C′:  (a′) rule A AND the last close itself still beyond the IB edge on the stop side;
                (b′) effort against AND that effort had a result (the largest-|delta| bar of the last 3 closed in the
                     effort's half of its range) — effort without result = absorption, not a reason to refuse.
Measured on: the 35 real trades, the move-window candidates (missed.json), and (secondary) the 81-session candidates
(cand81.json). Read-only.   python3 harness_out/t645/examiner/xq2c.py > harness_out/t645/examiner/q2c.txt
"""
import os, sys, json, collections, datetime as dt
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner")
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
import xlib


def extra(day, ts, direction):
    bs = xlib.rth_days()[day]; k = xlib.bar_index_at(bs, ts); short = direction == "SHORT"
    if k < 11:
        return None, None
    ibh = max(x["h"] for x in bs[:12]); ibl = min(x["l"] for x in bs[:12]); last = bs[k]
    last_beyond = (last["c"] > ibh) if short else (last["c"] < ibl)
    l3 = bs[max(0, k - 2):k + 1]
    eb = max(l3, key=lambda x: abs(x["d"] or 0))
    mid = (eb["h"] + eb["l"]) / 2.0
    eff_result = (eb["c"] >= mid) if short else (eb["c"] <= mid)
    return last_beyond, eff_result


def q2c(f, lb, er):
    if f["rel"] != "BAL" or f["phase"] != "C":
        return False, False
    old = f["ruleA"] == "accepted_against" or bool(f["eff_against"])
    new = (f["ruleA"] == "accepted_against" and bool(lb)) or (bool(f["eff_against"]) and bool(er))
    return old, new


def st(c):
    n = sum(c.values())
    return "n=%4d good %3d (%2.0f%%) bad %3d (%2.0f%%) flat %3d" % (n, c["good"], 100.0 * c["good"] / max(n, 1), c["bad"], 100.0 * c["bad"] / max(n, 1), c["flat"])


D = xlib.data()
TR = json.load(open(os.path.join(xlib.HERE, "trades_exam.json")))
print("## 1. real trades: ש2-C (old) vs ש2-C′ (new)")
for r in TR:
    t = [x for x in D["trades"] if x["id"] == r["id"]][0]
    ts = dt.datetime.fromisoformat(t["entry_ts"])
    f = xlib.features(r["day"], ts, r["dir"], r["entry"])
    if not f:
        continue
    lb, er = extra(r["day"], ts, r["dir"])
    o, n = q2c(f, lb, er)
    if o or n:
        print("  #%s %s %s %-20s %-5s pnl %-8s verdict %-10s A=%s last_beyond=%s eff=%s eff_result=%s → old %s new %s" % (
            r["id"], r["day"][5:], r["hm"], r["pat"][:20], r["dir"], r["pnl"], r["verdict"].get("v"), f["ruleA"], lb, f["eff_against"], er, o, n))

print("\n## 2. move-window candidates (shadow twins, bar label)")
MS = json.load(open(os.path.join(xlib.HERE, "missed.json")))
co = collections.Counter(); cn = collections.Counter()
for m in MS:
    if m["mode"] != "shadow" or not m["label"]:
        continue
    t = [x for x in D["trades"] if x["id"] == m["id"]][0]
    ts = dt.datetime.fromisoformat(t["entry_ts"])
    f = xlib.features(m["day"], ts, m["dir"], m["entry"])
    if not f:
        continue
    lb, er = extra(m["day"], ts, m["dir"])
    o, n = q2c(f, lb, er)
    if o:
        co[m["label"]] += 1
    if n:
        cn[m["label"]] += 1
    if o != n:
        print("  %s %s %-22s %-5s @%s lab %-5s blocked=%s A=%s last_beyond=%s eff=%s eff_result=%s → old %s new %s" % (
            m["day"][5:], m["hm"], m["pat"][:22], m["dir"], m["entry"], m["label"], m["blocked"], f["ruleA"], lb, f["eff_against"], er, o, n))
print("  refused by old ש2-C:", st(co))
print("  refused by new ש2-C′:", st(cn))

print("\n## 3. 81 sessions — candidate level (secondary)")
xlib.use_bars(os.path.join(xlib.HERE, "bars81.json"))
C = json.load(open(os.path.join(xlib.HERE, "cand81.json")))
agg = collections.defaultdict(collections.Counter)
for o_ in C:
    f = o_["f"]
    if f["rel"] != "BAL" or f["phase"] != "C":
        continue
    ts = dt.datetime.fromisoformat(o_["ts"])
    lb, er = extra(o_["day"], ts, o_["dir"])
    o, n = q2c(f, lb, er)
    agg["BAL-C all"][o_["lab"]] += 1
    agg["old refuses"][o_["lab"]] += 1 if o else 0
    agg["new refuses"][o_["lab"]] += 1 if n else 0
    agg["old refuses, new passes"][o_["lab"]] += 1 if (o and not n) else 0
    agg["neither refuses"][o_["lab"]] += 1 if not (o or n) else 0
    if f["ruleA"] == "accepted_against":
        agg["A accepted & last beyond" if lb else "A accepted & last back inside"][o_["lab"]] += 1
    if f["eff_against"]:
        agg["effort with result" if er else "effort without result (absorbed)"][o_["lab"]] += 1
for k in ("BAL-C all", "old refuses", "new refuses", "old refuses, new passes", "neither refuses", "A accepted & last beyond",
          "A accepted & last back inside", "effort with result", "effort without result (absorbed)"):
    c = agg[k]; c = collections.Counter({x: v for x, v in c.items() if v})
    print("  %-36s %s" % (k, st(c)))
