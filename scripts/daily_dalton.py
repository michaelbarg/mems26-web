#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily_dalton.py — נתב-דלתון יומי · שלב 1 (CC_ORDER 2026-10-05 17:11).

קורא רק את `harness_out/t466/t529b_*.json` (65 סשנים, ריפליי קונפיג-הלייב, 1 חוזה).
אפס Postgres · אפס הרנס · אפס כתיבה מלבד הדוח (`docs/reports/DAILY_DALTON_<date>.md`).

מדפיס את טבלת-המנעולים של §0 בפורמט יציב, ויוצא בקוד 1 אם שורה חסרה או
מספר לא זהה (עיגול ל-1 ספרה לכל Σ של תא; Σ הכולל ל-2 ספרות).

הגדרות נעולות (סטייה מהן = המנעול נשבר = כישלון):
  • Σ = sum(trade.pnl_usd) של העסקאות שההרנס ביצע (תיק, לא Σ-מועמדים); "שלילי" = לא-חיובי (יום בלי עסקאות נספר שם).
  • פתיחת היום = הערך השכיח של tree_v3.vec.opening_type על routes,
    אחרי השלכת UNKNOWN ו-None.
  • מבנה היום = הערך השכיח של vec.structure על routes ש-vec.phase שלהם C/D;
    אין כאלה ⇒ `no_CD`.
  • שיוך עסקה ל-route: אותו classification, אותו direction, |entry| < 0.01;
    משם phase / kind / hour.
  • דלי-שעה: hour<=16 → "16" · ==17 → "17" · <=19 → "18-19" · אחרת "20+".

