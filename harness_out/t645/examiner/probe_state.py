#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe: print per session θ, swings and the candidate direction-state variants (state changes only)."""
import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner")
import xlib

days = sys.argv[1:] or ["2026-10-23"]
D = xlib.rth_days()


def changes(bs, st):
    out = []; prev = None
    for i, b in enumerate(bs):
        if st[i] != prev:
            out.append("%s %s" % (xlib.il_hm(b), st[i])); prev = st[i]
    return " · ".join(out)


for day in days:
    bs = D[day]; th = xlib.theta_series(day)
    R = xlib.day_refs(day)
    print("=" * 30, day, "θ open %.2f mid %.2f | IB %.2f-%.2f | prevVA(bars) %.2f-%.2f POC %.2f | sysVA %s-%s | H/L %.2f/%.2f" % (
        th[0], th[len(th) // 2], R["ib_lo"], R["ib_hi"], R["p_val"], R["p_vah"], R["p_poc"], R.get("s_val"), R.get("s_vah"), R["p_hi"], R["p_lo"]))
    for nm, zz in (("close", xlib.zigzag), ("ext", xlib.zigzag_ext)):
        sw = zz(bs, th)
        print("[%s] swings:" % nm, " ".join("%s%s@%s(c%s)" % (s["type"], s["px"], xlib.il_hm(bs[s["i"]]), xlib.il_hm(bs[s["ci"]])) for s in sw))
        for lab, kw in (("bos", dict(accept=1)), ("bos+fail6", dict(accept=1, fail_bars=6)), ("bos2", dict(accept=2)), ("bos2+fail6", dict(accept=2, fail_bars=6))):
            st, ev = xlib.direction_state(bs, th, sw, **kw)
            print("   %-11s %s" % (lab, changes(bs, st)))
        print("   %-11s %s" % ("dow", changes(bs, xlib.structure_state(bs, sw))))
