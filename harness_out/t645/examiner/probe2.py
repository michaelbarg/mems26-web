#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 2: the final direction state (dstate) per session — events + the state at every real trade's entry."""
import sys, datetime as dt
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner")
import xlib

days = sys.argv[1:] or xlib.data()["days"]
D = xlib.rth_days()
TR = [t for t in xlib.data()["trades"] if t["mode"] in ("demo", "live")]
opts = dict(accept=2, fail_bars=6, halfback=True)
for day in days:
    bs = D[day]; th = xlib.theta_series(day)
    sw = xlib.zigzag_ext(bs, th)
    st, ev = xlib.dstate(bs, th, sw, **opts)
    R = xlib.day_refs(day)
    print("=" * 20, day, "open %.2f (%s) IB %.2f-%.2f H/L %.2f/%.2f close %.2f | yVA %.2f-%.2f POC %.2f yH/L %.2f/%.2f" % (
        R["open"], R.get("open_loc"), R["ib_lo"], R["ib_hi"], R["hi"], R["lo"], R["close"], R["p_val"], R["p_vah"], R["p_poc"], R["p_hi"], R["p_lo"]))
    for e in ev:
        print("   %s → %-6s (%s) %s" % (xlib.il_hm(bs[e["i"]]), e["to"], e["px"], e["why"]))
    thr = max(15.0, 0.5 * (R["ib_hi"] - R["ib_lo"]))
    tp = xlib.turning_points(bs, thr)
    print("   turning points (thr %.2f): %s" % (thr, " ".join("%s%s@%s" % (k, p, xlib.il_hm(bs[i])) for k, p, i in tp)))
    for t in TR:
        if t["day"] != day:
            continue
        ets = dt.datetime.fromisoformat(t["entry_ts"])
        k = xlib.bar_index_at(bs, ets)
        s = st[k] if k >= 0 else "BAL"
        nxt = next((e for e in ev if e["i"] > k), None)
        pos, pl = xlib.hour_pos(bs, k, float(t["entry_price"]), t["direction"]) if k >= 0 else (None, "-")
        print("   #%s %s %s %s %s @%s → state %s (last closed %s) · pos_hour %s · next: %s · pnl %s" % (
            t["id"], t["mode"], ets.astimezone(xlib.IL).strftime("%H:%M"), t["pattern_id_at_entry"], t["direction"], t["entry_price"], s,
            xlib.il_hm(bs[k]) if k >= 0 else "-", pl, ("%s %s" % (xlib.il_hm(bs[nxt["i"]]), nxt["to"])) if nxt else "-", t["pnl_usd"]))
