#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ש5 on the LIVE record of the examined days (v9_trades shadow twins with blocked_by = tree:bias, as dumped in data.json),
not the T-640 replay: the direction state at the candidate, its location, the bar label (+1R before its own initial stop),
and the other questions. De-duplicated: the same pattern+direction within 10 minutes counts once. Read-only.
  python3 harness_out/t645/examiner/xlet_live.py > harness_out/t645/examiner/let_in_live.txt
"""
import os, sys, json, collections, datetime as dt
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner")
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
import xlib


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def init_stop(t):
    for k in ("stop_initial", "entry_stop", "initial_stop", "stop"):
        v = fnum(t.get(k))
        if v:
            return v
    return None


D = xlib.data()
rows = []; last = {}
for t in sorted(D["trades"], key=lambda t: t["entry_ts"] or ""):
    if t["mode"] != "shadow" or (t.get("blocked_by") or "") != "tree:bias" or not t["entry_ts"]:
        continue
    ts = dt.datetime.fromisoformat(t["entry_ts"]); day = t["day"]
    key = (day, t["pattern_id_at_entry"], t["direction"])
    if key in last and (ts - last[key]).total_seconds() < 600:
        continue
    last[key] = ts
    ep = fnum(t["entry_price"]); s0 = init_stop(t)
    bs = xlib.rth_days()[day]
    lab, lt = xlib.label_candidate(bs, ts, t["direction"], ep, s0) if (ep and s0) else (None, None)
    f = xlib.features(day, ts, t["direction"], ep)
    if not f:
        continue
    q = xlib.ask(f)
    rows.append(dict(day=day, hm=ts.astimezone(xlib.IL).strftime("%H:%M"), id=t["id"], pat=t["pattern_id_at_entry"], dir=t["direction"],
                     entry=ep, stop=s0, lab=lab, lt=lt, rel=f["rel"], state=f["state"], pos=round(f["pos"], 2), phase=f["phase"],
                     q=q, sh=(t.get("outcome"), t.get("pnl_usd"))))
agg = collections.defaultdict(collections.Counter)
for r in rows:
    agg[r["rel"]][r["lab"]] += 1
    if r["rel"] == "with" and not r["q"]:
        agg["with & all questions pass"][r["lab"]] += 1
print("tree:bias refusals on the examined days (live record, de-duplicated):")
for k, c in agg.items():
    n = sum(c.values())
    print("  state %-28s n=%3d good %3d bad %3d flat %3d none %d" % (k, n, c["good"], c["bad"], c["flat"], c[None]))
print("\nwith the state (ש5 would release):")
for r in rows:
    if r["rel"] == "with":
        print("  %s %s #%s %-22s %-5s @%-8s stop %-8s state %s pos %.2f ph %s lab %-5s %-5s q %-8s shadow %s" % (
            r["day"][5:], r["hm"], r["id"], (r["pat"] or "?")[:22], r["dir"], r["entry"], r["stop"], r["state"], r["pos"], r["phase"],
            r["lab"], r["lt"] or "", ",".join(r["q"]) or "pass", r["sh"]))
