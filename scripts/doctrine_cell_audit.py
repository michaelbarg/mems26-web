#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""doctrine_cell_audit.py — the doctrine table, cell by cell (Michael 08.10: "עליך להתאים את האופן שהמערכת סוחרת בכל
יום ובכל שלב של היום לאפשר כניסה בנקודות בהתאם לדוקטרינה שמאפיינת כל יום").

For every cell = (phase, day type AT DECISION TIME) over the live-config replay (harness tag, 67 sessions):
  what the doctrine says the entries are · what the tree TAKEs / SKIPs there (observed on the candidates) ·
  what FIRED (replay trades: n, win%, Σ) · what the tree TAKEs but a later gate / the slot / a shadow-only producer
  stopped (n, Σ on the bars) · what the tree SKIPs and what those candidates were worth on the bars.
Bar value = the fixed model of context_table.py (own stop, 1.5R, first touch on closed 5-min bars, EOD close,
$5/pt, −2.60). Representative pool = live-capable producers, post-gate (blocked_by empty or tree:*), 30-min dedup
per (pattern, direction) — the filter T-543 stage 5 settled on. Read-only. Prints markdown.
usage: python3 scripts/doctrine_cell_audit.py [--tag t564ref] [--nmin 8] [--holdout 10]
"""
import collections, glob, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
ARG = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d  # noqa
TAG = ARG("--tag", "t564ref"); NMIN = int(ARG("--nmin", "8")); HOLD = int(ARG("--holdout", "10"))
COMM = 2.60; PT = 5.0; RR = 1.5

DOCTRINE = {  # Dalton / dalton_playbook.yaml (09.09) + rulings — what each cell is supposed to trade
    ("A", "*"): "פתיחה (16:30–16:45): לפי סוג-הפתיחה בלבד — דרייב: עם הדרייב; ORR: היפוך הדרייב; auction-in: המתנה. בלי סוג-יום עדיין.",
    ("B", "*"): "לפני נעילת-IB (16:45–17:30): דרייב/טסט-דרייב עם הכיוון; היפוך בקיצון-הפתיחה (ORR, EXTREME_REJECT); דהיית-קצה רק ב-auction-in.",
    ("C", "Trend_Normal"): "יום-מגמה: רק עם המגמה — פולבק/המשך/פריצה בכיוון; אפס דהייה; יעד מתגלגל.",
    ("C", "Trend_DD"): "התפלגות-כפולה: עם הכיוון אחרי קבלת ההתפלגות השנייה; אין דהייה לצוואר.",
    ("C", "Variation"): "Normal-Variation: עם ההרחבה שהתקבלה (BREAK/PULLBACK); נגד ההרחבה רק בקצה-הרחבה-כושלת (T-329); דהיית-ערך בחזרה-ל-IB.",
    ("C", "Normal"): "יום-Normal (IB רחב): רספונסיבי — דהיית הקצוות (VAH/VAL, קצה-IB), אין פריצות; יעד POC/ערך.",
    ("C", "Neutral_Center"): "ניטרלי-מרכז: דהיית שני הקצוות בחזרה לערך; אין כיוון.",
    ("C", "Neutral_Extreme"): "ניטרלי-קיצון: מאוחר ביום עם הצד המנצח (הקיצון שנשאר); לפני כן — רספונסיבי.",
    ("C", "Nontrend"): "ללא-מגמה / Nonconviction: לא סוחרים.",
    ("D", "*"): "שלב D (21:00+): רק עם ההרחבה החד-צדדית של היום (T-494, S1); אחרי 22:00 אין כניסות (T-538).",
}


def q(sql):
    out = subprocess.run('%s -d mems26 -Atc "%s"' % (PSQL, sql.replace('"', '\\"')), shell=True, capture_output=True, text=True, timeout=180).stdout
    return [r.split("|") for r in out.splitlines() if r]


def fl(x):
    try:
        return float(x)
    except Exception:
        return None


bars = collections.defaultdict(list)
for r in q("select to_char(ts at time zone 'Asia/Jerusalem','YYYY-MM-DD'), to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), high, low, close "
           "from v9_bars_5min_woodies where symbol='MES' and ts>='2026-06-01' and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts"):
    if len(r) == 5:
        bars[r[0]].append((r[1], fl(r[2]), fl(r[3]), fl(r[4])))


def score(day, t_il, direction, entry, stop):
    risk = abs(entry - stop); tgt = entry + RR * risk if direction == "LONG" else entry - RR * risk
    seq = [b for b in bars.get(day, []) if b[0] > t_il]
    if not seq:
        return None
    for _, h, l, c in seq:
        if direction == "LONG":
            if l <= stop: return (stop - entry) * PT - COMM
            if h >= tgt: return (tgt - entry) * PT - COMM
        else:
            if h >= stop: return (entry - stop) * PT - COMM
            if l <= tgt: return (entry - tgt) * PT - COMM
    c = seq[-1][3]
    return ((c - entry) if direction == "LONG" else (entry - c)) * PT - COMM


def tmin(t):
    return int(t[:2]) * 60 + int(t[3:5])


files = sorted(glob.glob("harness_out/t466/%s_2026-*.json" % TAG))
days = [os.path.basename(p)[len(TAG) + 1:len(TAG) + 11] for p in files]
hold_days = set(days[-HOLD:])
cands = []
for p, d in zip(files, days):
    j = json.load(open(p))
    trades = {}
    for t in j.get("trades") or []:
        trades[(t.get("fired_il", "")[:5], t.get("classification"), t.get("direction"))] = t
    last = {}  # (pattern, dir) -> last kept minute, for the 30-min dedup
    for r in j.get("routes") or []:
        tv = r.get("tree_v3")
        if not isinstance(tv, dict):
            continue
        v = tv.get("vec") or {}
        ep = fl(r.get("entry")); stp = fl(r.get("stop")); direction = r.get("direction")
        if not (ep and stp and 1.0 <= abs(ep - stp) <= 30):
            continue
        t_il = (r.get("il") or "00:00:00")[:5]
        blocked = r.get("blocked_by") or ""
        res = r.get("result") or {}
        fired_tr = trades.get((t_il, r.get("classification"), direction))
        fired = bool(res.get("live") or res.get("demo")) and fired_tr is not None
        if not fired:
            if r.get("shadow_only"):
                continue                                   # never fires live — not a doctrine question
            if blocked and not blocked.startswith("tree:"):
                gate = blocked                              # post-tree gate — kept, counted separately
            else:
                gate = ""
            k = (r.get("classification"), direction)
            if k in last and tmin(t_il) - last[k] < 30:
                continue                                   # same thesis re-fired within 30 min
            last[k] = tmin(t_il)
        else:
            gate = ""
        sc = score(d, t_il, direction, ep, stp)
        if sc is None:
            continue
        kind = v.get("kind") or "?"
        cands.append({"day": d, "hold": d in hold_days, "il": t_il, "phase": v.get("phase") or "?", "dt": v.get("day_type") or "?",
                      "pattern": r.get("classification") or "?", "kind": kind, "dir": direction, "rel": v.get("rel_bias") or "?",
                      "leaf": str(tv.get("leaf") or "SKIP").upper(), "tree_block": blocked if blocked.startswith("tree:") else "",
                      "gate": gate, "slot": (r.get("live_blocked_by") == "live_slot_occupied"), "fired": fired,
                      "pnl": (float(fired_tr.get("pnl_usd") or 0) if fired else None), "score": sc})


def st(rows, key="score"):
    s = [c[key] for c in rows if c.get(key) is not None]
    n = len(s); w = (sum(1 for x in s if x > 0) / n * 100) if n else 0.0
    return n, w, sum(s)


def fmt(rows, key="score"):
    n, w, s = st(rows, key)
    return "n=%d · win %.0f%% · Σ%+.0f$" % (n, w, s) if n else "—"


def doctrine(phase, dt):
    return DOCTRINE.get((phase, dt)) or DOCTRINE.get((phase, "*")) or "—"


PHASE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
cells = collections.defaultdict(list)
for c in cands:
    cells[(c["phase"], c["dt"])].append(c)
print("# טבלת-הדוקטרינה תא-תא · %s · %d סשנים (%s..%s) · %d מועמדים (מסונן: live-capable, אחרי-שער, dedup 30 דק׳) · החזקה = %d האחרונים" % (
    TAG, len(days), days[0], days[-1], len(cands), HOLD))
print()
for (phase, dt), rows in sorted(cells.items(), key=lambda kv: (PHASE_ORDER.get(kv[0][0], 9), -len(kv[1]))):
    ndays = len(set(c["day"] for c in rows))
    fired = [c for c in rows if c["fired"]]
    take_not = [c for c in rows if c["leaf"] == "TAKE" and not c["fired"] and not c["tree_block"]]
    skip = [c for c in rows if c["tree_block"] or (c["leaf"] != "TAKE" and not c["fired"])]
    print("## %s · %s — %d מועמדים על %d ימים" % (phase, dt, len(rows), ndays))
    print("**דוקטרינה:** " + doctrine(phase, dt))
    print("- **ירה (ריפליי):** %s · החזקה: %s" % (fmt(fired, "pnl"), fmt([c for c in fired if c["hold"]], "pnl")))
    if fired:
        by = collections.defaultdict(list)
        for c in fired: by[(c["pattern"], c["rel"])].append(c)
        top = sorted(by.items(), key=lambda kv: -abs(st(kv[1], "pnl")[2]))[:6]
        print("  - לפי תבנית·הטיה: " + " · ".join("%s/%s %s" % (k[0], k[1], fmt(v, "pnl")) for k, v in top))
    if take_not:
        byg = collections.defaultdict(list)
        for c in take_not: byg["slot" if c["slot"] else (c["gate"] or "shadow-result")].append(c)
        print("- **העץ אמר TAKE ולא ירה (שווי על הברים):** " + " · ".join("%s %s" % (g, fmt(v)) for g, v in sorted(byg.items(), key=lambda kv: -len(kv[1]))))
    if skip:
        print("- **העץ אמר SKIP (שווי על הברים):** %s · החזקה: %s" % (fmt(skip), fmt([c for c in skip if c["hold"]])))
        byr = collections.defaultdict(list)
        for c in skip: byr[c["tree_block"] or "skip-leaf"].append(c)
        print("  - לפי סיבה: " + " · ".join("%s %s" % (k, fmt(v)) for k, v in sorted(byr.items(), key=lambda kv: -len(kv[1]))))
        byk = collections.defaultdict(list)
        for c in skip: byk[(c["pattern"], c["dir"], c["rel"])].append(c)
        best = [(k, v) for k, v in byk.items() if len(v) >= NMIN]
        best.sort(key=lambda kv: -st(kv[1])[2])
        if best:
            print("  - SKIP שהשאיר הכי הרבה (n≥%d): " % NMIN + " · ".join("%s/%s/%s %s [החזקה %s]" % (k[0], k[1], k[2], fmt(v), fmt([c for c in v if c["hold"]])) for k, v in best[:4]))
            worst = sorted(best, key=lambda kv: st(kv[1])[2])[:2]
            print("  - SKIP שצדק הכי הרבה (n≥%d): " % NMIN + " · ".join("%s/%s/%s %s" % (k[0], k[1], k[2], fmt(v)) for k, v in worst))
    # fired contexts that lose with N
    if fired:
        byf = collections.defaultdict(list)
        for c in fired: byf[(c["pattern"], c["dir"], c["rel"])].append(c)
        losers = [(k, v) for k, v in byf.items() if len(v) >= NMIN and st(v, "pnl")[2] < 0]
        losers.sort(key=lambda kv: st(kv[1], "pnl")[2])
        if losers:
            print("  - **TAKE שמפסיד עם N (n≥%d):** " % NMIN + " · ".join("%s/%s/%s %s" % (k[0], k[1], k[2], fmt(v, "pnl")) for k, v in losers[:4]))
    print()
tot_f = [c for c in cands if c["fired"]]
print("## סיכום: ירה %s · TAKE-לא-ירה %s · SKIP %s" % (fmt(tot_f, "pnl"), fmt([c for c in cands if c["leaf"] == "TAKE" and not c["fired"] and not c["tree_block"]]), fmt([c for c in cands if c["tree_block"] or (c["leaf"] != "TAKE" and not c["fired"])])))
