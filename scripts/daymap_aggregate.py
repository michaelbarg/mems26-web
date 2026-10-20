#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daymap_aggregate.py — DAYMAP («פירוק-יום») aggregate over every day file of a version.

Reads <dir>/<D>.json (written by scripts/day_dissect.py) → <dir>/SUMMARY.json + <dir>/SUMMARY.md (Hebrew):
  * opening / day-type hit rates — vs the rule-based reference and vs Michael's labels where present, live and replay
    separately (partial sessions and live days without system data are excluded);
  * time-to-correct-label distribution (minutes after the 09:30 ET open until the S1 label's family first equals the truth);
  * the cell table  day_type(truth) × phase × family : fires, win%, Σ pts, Σ$ (live), would-fire Σ pts, missed legs Σ pts
    (a missed leg is attributed to the family of the first candidate that was BLOCKED in its direction inside the leg's
    first half; '—' = no candidate saw it);
  * the what-if table per (thesis → new label): N and Σ pts of EXIT / BE / HOLD;
  * the top-6 branch candidates (largest negative Σ pts cells and largest missed Σ pts cells), phrased
    «ביום X בשלב Y: לחסום / לאפשר / לשנות Z», with N, Σ and a small-N flag (N < 8).
Read-only except the two SUMMARY files.

  python3 scripts/daymap_aggregate.py [--version base-20.10] [--dir harness_out/daymap/base-20.10] [--since YYYY-MM-DD]
"""
import os, sys, json, glob, argparse, statistics, collections, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import daymap_lib as L  # noqa: E402

SMALL_N = 8
MD_MAX_ROWS = 80
PH_ORDER = {p: i for i, p in enumerate(L.PHASES)}
DT_ORDER = {"Trend": 0, "Variation": 1, "Normal": 2, "Neutral": 3, "Nontrend": 4, "?": 9}
FAM_HEB_DT = {"Trend": "מגמה", "Variation": "וריאציה", "Normal": "נורמלי", "Neutral": "ניטרלי", "Nontrend": "ללא-מגמה", "?": "לא-ידוע"}
PH_HEB = {"0": "0 (לילה)", "A": "A (פתיחה)", "B": "B (IB)", "C": "C (התפתחות)", "D": "D (ניהול)"}


def load_days(d, since=None, until=None):
    out = []
    for p in sorted(glob.glob(os.path.join(d, "20??-??-??.json"))):
        day = os.path.basename(p)[:10]
        if (since and day < since) or (until and day > until):
            continue
        try:
            with open(p, encoding="utf-8") as fh:
                out.append(json.load(fh))
        except Exception as e:
            print("skip %s: %s" % (p, e))
    return out


def rate(ok, n):
    return round(100.0 * ok / n, 1) if n else None


def tally(pairs):
    """pairs = [(sys_label, truth_label, same_fn)] → {n, ok, rate}"""
    n = ok = 0
    for s, t, same in pairs:
        if s is None or t is None:
            continue
        n += 1; ok += bool(same(s, t))
    return dict(n=n, ok=ok, rate=rate(ok, n))


def pctl(xs, q):
    if not xs:
        return None
    xs = sorted(xs); k = (len(xs) - 1) * q; f = int(k); c = min(f + 1, len(xs) - 1)
    return round(xs[f] + (xs[c] - xs[f]) * (k - f), 1)


def known_ot(x):
    x = L.norm_ot(x)
    return None if x in ("UNKNOWN", "UNCLEAR") else x


def known_fam(x):
    return None if x in (None, "UNCLEAR") else L.dt_family(x)


def hits(days, view):
    vs_ref_o, vs_ref_d, vs_ref_x, vs_m_o, vs_m_d, ttc, never, stable = [], [], [], [], [], [], 0, []
    for R in days:
        V = R.get(view)
        if not V or not V.get("available") or R["truth"].get("partial"):
            continue
        h, tr = V["hit"], R["truth"]
        so, sd = known_ot(h.get("sys_opening")), known_fam(h.get("sys_day_type"))
        vs_ref_o.append((so, known_ot(tr.get("ref_opening")), lambda a, b: a == b))
        vs_ref_d.append((sd, known_fam(tr.get("ref_day_type")), lambda a, b: a == b))
        vs_ref_x.append((L.norm_dt(h.get("sys_day_type")) if sd else None, (L.norm_dt(tr.get("ref_day_type")) if known_fam(tr.get("ref_day_type")) else None), lambda a, b: a == b))
        if tr.get("opening_src") == "michael":
            vs_m_o.append((so, known_ot(tr.get("opening")), lambda a, b: a == b))
        if tr.get("day_type_src") == "michael":
            vs_m_d.append((sd, known_fam(tr.get("day_type")), lambda a, b: a == b))
        if known_fam(tr.get("day_type")) and V["system"].get("timeline"):
            if h.get("first_ok_min") is not None:
                ttc.append(h["first_ok_min"])
            else:
                never += 1
            if h.get("stable_ok_min") is not None:
                stable.append(h["stable_ok_min"])
    bins = collections.OrderedDict((k, 0) for k in ("≤30", "30–60", "60–120", "120–240", ">240", "never"))
    for m in ttc:
        bins["≤30" if m <= 30 else "30–60" if m <= 60 else "60–120" if m <= 120 else "120–240" if m <= 240 else ">240"] += 1
    bins["never"] = never
    return dict(vs_ref=dict(opening=tally(vs_ref_o), day_type=tally(vs_ref_d), day_type_exact=tally(vs_ref_x)),
                vs_michael=dict(opening=tally(vs_m_o), day_type=tally(vs_m_d)),
                ttc=dict(n=len(ttc), never=never, median=pctl(ttc, 0.5), p25=pctl(ttc, 0.25), p75=pctl(ttc, 0.75), bins=bins,
                         stable_median=pctl(stable, 0.5), stable_n=len(stable)))


def cells(days, view):
    C = collections.defaultdict(lambda: dict(fires=0, priced=0, wins=0, pts=0.0, usd=0.0, usd_n=0, would_n=0, would_pts=0.0,
                                             missed_n=0, missed_pts=0.0, days=set(), gates=collections.Counter()))
    for R in days:
        V = R.get(view)
        if not V or not V.get("available"):
            continue
        tdt = known_fam(R["truth"].get("day_type")) if not R["truth"].get("partial") else None
        tdt = tdt or "?"
        for t in V["trades"]:
            c = C[(tdt, t["phase"], t["fam"])]
            c["fires"] += 1; c["days"].add(R["date"])
            if t.get("pts") is not None:
                c["priced"] += 1; c["pts"] += t["pts"]; c["wins"] += t["pts"] > 0
            if t.get("usd") is not None:
                c["usd"] += t["usd"]; c["usd_n"] += 1
        for w in V["would"]:
            c = C[(tdt, w["phase"], w["fam"])]
            c["would_n"] += 1; c["would_pts"] += (w.get("pts") or 0.0); c["days"].add(R["date"])
        for lg in V["legs"]:
            if not lg["missed"]:
                continue
            fam = lg["blocked"][0]["fam"] if lg.get("blocked") else "—"
            c = C[(tdt, lg["phase"], fam)]
            c["missed_n"] += 1; c["missed_pts"] += lg["pts"]; c["days"].add(R["date"])
            if lg.get("blocked"):
                c["gates"][lg["blocked"][0]["gate"]] += 1
    out = []
    for (tdt, ph, fam), c in C.items():
        out.append(dict(view=view, dt=tdt, ph=ph, fam=fam, fires=c["fires"], priced=c["priced"], wins=c["wins"], win_pct=rate(c["wins"], c["priced"]),
                        pts=round(c["pts"], 2), usd=(round(c["usd"], 2) if (view == "live" and c["usd_n"]) else None),
                        would_n=c["would_n"], would_pts=round(c["would_pts"], 2), missed_n=c["missed_n"], missed_pts=round(c["missed_pts"], 2),
                        n_days=len(c["days"]), top_gate=(c["gates"].most_common(1)[0][0] if c["gates"] else None)))
    out.sort(key=lambda x: (DT_ORDER.get(x["dt"], 8), PH_ORDER.get(x["ph"], 9), -abs(x["pts"]) - x["missed_pts"]))
    return out


def what_ifs(days, view):
    G = collections.defaultdict(lambda: dict(n=0, exit=0.0, be=0.0, hold=0.0, best=collections.Counter(), ids=[]))
    for R in days:
        V = R.get(view)
        if not V:
            continue
        for t in V["trades"]:
            w = t.get("what_if")
            if not w:
                continue
            g = G[(view, w["kind"], w["frm"], w["to"])]
            g["n"] += 1; g["exit"] += w["exit"]; g["be"] += w["be"]; g["hold"] += w["hold"]; g["best"][w["best"]] += 1
            g["ids"].append("%s#%s" % (R["date"], t["id"]))
    out = []
    for (v, kind, frm, to), g in G.items():
        alts = dict(EXIT=g["exit"], BE=g["be"], HOLD=g["hold"])
        out.append(dict(view=v, kind=kind, frm=frm, to=to, n=g["n"], exit=round(g["exit"], 2), be=round(g["be"], 2), hold=round(g["hold"], 2),
                        best=max(alts, key=lambda k: (alts[k], k == "HOLD")), best_counts=dict(g["best"]), small_n=g["n"] < SMALL_N, ids=g["ids"][:12]))
    out.sort(key=lambda x: -x["n"])
    return out


def phrase(c, kind):
    day = FAM_HEB_DT.get(c["dt"], c["dt"]); ph = c["ph"]
    if kind == "block":
        return "ביום %s בשלב %s: לחסום %s" % (day, ph, c["fam"])
    if c["fam"] == "—":
        return "ביום %s בשלב %s: לשנות — אין מועמד שזיהה את הרגל (גלאי/ענף חסר)" % (day, ph)
    return "ביום %s בשלב %s: לאפשר %s%s" % (day, ph, c["fam"], (" (נחסם ע״י %s)" % c["top_gate"]) if c.get("top_gate") else "")


def branches(cl, k=6):
    """Top-k: the 3 most negative Σ-pts cells (fires) + the 3 largest missed-Σ cells, filled from either list."""
    neg = sorted([c for c in cl if c["fires"] and c["pts"] < 0], key=lambda c: c["pts"])
    mis = sorted([c for c in cl if c["missed_pts"] > 0], key=lambda c: -c["missed_pts"])
    pick = [("block", c) for c in neg[:k // 2]] + [("allow", c) for c in mis[:k // 2]]
    rest = [("block", c) for c in neg[k // 2:]] + [("allow", c) for c in mis[k // 2:]]
    rest.sort(key=lambda kc: -(abs(kc[1]["pts"]) if kc[0] == "block" else kc[1]["missed_pts"]))
    pick += rest[:max(0, k - len(pick))]
    out = []
    for kind, c in pick:
        n = c["fires"] if kind == "block" else c["missed_n"]
        pts = c["pts"] if kind == "block" else c["missed_pts"]
        out.append(dict(kind=kind, view=c["view"], dt=c["dt"], ph=c["ph"], fam=c["fam"], n=n, pts=round(pts, 2), small_n=n < SMALL_N,
                        n_days=c["n_days"], text=phrase(c, kind), usd=c.get("usd"), win_pct=c.get("win_pct"), gate=c.get("top_gate")))
    out.sort(key=lambda b: -abs(b["pts"]))
    for i, b in enumerate(out, 1):
        b["rank"] = i
    return out


def f2(x, sign=True):
    if x is None:
        return "—"
    return ("%+.1f" % x) if sign else ("%.1f" % x)


def fr(t):
    return "—" if not t or not t.get("n") else "%d/%d (%.0f%%)" % (t["ok"], t["n"], t["rate"])


def write_md(S, path):
    L_ = []
    a = L_.append
    a("# DAYMAP — פירוק-יום · %s — סיכום" % S["v_heb"])
    a("")
    a("נוצר %s · %d קובצי-יום (לייב/דמו %d · ריפליי %d · חלקיים %d · לייב בלי נתוני-מערכת %d). נקודות = לחוזה אחד; "
      "סימולציה = עצירה-קודם כשבר נוגע בשניהם, יציאת-EOD ב-15:50 ET." % (S["generated"], S["n_files"], S["n_live"], S["n_replay"], S["n_partial"], S["n_live_nodata"]))
    a("")
    a("| מבט | ימים | ירי | Σ נק׳ | Σ$ | היה-יורה | Σ היה-יורה | רגליים שפוספסו | Σ פספוס | רגליים בלי מערכת-רצה |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for v, t in (S.get("totals") or {}).items():
        a("| %s | %d | %d | %s | %s | %d | %s | %d | %.0f | %d (%.0f נק׳) |" % ("לייב/דמו" if v == "live" else "ריפליי", t["days"], t["fired"], f2(t["pts"]),
                                                                       f2(t["usd"]) if t.get("usd") is not None else "—", t["would"], f2(t["would_pts"]), t["missed"],
                                                                       t["missed_pts"], t["uncovered"], t["uncovered_pts"]))
    a("")
    a("## דיוק סוג-פתיחה וסוג-יום")
    a("")
    a("| מבט | פתיחה מול ייחוס | סוג-יום (משפחה) מול ייחוס | סוג-יום מדויק | פתיחה מול מייקל | סוג-יום מול מייקל |")
    a("|---|---|---|---|---|---|")
    for v in ("live", "replay"):
        h = S["hit"].get(v)
        if not h:
            continue
        a("| %s | %s | %s | %s | %s | %s |" % ("לייב/דמו" if v == "live" else "ריפליי", fr(h["vs_ref"]["opening"]), fr(h["vs_ref"]["day_type"]),
                                             fr(h["vs_ref"]["day_type_exact"]), fr(h["vs_michael"]["opening"]), fr(h["vs_michael"]["day_type"])))
    a("")
    a("## זמן עד תווית-יום נכונה (דקות אחרי 16:30)")
    a("")
    a("| מבט | n | חציון | p25 | p75 | ≤30 | 30–60 | 60–120 | 120–240 | >240 | לא הגיעה | חציון-יציבות |")
    a("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for v in ("live", "replay"):
        h = S["hit"].get(v)
        if not h:
            continue
        t = h["ttc"]; b = t["bins"]
        a("| %s | %d | %s | %s | %s | %d | %d | %d | %d | %d | %d | %s |" % ("לייב/דמו" if v == "live" else "ריפליי", t["n"], f2(t["median"], False), f2(t["p25"], False),
                                                                          f2(t["p75"], False), b["≤30"], b["30–60"], b["60–120"], b["120–240"], b[">240"], b["never"],
                                                                          f2(t["stable_median"], False)))
    a("")
    for v in ("live", "replay"):
        cl = [c for c in S["cells"] if c["view"] == v]
        if not cl:
            continue
        n_all = len(cl)
        imp = lambda c: abs(c["pts"]) + c["missed_pts"] + 0.5 * abs(c["would_pts"])
        cl = [c for c in cl if c["fires"] or c["missed_n"] or c["would_n"] >= 2]
        if len(cl) > MD_MAX_ROWS:
            keep = set(id(c) for c in sorted(cl, key=lambda c: -imp(c))[:MD_MAX_ROWS])
            cl = [c for c in cl if id(c) in keep]
        a("## תאים — סוג-יום (אמת) × שלב × משפחה · %s" % ("לייב/דמו" if v == "live" else "ריפליי"))
        a("")
        a("_%d מתוך %d תאים (ירי / פספוס / ≥2 'היה-יורה'; עד %d החשובים) — הטבלה המלאה ב-SUMMARY.json._" % (len(cl), n_all, MD_MAX_ROWS))
        a("")
        a("| סוג-יום | שלב | משפחה | ירי | ניצחון% | Σ נק׳ | Σ$ | היה-יורה | Σ היה-יורה | רגליים שפוספסו | Σ פספוס | שער מוביל | ימים |")
        a("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for c in cl:
            a("| %s | %s | %s | %d | %s | %s | %s | %d | %s | %d | %s | %s | %d |" % (
                FAM_HEB_DT.get(c["dt"], c["dt"]), c["ph"], c["fam"], c["fires"], ("%.0f" % c["win_pct"]) if c["win_pct"] is not None else "—",
                f2(c["pts"]) if c.get("priced") else "—", f2(c["usd"]) if c.get("usd") is not None else "—", c["would_n"], f2(c["would_pts"]) if c["would_n"] else "—",
                c["missed_n"], ("%.0f" % c["missed_pts"]) if c["missed_n"] else "—", c.get("top_gate") or "", c["n_days"]))
        a("")
    a("## מה-אם — כשהתווית מתחלפת בזמן שהעסקה פתוחה (נק׳ לחוזה, Σ)")
    a("")
    a("| מבט | סוג | מ- | ל- | N | EXIT | BE | HOLD | הטוב | N<8 |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for w in S["what_if"]:
        a("| %s | %s | %s | %s | %d | %s | %s | %s | %s | %s |" % ("לייב/דמו" if w["view"] == "live" else "ריפליי", "סוג-יום" if w["kind"] == "day_type" else "פתיחה",
                                                            w["frm"], w["to"], w["n"], f2(w["exit"]), f2(w["be"]), f2(w["hold"]), w["best"], "⚠️" if w["small_n"] else ""))
    if not S["what_if"]:
        a("| — | | | | 0 | | | | | |")
    a("")
    for v in ("live", "replay"):
        br = S["branches"].get(v) or []
        if not br:
            continue
        a("## מועמדי-ענף (6) · %s" % ("לייב/דמו" if v == "live" else "ריפליי"))
        a("")
        for b in br:
            a("%d. **%s** — N=%d%s · Σ %s נק׳%s · %d ימים%s" % (b["rank"], b["text"], b["n"], " ⚠️ N<8" if b["small_n"] else "", f2(b["pts"]),
                                                          (" · %s$" % f2(b["usd"])) if b.get("usd") is not None else "", b["n_days"],
                                                          " (פספוס = כל הרגל; לא כל הרגל ניתנת לתפיסה)" if b["kind"] == "allow" else ""))
        a("")
    a("## הנחות ופערי-נתונים")
    a("")
    for x in S["caveats"]:
        a("- " + x)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L_) + "\n")


CAVEATS = [
    "אמת = תווית של מייקל (harness_out/swipe/labels.json) כשקיימת, אחרת הייחוס החוקי (eod_journal: IB, הרחבה-עם-קבלה = 2 סגירות, מיקום-הסגירה) — ספי-הייחוס אינם של מייקל.",
    "השוואת סוג-יום לפי משפחה: Trend_Normal/Trend_DD → מגמה; Variation/Normal_Variation → וריאציה; Neutral_Center/Extreme → ניטרלי.",
    "תווית-המערכת (לייב) = מכונת-S1 (v9_day_type_state ∪ צילום day_type_machine בכל עסקת-צל); ריפליי = s1.live_label. פתיחה = נעילת T-314 מהלוג (לייב, מ-02.10) / s1.ot_locked (ריפליי).",
    "'היה-יורה' = עסקת-צל שעברה את כל השערים (לייב) / route בלי blocked_by שלא נכנס ללייב (ריפליי), אחרי ניכוי התאום של עסקה אמיתית וכפילויות באותו בר; נקודות = סימולציית-בר עד T1.",
    "רגל = זיגזג (review_lib) ≥ max(12, 1.5×ATR14) ו-≥3 ברים; 'נתפסה' אם ירי או 'היה-יורה' בכיוונה נכנס בחצי הראשון שלה. Σ פספוס = הרגל המלאה (חסם עליון).",
    "מה-אם: EXIT בסגירת בר-ההיפוך · BE = סטופ לכניסה מבר-ההיפוך עם היעדים המקוריים · HOLD = התוצאה בפועל (סימולציה כשלא מתומחרת).",
    "לייב: רגל בלי 'דופק' (שורות BAR ב-v9_decision_vectors, מ-16.09) בחלון שלה = המערכת לא רצה — נספרת בנפרד ולא כפספוס; לפני 16.09 אין דופק ⇒ הכול נחשב מכוסה.",
    "ימי ריפליי מ-07.07 ואילך מחושבים על ברי mems26 (לייב); ימי ריפליי-בלבד על mems26_hist — ה-DB שההרנס רץ עליו.",
]


def main(argv=None):
    ap = argparse.ArgumentParser(description="DAYMAP aggregate (read-only except SUMMARY.*)")
    ap.add_argument("--version", default=L.VERSION_DEFAULT)
    ap.add_argument("--dir", default=None)
    ap.add_argument("--since"); ap.add_argument("--until")
    a = ap.parse_args(argv)
    d = a.dir or os.path.join(L.REPO, "harness_out", "daymap", a.version)
    if not os.path.isabs(d):
        d = os.path.join(L.REPO, d)
    days = load_days(d, a.since, a.until)
    S = dict(v=a.version, v_heb=L.VERSION_HEB if a.version == L.VERSION_DEFAULT else a.version, generated=dt.datetime.now(L.IL).strftime("%Y-%m-%d %H:%M"),
             n_files=len(days), n_live=sum(1 for R in days if R.get("live") and R["live"].get("available")),
             n_replay=sum(1 for R in days if R.get("replay")), n_partial=sum(1 for R in days if R.get("partial")),
             n_live_nodata=sum(1 for R in days if R.get("live") and not R["live"].get("available")),
             range=[days[0]["date"], days[-1]["date"]] if days else None, hit={}, cells=[], what_if=[], branches={}, caveats=CAVEATS)
    S["totals"] = {}
    for v in ("live", "replay"):
        Vs = [R[v] for R in days if R.get(v) and R[v].get("available")]
        if Vs:
            sm = [V["summary"] for V in Vs]
            S["totals"][v] = dict(days=len(Vs), fired=sum(s["n_fired"] for s in sm), pts=round(sum(s["pts"] or 0 for s in sm), 2),
                                  usd=(round(sum(s["usd"] or 0 for s in sm), 2) if v == "live" else None),
                                  would=sum(s["n_would"] for s in sm), would_pts=round(sum(s["would_pts"] or 0 for s in sm), 2),
                                  missed=sum(s["n_missed"] for s in sm), missed_pts=round(sum(s["missed_pts"] or 0 for s in sm), 2),
                                  uncovered=sum(s.get("n_uncovered") or 0 for s in sm), uncovered_pts=round(sum(s.get("uncovered_pts") or 0 for s in sm), 2))
    for v in ("live", "replay"):
        if any(R.get(v) for R in days):
            S["hit"][v] = hits(days, v)
            cl = cells(days, v)
            S["cells"] += cl
            S["what_if"] += what_ifs(days, v)
            S["branches"][v] = branches(cl)
    with open(os.path.join(d, "SUMMARY.json"), "w", encoding="utf-8") as fh:
        json.dump(S, fh, ensure_ascii=False, indent=1, default=str)
    write_md(S, os.path.join(d, "SUMMARY.md"))
    hv = S["hit"]
    print("DAYMAP aggregate %s: %d files (live %d · replay %d · partial %d) → %s/SUMMARY.{json,md}" % (a.version, S["n_files"], S["n_live"], S["n_replay"],
                                                                                                  S["n_partial"], os.path.relpath(d, L.REPO)))
    for v, h in hv.items():
        print("  %s: opening %s · day-type %s · exact %s · ttc median %s min (n %d, never %d)" % (
            v, fr(h["vs_ref"]["opening"]), fr(h["vs_ref"]["day_type"]), fr(h["vs_ref"]["day_type_exact"]), f2(h["ttc"]["median"], False), h["ttc"]["n"], h["ttc"]["never"]))
    for v, br in S["branches"].items():
        for b in br[:6]:
            print("  [%s] %d. %s — N=%d%s Σ %+.1f" % (v, b["rank"], b["text"], b["n"], " (N<8)" if b["small_n"] else "", b["pts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
