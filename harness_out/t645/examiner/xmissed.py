#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part D — every significant move (a hindsight swing ≥ max(15 pts, ½ IB)) of the examined sessions: when the direction
state confirmed it, which candidates the live system had in the move's direction while it was still young (from the
turning bar until 60% of the move was done), what blocked each (live shadow twin blocked_by; the tree path from the
backend log on 22–23.10), its bar label, and what the examiner's questions say. Read-only.

  python3 harness_out/t645/examiner/xmissed.py > harness_out/t645/examiner/missed.txt   (+ missed.json)
"""
import os, sys, json, datetime as dt
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner")
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
import xlib

DATA = xlib.data(); D = xlib.rth_days()
LOG = json.load(open(os.path.join(xlib.HERE, "log_tree.json")))


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


def log_path(day, ts, pat, d):
    if day not in ("2026-10-22", "2026-10-23"):
        return None
    best = None
    for lts, p, dd, e, leaf, path in LOG["tree"]:
        t = dt.datetime.fromisoformat(lts.replace(" ", "T") + "+03:00")
        if p == pat and dd == d and abs((t - ts).total_seconds()) <= 90:
            if best is None or abs((t - ts).total_seconds()) < best[0]:
                best = (abs((t - ts).total_seconds()), leaf, path)
    return (best[1] + " " + best[2]) if best else None


OUT = []
for day in DATA["days"]:
    bs, th, sw, st, ev = xlib.day_state(day)
    R = xlib.day_refs(day); ibw = R["ib_hi"] - R["ib_lo"]; thr = max(15.0, 0.5 * ibw)
    tp = xlib.turning_points(bs, thr)
    print("=" * 110)
    print("%s · סף %.2f · IB %.2f–%.2f" % (day, thr, R["ib_lo"], R["ib_hi"]))
    cands = [t for t in DATA["trades"] if t["day"] == day]
    for a, b in zip(tp, tp[1:]):
        want = "UP" if a[0] == "L" else "DOWN"; dirn = "LONG" if want == "UP" else "SHORT"
        size = abs(b[1] - a[1])
        if size < thr:
            continue
        i0, i1 = a[2], b[2]
        # the bar where 60% of the move is done
        i60 = next((k for k in range(i0, i1 + 1) if abs(bs[k]["c"] - a[1]) >= 0.6 * size), i1)
        conf = next((k for k in range(i0, i1 + 1) if st[k] == want), None)
        t0 = bs[i0]["t"] - dt.timedelta(minutes=5); t1 = bs[i60]["t"] + dt.timedelta(minutes=5)
        print("\n%s %s@%s → %s@%s (%+.2f) · מצב-כיוון אישר %s · 60%% מהתנועה ב-%s" % (
            "לונג" if want == "UP" else "שורט", a[1], xlib.il_hm(bs[i0]), b[1], xlib.il_hm(bs[i1]), b[1] - a[1],
            ("%s @%s" % (xlib.il_hm(bs[conf]), bs[conf]["c"])) if conf is not None else "לא אישר", xlib.il_hm(bs[i60])))
        rows = []; last = {}
        for t in sorted(cands, key=lambda t: t["entry_ts"]):
            ts = dt.datetime.fromisoformat(t["entry_ts"])
            if t["direction"] != dirn or not (t0 <= ts <= t1):
                continue
            key = (t["pattern_id_at_entry"], t["mode"])
            if key in last and (ts - last[key]).total_seconds() < 600 and t["mode"] == "shadow":
                continue
            last[key] = ts
            ep = fnum(t["entry_price"]); s0 = init_stop(t)
            lab, lt = xlib.label_candidate(bs, ts, t["direction"], ep, s0) if (ep and s0) else (None, None)
            f = xlib.features(day, ts, t["direction"], ep)
            q = xlib.ask(f)
            lp = log_path(day, ts, t["pattern_id_at_entry"], t["direction"])
            row = dict(day=day, leg="%s@%s→%s@%s" % (a[1], xlib.il_hm(bs[i0]), b[1], xlib.il_hm(bs[i1])), id=t["id"], mode=t["mode"],
                       hm=ts.astimezone(xlib.IL).strftime("%H:%M"), pat=t["pattern_id_at_entry"], dir=t["direction"], entry=ep, stop=s0,
                       R=abs(ep - s0) if (ep and s0) else None, blocked=t.get("blocked_by"), shadow=(t.get("outcome"), t.get("pnl_usd")),
                       label=lab, label_t=lt, state=f["state"] if f else None, pos=round(f["pos"], 2) if f else None,
                       q=q, log=lp)
            rows.append(row); OUT.append(row)
            print("   %s %-6s %-22s @%-8s R %-6s %-26s מצב %-4s pos %-5s → %-5s %-6s | שאלות: %-10s | shadow %s %s%s" % (
                row["hm"], t["mode"], row["pat"][:22], ep, ("%.2f" % row["R"]) if row["R"] else "-", (row["blocked"] or "—")[:26],
                row["state"], row["pos"], lab, lt or "", ",".join(q) or "עובר", row["shadow"][0], row["shadow"][1],
                ("\n        עץ(לוג): " + lp) if lp else ""))
        if not rows:
            print("   (אין מועמד של המערכת בכיוון התנועה בחלון)")
json.dump(OUT, open(os.path.join(xlib.HERE, "missed.json"), "w"), ensure_ascii=False, default=str, indent=1)