שימוש:  python3 scripts/daily_dalton.py [--no-report] [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import sys
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_GLOB = os.path.join(ROOT, "harness_out", "t466", "t529b_*.json")
REPORT_DIR = os.path.join(ROOT, "docs", "reports")

# ── §0 · המנעולים (נמדדו 05.10 17:10 על 65 קבצי t529b) ───────────────────────
LOCK_TOTAL = {"sessions": 65, "pnl": "2502.40", "pos": 35, "neg": 30}
LOCK_OPENING = OrderedDict([
    ("OPEN_REJECTION_REVERSE", {"days": 14, "pnl": "990.0", "pos": 10}),
    ("OPEN_AUCTION_IN", {"days": 41, "pnl": "790.6", "pos": 19}),
    ("OPEN_DRIVE", {"days": 10, "pnl": "721.9", "pos": 6}),
])
LOCK_STRUCTURE = OrderedDict([
    ("up", {"days": 22, "pnl": "1285.0", "pos": 12}),
    ("down", {"days": 28, "pnl": "833.8", "pos": 15}),
    ("two_sided", {"days": 5, "pnl": "206.2", "pos": 3}),
    ("none", {"days": 10, "pnl": "177.5", "pos": 5}),
])
LOCK_PHASE = OrderedDict([
    ("B", {"n": 60, "pnl": "1126.8"}),
    ("C", {"n": 110, "pnl": "1216.8"}),
    ("D", {"n": 21, "pnl": "182.5"}),
    ("A", {"n": 1, "pnl": "-23.8"}),
])
LOCK_KIND = OrderedDict([
    ("BREAK", {"n": 80, "pnl": "1200.0"}),
    ("WITH_DRIVE", {"n": 28, "pnl": "791.2"}),
    ("REVERSAL", {"n": 59, "pnl": "404.9"}),
    ("PULLBACK", {"n": 3, "pnl": "107.5"}),
    ("EDGE_FADE", {"n": 22, "pnl": "-1.2"}),
])
LOCK_HOUR = OrderedDict([
    ("16", {"n": 44, "pnl": "686.8"}),
    ("17", {"n": 28, "pnl": "326.2"}),
    ("18-19", {"n": 73, "pnl": "1211.9"}),
    ("20+", {"n": 47, "pnl": "277.5"}),
])


# ── helpers ────────────────────────────────────────────────────────────────────
def D(x) -> float:
    """The lock arithmetic is float + Python round() (05.10 17:10 measurement):
    e.g. phase C = 1216.85 -> 1216.8, EDGE_FADE = -1.25 -> -1.2. Exact-decimal
    HALF_UP would print 1216.9 / -1.3 and break four locks - so floats, on purpose."""
    return float(x if x is not None else 0.0)


def fmt(d: float, places: int = 1) -> str:
    return "%.*f" % (places, round(d, places))


def mode(values):
    """Most common value; ties → the value seen first (deterministic)."""
    if not values:
        return None
    c = Counter(values)
    first = {}
    for i, v in enumerate(values):
        first.setdefault(v, i)
    return max(c, key=lambda k: (c[k], -first[k]))


def vec_of(route):
    t = route.get("tree_v3") or {}
    return t.get("vec") or {}


def hour_bucket(h):
    if h is None:
        return "unmatched"
    try:
        h = int(h)
    except (TypeError, ValueError):
        return "unmatched"
    if h <= 16:
        return "16"
    if h == 17:
        return "17"
    if h <= 19:
        return "18-19"
    return "20+"


def load_sessions(pattern: str = HARNESS_GLOB):
    out = []
    for f in sorted(glob.glob(pattern)):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        sess = d.get("session") or os.path.basename(f)[len("t529b_"):-len(".json")]
        out.append({"file": f, "session": str(sess)[:10],
                    "routes": d.get("routes") or [], "trades": d.get("trades") or []})
    return out


def day_opening(routes):
    vals = [vec_of(r).get("opening_type") for r in routes]
    vals = [v for v in vals if v not in (None, "", "UNKNOWN")]
    return mode(vals) or "UNKNOWN"


def day_structure(routes):
    vals = [vec_of(r).get("structure") for r in routes if vec_of(r).get("phase") in ("C", "D")]
    if not vals:
        return "no_CD"
    return mode([v if v not in (None, "") else "none" for v in vals])


def match_route(trade, routes):
    cls, dr, entry = trade.get("classification"), trade.get("direction"), trade.get("entry")
    for r in routes:
        if r.get("classification") == cls and r.get("direction") == dr:
            try:
                if abs(float(r.get("entry")) - float(entry)) < 0.01:
                    return r
            except (TypeError, ValueError):
                continue
    return None


def compute(sessions):
    """Aggregate the locks. Pure: no I/O. Returns a dict of OrderedDicts."""
    total = 0.0; pos = neg = 0
    by_open, by_struct = {}, {}
    by_phase, by_kind, by_hour = {}, {}, {}
    days = []
    for s in sessions:
        routes, trades = s["routes"], s["trades"]
        dpnl = sum(D(t.get("pnl_usd")) for t in trades)
        total += dpnl
        if dpnl > 0: pos += 1
        else: neg += 1  # lock: "negative" = not positive (a 0-trade day counts here; 35+30=65)
        op, st = day_opening(routes), day_structure(routes)
        for key, book in ((op, by_open), (st, by_struct)):
            b = book.setdefault(key, {"days": 0, "pnl": 0.0, "pos": 0})
            b["days"] += 1; b["pnl"] += dpnl; b["pos"] += 1 if dpnl > 0 else 0
        for t in trades:
            r = match_route(t, routes)
            v = vec_of(r) if r else {}
            pnl = D(t.get("pnl_usd"))
            for key, book in ((v.get("phase") or "unmatched", by_phase),
                              (v.get("kind") or "unmatched", by_kind),
                              (hour_bucket(v.get("hour")) if r else "unmatched", by_hour)):
                b = book.setdefault(key, {"n": 0, "pnl": 0.0})
                b["n"] += 1; b["pnl"] += pnl
        days.append({"date": s["session"], "pnl": dpnl, "n_trades": len(trades),
                     "opening": op, "structure": st})
    return {"sessions": len(sessions), "pnl": total, "pos": pos, "neg": neg,
            "opening": by_open, "structure": by_struct, "phase": by_phase,
            "kind": by_kind, "hour": by_hour, "days": days}


def check_locks(res):
    """Return the list of broken locks ([] = all green). A cent is a failure."""
    bad = []
    if res["sessions"] != LOCK_TOTAL["sessions"]: bad.append("sessions %d != %d" % (res["sessions"], LOCK_TOTAL["sessions"]))
    if fmt(res["pnl"], 2) != LOCK_TOTAL["pnl"]: bad.append("pnl %s != %s" % (fmt(res["pnl"], 2), LOCK_TOTAL["pnl"]))
    if res["pos"] != LOCK_TOTAL["pos"]: bad.append("pos %d != %d" % (res["pos"], LOCK_TOTAL["pos"]))
    if res["neg"] != LOCK_TOTAL["neg"]: bad.append("neg %d != %d" % (res["neg"], LOCK_TOTAL["neg"]))
    for name, lock, book in (("opening", LOCK_OPENING, res["opening"]), ("structure", LOCK_STRUCTURE, res["structure"])):
        for key, want in lock.items():
            got = book.get(key)
            if not got:
                bad.append("%s %s missing" % (name, key)); continue
            if got["days"] != want["days"] or fmt(got["pnl"]) != want["pnl"] or got["pos"] != want["pos"]:
                bad.append("%s %s days=%d pnl=%s pos=%d != days=%d pnl=%s pos=%d" % (
                    name, key, got["days"], fmt(got["pnl"]), got["pos"], want["days"], want["pnl"], want["pos"]))
    for name, lock, book in (("phase", LOCK_PHASE, res["phase"]), ("kind", LOCK_KIND, res["kind"]), ("hour", LOCK_HOUR, res["hour"])):
        for key, want in lock.items():
            got = book.get(key)
            if not got:
                bad.append("%s %s missing" % (name, key)); continue
            if got["n"] != want["n"] or fmt(got["pnl"]) != want["pnl"]:
                bad.append("%s %s n=%d pnl=%s != n=%d pnl=%s" % (name, key, got["n"], fmt(got["pnl"]), want["n"], want["pnl"]))
    return bad


def render(res, bad):
    """The stable stdout. First four lines are the ones §3 names verbatim."""
    L = ["sessions=%d pnl=%s pos=%d neg=%d" % (res["sessions"], fmt(res["pnl"], 2), res["pos"], res["neg"])]
    for key in LOCK_OPENING:
        b = res["opening"].get(key, {"days": 0, "pnl": 0.0, "pos": 0})
        L.append("%s days=%d pnl=%s pos=%d" % (key, b["days"], fmt(b["pnl"]), b["pos"]))
    for key in LOCK_STRUCTURE:
        b = res["structure"].get(key, {"days": 0, "pnl": 0.0, "pos": 0})
        L.append("structure %s days=%d pnl=%s pos=%d" % (key, b["days"], fmt(b["pnl"]), b["pos"]))
    for name, lock in (("phase", LOCK_PHASE), ("kind", LOCK_KIND), ("hour", LOCK_HOUR)):
        for key in lock:
            b = res[name].get(key, {"n": 0, "pnl": 0.0})
            L.append("%s %s n=%d pnl=%s" % (name, key, b["n"], fmt(b["pnl"])))
    extra = [(n, k, b) for n in ("opening", "structure", "phase", "kind", "hour")
             for k, b in res[n].items() if k not in {"opening": LOCK_OPENING, "structure": LOCK_STRUCTURE,
                                                     "phase": LOCK_PHASE, "kind": LOCK_KIND, "hour": LOCK_HOUR}[n]]
    for n, k, b in extra:  # anything outside the lock table is printed, never hidden
        L.append("%s %s (unlocked) %s pnl=%s" % (n, k, "days=%d pos=%d" % (b["days"], b["pos"]) if "days" in b else "n=%d" % b["n"], fmt(b["pnl"])))
    L.append("--- days (date pnl n_trades opening structure) ---")
    for d in res["days"]:
        L.append("%s %s %d %s %s" % (d["date"], fmt(d["pnl"], 2), d["n_trades"], d["opening"], d["structure"]))
    L.append("LOCKS: %s" % ("OK (all %d rows identical)" % (4 + len(LOCK_OPENING) + len(LOCK_STRUCTURE) + len(LOCK_PHASE) + len(LOCK_KIND) + len(LOCK_HOUR)) if not bad else "FAIL — " + " | ".join(bad)))
    return "\n".join(L)


def write_report(stdout: str, date: str, cmd: str) -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, "DAILY_DALTON_%s.md" % date)
    body = ("# נתב-דלתון יומי · שלב 1 · %s\n\n"
            "CC_ORDER 2026-10-05 17:11 — המנעולים של §0 על `harness_out/t466/t529b_*.json` (קריאה-בלבד; אפס Postgres, אפס הרנס).\n\n"
            "```\n$ %s\n%s\n```\n" % (date, cmd, stdout))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-report", action="store_true", help="print only; do not write docs/reports/DAILY_DALTON_<date>.md")
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="report date (default: today)")
    ap.add_argument("--glob", default=HARNESS_GLOB, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    sessions = load_sessions(a.glob)
    res = compute(sessions)
    bad = check_locks(res)
    out = render(res, bad)
    print(out)
    if not a.no_report:
        p = write_report(out, a.date, "python3 scripts/daily_dalton.py")
        print("report: %s" % os.path.relpath(p, ROOT))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
