#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part B — the direction state bar by bar, its lag behind the actual turning points, and the system's own direction
reads on the same bars (dir_hint Layer-1/Layer-2, structure, turn_state, LSMA side, LSMA+CVD veto, dir_sustained,
day type of the replay). Read-only. Writes state_<day>.json + prints a summary (→ state.txt).

  python3 harness_out/t645/examiner/xstate.py [days...] > harness_out/t645/examiner/state.txt
"""
import os, sys, json, datetime as dt, collections
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner")
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
import xlib
from backend.v9.services import turn_state as TS          # pure functions, no I/O

D = xlib.rth_days()
days = sys.argv[1:] or xlib.data()["days"]
MAP = {"LONG": "UP", "SHORT": "DOWN", "up": "UP", "down": "DOWN", "UP": "UP", "DOWN": "DOWN"}


def to3(x):
    return MAP.get(x, "BAL") if x is not None else "BAL"


def sys_reads(day, bs):
    rp = xlib.replay(day) or {}
    s1 = {x["il"]: x for x in (rp.get("s1") or [])}
    routes = rp.get("routes") or []
    out = []
    ib_h = ib_l = None
    l1 = None   # Layer-1 hint (opening direction) carried from the replay routes before 17:30
    for i, b in enumerate(bs):
        hm = xlib.il_hm(b)
        close_t = b["il"] + dt.timedelta(minutes=5)
        # the replay's own hint at the routes that happened before this bar closed (Layer 1 + whatever the gateway did)
        rh = [r for r in routes if r.get("il", "99")[:5] <= close_t.strftime("%H:%M")]
        rp_hint = rh[-1].get("dp_dir_hint") if rh else None
        if hm < "17:25" and rh:
            l1 = rh[-1].get("dp_dir_hint")
        seen = bs[:i + 1]
        if i >= 11:
            ib_h = max(x["h"] for x in bs[:12]); ib_l = min(x["l"] for x in bs[:12])
        sh = max(x["h"] for x in seen); sl = min(x["l"] for x in seen)
        hint = l1; struct = "forming"
        if ib_h is not None and close_t.strftime("%H:%M") >= "17:30":
            up = max(0.0, sh - ib_h); dn = max(0.0, ib_l - sl)
            if up > dn and up > 0:
                hint = "LONG"
            elif dn > up and dn > 0:
                hint = "SHORT"
            need = max(2.0, 0.10 * (ib_h - ib_l))
            u = sh - ib_h >= need; d = ib_l - sl >= need
            struct = "two_sided" if (u and d) else "up" if u else "down" if d else "none"
        tn = TS.detect_turn([dict(h=x["h"], l=x["l"], c=x["c"]) for x in seen])
        lside = (1 if b["c"] > b["lsma"] else -1) if b.get("lsma") is not None else None
        cvd = sum((x["d"] or 0.0) for x in seen[-3:])
        cs = 1 if cvd > 0 else (-1 if cvd < 0 else 0)
        if lside is None:
            lcv = "NEUTRAL"
        elif cs != 0 and cs == -lside:
            lcv = "NEUTRAL"
        else:
            lcv = "UP" if lside > 0 else "DOWN"
        # dir_sustained (LSMA_SUSTAIN_BARS=2) + CONT_TREND_STATE_CERT_V1
        last2 = [x for x in seen[-2:] if x.get("lsma") is not None]
        sides = [1 if x["c"] > x["lsma"] else -1 for x in last2]
        sus = ("UP" if sides[0] > 0 else "DOWN") if (len(sides) == 2 and sides[0] == sides[1]) else "NEUTRAL"
        l4 = [x["lsma"] for x in seen[-4:] if x.get("lsma") is not None]
        slope = (l4[-1] - l4[0]) / (len(l4) - 1) if len(l4) >= 2 else None
        tsx = [str(x.get("tstate") or "").upper() for x in seen[-2:]]
        if sus != "UP" and len(tsx) == 2 and all(s == "BLUE" for s in tsx) and slope is not None and slope > 0:
            sus = "UP"
        elif sus != "DOWN" and len(tsx) == 2 and all(s == "RED" for s in tsx) and slope is not None and slope < 0:
            sus = "DOWN"
        s1x = s1.get(close_t.strftime("%H:%M")) or s1.get(hm) or {}
        out.append(dict(hint=hint, rp_hint=rp_hint, struct=struct, turn=tn.get("turn", "none"), lsma=lside, lsma_cvd=lcv,
                        sus=sus, daytype=s1x.get("published"), ot=s1x.get("ot_locked") or s1x.get("machine_opening")))
    return out


def lag_of(bs, series, start_i, want, upto=None):
    """First bar index ≥ start_i where series[k] == want (None if never before `upto`)."""
    upto = len(bs) if upto is None else upto
    for k in range(start_i, upto):
        if series[k] == want:
            return k
    return None


SUMMARY = {}
for day in days:
    bs = D[day]; th = xlib.theta_series(day); sw = xlib.zigzag_ext(bs, th)
    st, ev = xlib.dstate(bs, th, sw)
    R = xlib.day_refs(day)
    SR = sys_reads(day, bs)
    ibw = R["ib_hi"] - R["ib_lo"]; thr = max(15.0, 0.5 * ibw)
    tp = xlib.turning_points(bs, thr)
    reads = {"מצב-כיוון": st, "dir_hint": [to3(x["hint"]) for x in SR], "structure": [to3(x["struct"]) for x in SR],
             "turn": [to3(x["turn"]) for x in SR], "LSMA+CVD": [to3(x["lsma_cvd"]) for x in SR], "dir_sustained": [to3(x["sus"]) for x in SR]}
    print("=" * 110)
    print("%s · θ פתיחה %.2f · IB %.2f–%.2f (%.2f) · סף-תנועה-משמעותית %.2f" % (day, th[0], R["ib_lo"], R["ib_hi"], ibw, thr))
    print("אירועי מצב-הכיוון:")
    for e in ev:
        print("  %s  %s → %s  (סגירה %s) — %s" % (xlib.il_hm(bs[e["i"]]), xlib.HE[e["frm"]], xlib.HE[e["to"]], e["px"], e["why"]))
    # actual turning points and the lag of every read
    print("נקודות-מפנה בפועל (בדיעבד, סף %.2f) והפיגור של כל קריאה עד שהיא מסכימה עם הכיוון החדש:" % thr)
    legs = []
    for k in range(len(tp) - 1):
        a, b2 = tp[k], tp[k + 1]
        want = "UP" if a[0] == "L" else "DOWN"
        legs.append((a, b2, want))
    rows = []
    for a, b2, want in legs:
        i0 = a[2]; i1 = b2[2]
        line = "  %s %s@%s → %s@%s (%+.2f נק׳, %s):" % ("לונג" if want == "UP" else "שורט", a[1], xlib.il_hm(bs[i0]), b2[1], xlib.il_hm(bs[i1]),
                                                      b2[1] - a[1], "עולה" if want == "UP" else "יורד")
        parts = []
        for nm, ser in reads.items():
            k = lag_of(bs, ser, i0, want, i1 + 1)
            if k is None:
                parts.append("%s: לא עד סוף התנועה" % nm); rows.append((day, nm, None, None, abs(b2[1] - a[1])))
            else:
                done = abs(bs[k]["c"] - a[1]) / max(abs(b2[1] - a[1]), 0.25)
                parts.append("%s: %s (+%d דק׳, %.0f%% מהתנועה)" % (nm, xlib.il_hm(bs[k]), 5 * (k - i0) + 5, 100 * done))
                rows.append((day, nm, 5 * (k - i0) + 5, done, abs(b2[1] - a[1])))
        print(line); print("     " + " · ".join(parts))
    # agreement vs the state on the bars where the state is UP/DOWN (16:45–21:55)
    print("הסכמה של קריאות-המערכת עם מצב-הכיוון (ברים שבהם המצב עולה/יורד, 16:45–21:55):")
    for nm, ser in reads.items():
        if nm == "מצב-כיוון":
            continue
        n = agree = opp = 0
        for k, b in enumerate(bs):
            if not ("16:45" <= xlib.il_hm(b) <= "21:55") or st[k] == "BAL":
                continue
            n += 1
            if ser[k] == st[k]:
                agree += 1
            elif ser[k] in ("UP", "DOWN"):
                opp += 1
        print("  %-13s מסכימה %d/%d (%.0f%%) · הפוכה %d (%.0f%%)" % (nm, agree, n, 100.0 * agree / max(n, 1), opp, 100.0 * opp / max(n, 1)))
    # the state timeline in 30-min blocks (for the report)
    print("ציר-הזמן (כל בר: מצב · hint · struct · turn · LSMA+CVD · sustained · day type):")
    for k, b in enumerate(bs):
        x = SR[k]
        print("  %s c=%-8s %-5s | hint %-5s(rp %-5s) struct %-9s turn %-5s lsma %-3s lcv %-7s sus %-7s | %s %s" % (
            xlib.il_hm(b), b["c"], st[k], x["hint"], x["rp_hint"], x["struct"], x["turn"], x["lsma"], x["lsma_cvd"], x["sus"], x["daytype"], x["ot"]))
    json.dump(dict(day=day, ev=[dict(e, hm=xlib.il_hm(bs[e["i"]])) for e in ev], state=st, sys=SR, tp=tp, thr=thr,
                   swings=sw, theta=th, refs=R),
              open(os.path.join(xlib.HERE, "state_%s.json" % day), "w"), ensure_ascii=False, default=str)
    SUMMARY[day] = rows
json.dump(SUMMARY, open(os.path.join(xlib.HERE, "lags.json"), "w"), ensure_ascii=False, default=str)
