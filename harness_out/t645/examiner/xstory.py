#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part A — the raw material for each session's story in Dalton terms (IL times, closed 5-min bars): yesterday's value
and range (TPO from bars + the system's v9_tpo_sessions row), overnight range, the open vs yesterday, the first 30 minutes,
the system's opening label (replay s1), the IB, every extension with its acceptance (closes beyond, first/last, return
inside), the significant swings and the θ-swings, the day-type label changes of the replay, the final value. Read-only.

  python3 harness_out/t645/examiner/xstory.py > harness_out/t645/examiner/story.txt
"""
import os, sys, json, collections
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner")
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
import xlib

for day in xlib.data()["days"]:
    bs, th, sw, st, ev = xlib.day_state(day)
    R = xlib.day_refs(day)
    ibh, ibl = R["ib_hi"], R["ib_lo"]; ibw = ibh - ibl
    print("=" * 100)
    print("# %s (prev %s)" % (day, R["prev"]))
    print("אתמול (TPO מברים): VAH %.2f VAL %.2f POC %.2f · שיא %.2f שפל %.2f סגירה %.2f · שורת-המערכת: VAH %s VAL %s POC %s" % (
        R["p_vah"], R["p_val"], R["p_poc"], R["p_hi"], R["p_lo"], R["p_close"], R.get("s_vah"), R.get("s_val"), R.get("s_poc")))
    print("לילה: שיא %s שפל %s · פתיחה %.2f — %s" % (R.get("on_hi"), R.get("on_lo"), R["open"], R.get("open_loc")))
    print("30 הדקות הראשונות (IL O H L C Δ):")
    for b in bs[:6]:
        print("   %s %.2f %.2f %.2f %.2f %+.0f" % (xlib.il_hm(b), b["o"], b["h"], b["l"], b["c"], b["d"] or 0))
    rp = xlib.replay(day) or {}
    s1 = rp.get("s1") or []
    ots = []; dts = []
    for x in s1:
        if not ("16:30" <= x["il"] <= "22:55"):
            continue
        o = x.get("ot_locked") or x.get("machine_opening")
        if not ots or ots[-1][1] != o:
            ots.append((x["il"], o))
        p = x.get("published")
        if not dts or dts[-1][1] != p:
            dts.append((x["il"], p))
    print("תווית-פתיחה (ריפליי): %s" % " → ".join("%s %s" % a for a in ots))
    print("תווית סוג-יום (ריפליי, published): %s" % " → ".join("%s %s" % a for a in dts))
    print("IB %.2f–%.2f (%.2f נק׳) · θ בפתיחה %.2f · היום: שיא %.2f שפל %.2f סגירה %.2f · VA סופי %.2f–%.2f POC %.2f" % (
        ibl, ibh, ibw, th[0], R["hi"], R["lo"], R["close"], R["val"], R["vah"], R["poc"]))
    # extensions and acceptance after the IB
    for side in ("up", "down"):
        after = bs[12:]
        if side == "up":
            beyond = [(i + 12, b) for i, b in enumerate(after) if b["c"] > ibh]
            ext = R["hi"] - ibh
        else:
            beyond = [(i + 12, b) for i, b in enumerate(after) if b["c"] < ibl]
            ext = ibl - R["lo"]
        if ext <= 0:
            print("הרחבה %s: אין" % ("למעלה" if side == "up" else "למטה")); continue
        # runs of consecutive closes beyond
        runs = []; cur = []
        for i, b in beyond:
            if cur and i == cur[-1][0] + 1:
                cur.append((i, b))
            else:
                if cur: runs.append(cur)
                cur = [(i, b)]
        if cur: runs.append(cur)
        first_touch = next((xlib.il_hm(b) for b in bs[12:] if (b["h"] > ibh if side == "up" else b["l"] < ibl)), None)
        print("הרחבה %s: %.2f נק׳ · נגיעה ראשונה %s · סגירות מעבר %d · רצפים: %s" % (
            "למעלה" if side == "up" else "למטה", ext, first_touch, len(beyond),
            "; ".join("%s–%s (%d)" % (xlib.il_hm(r[0][1]), xlib.il_hm(r[-1][1]), len(r)) for r in runs) or "—"))
    thr = max(15.0, 0.5 * ibw)
    tp = xlib.turning_points(bs, thr)
    print("תנועות משמעותיות (סף %.2f): %s" % (thr, " → ".join("%s %s@%s" % ("שפל" if k == "L" else "שיא", p, xlib.il_hm(bs[i])) for k, p, i in tp)))
    print("סווינגים (θ, מאושרים): %s" % " ".join("%s%s@%s" % ("H" if s["type"] == "H" else "L", s["px"], xlib.il_hm(bs[s["i"]])) for s in sw))
    print("מצב-הכיוון: %s" % " · ".join("%s %s" % (xlib.il_hm(bs[e["i"]]), xlib.HE[e["to"]]) for e in ev))
    print("30 דק׳ (IL O H L C V Δ):")
    per = collections.defaultdict(list)
    for i, b in enumerate(bs):
        per[i // 6].append(b)
    for k in sorted(per):
        pb = per[k]
        print("   %s %.2f %.2f %.2f %.2f %6d %+6.0f" % (xlib.il_hm(pb[0]), pb[0]["o"], max(x["h"] for x in pb), min(x["l"] for x in pb), pb[-1]["c"],
                                                   sum(x["v"] for x in pb), sum((x["d"] or 0) for x in pb)))
