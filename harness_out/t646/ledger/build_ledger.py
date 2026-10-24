#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-646 task 1 — the day ledger: one row per day, from the DAYMAP day files of version t646-live
(scripts/day_dissect.py on the 81 T-640 replay days, truth: opening = v2, day type = Dalton rule-based reference).

Writes ledger.json (rows + cells) and LEDGER.md (Hebrew). Read-only on everything else.
  python3 harness_out/t646/ledger/build_ledger.py [harness_out/daymap/t646-live]
"""
import os, sys, json, glob, collections
ROOT = '/Users/michael/Downloads/mems26_web_git'
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import daymap_lib as L  # noqa: E402

OT = {"OPEN_DRIVE": "Drive", "OPEN_TEST_DRIVE": "Test-Drive", "OPEN_REJECTION_REVERSE": "ORR",
      "OPEN_AUCTION_IN": "Auction-In", "OPEN_AUCTION_OUT": "Auction-Out"}
FAM_HEB = {"Trend": "מגמה", "Variation": "וריאציה", "Normal": "נורמלי", "Neutral": "ניטרלי", "Nontrend": "ללא-מגמה", None: "?"}


def ot_s(x, d=None):
    s = OT.get(L.norm_ot(x), "?")
    return s + ({"up": "↑", "down": "↓"}.get(d or "", "") if s in ("Drive", "Test-Drive", "ORR") else "")


def row_of(r):
    t = r["truth"]; rf = t.get("ref_feats") or {}
    v = r.get("replay") or {}; s = v.get("summary") or {}; h = v.get("hit") or {}; sysv = v.get("system") or {}
    lv = (r.get("live") or {}).get("summary") or {}
    legs = [x for x in (v.get("legs") or []) if x.get("missed")]
    big = max(legs, key=lambda x: x.get("pts") or 0) if legs else None
    fam = L.dt_family(t["day_type"])
    eod = (sysv.get("eod") or {}).get("dt")
    return dict(
        date=r["date"], dow=r.get("dow"), partial=r.get("partial"), open_loc=(r.get("refs") or {}).get("open_loc"),
        opening=L.norm_ot(t["opening"]), v2_dir=t.get("v2_direction"), v2_lock_bar=t.get("v2_lock_bar"),
        day_type=L.norm_dt(t["day_type"]), fam=fam, ib_w=(r.get("ib") or {}).get("width"), rib=rf.get("rib"),
        ext_up=rf.get("ext_up"), ext_dn=rf.get("ext_dn"), close_pos=rf.get("close_pos"),
        s1_eod=eod, s1_eod_fam=L.dt_family(eod) if eod else None, dt_ok=h.get("day_type_ok"),
        first_ok_min=h.get("first_ok_min"), stable_ok_min=h.get("stable_ok_min"),
        r_n=s.get("n_fired"), r_w=s.get("wins"), r_l=s.get("losses"), r_pts=s.get("pts"), r_usd=s.get("harness_usd"),
        would_n=s.get("n_would"), would_pts=s.get("would_pts"), top_block=s.get("top_block"),
        missed_n=s.get("n_missed"), missed_pts=s.get("missed_pts"), caught_pts=s.get("caught_pts"),
        big_miss=(dict(dir=big["dir"], t=big["t_from"] + "–" + big["t_to"], pts=big["pts"], phase=big.get("phase"),
                       blocked=["%s/%s" % (b["fam"], b["gate"]) for b in (big.get("blocked") or [])][:3]) if big else None),
        l_n=lv.get("n_fired"), l_usd=lv.get("usd"), has_replay=bool(v), has_live=bool(lv))


def main(ddir):
    rows = []
    for p in sorted(glob.glob(os.path.join(ddir, "20*.json"))):
        with open(p, encoding="utf-8") as fh:
            rows.append(row_of(json.load(fh)))
    rows = [x for x in rows if x["has_replay"]]
    cells = collections.defaultdict(lambda: dict(days=0, usd=0.0, pts=0.0, pos=0, neg=0, flat=0, missed=0.0, caught=0.0,
                                                  would=0.0, n=0, blocks=collections.Counter(), dates=[]))
    for x in rows:
        if x["partial"]:
            continue
        c = cells[(x["opening"], x["fam"])]
        c["days"] += 1; c["usd"] += x["r_usd"] or 0; c["pts"] += x["r_pts"] or 0; c["n"] += x["r_n"] or 0
        c["missed"] += x["missed_pts"] or 0; c["caught"] += x["caught_pts"] or 0; c["would"] += x["would_pts"] or 0
        u = x["r_usd"] or 0
        c["pos" if u > 0 else "neg" if u < 0 else "flat"] += 1
        if x["top_block"]:
            c["blocks"][x["top_block"][0]] += x["top_block"][1]
        c["dates"].append(x["date"])
    out = dict(rows=rows, cells=[dict(opening=k[0], fam=k[1], **{kk: (dict(vv) if isinstance(vv, collections.Counter) else vv)
                                                                   for kk, vv in v.items()}) for k, v in sorted(cells.items())])
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
    # ── Markdown ──
    M = []; P = M.append
    full = [x for x in rows if not x["partial"]]
    P("# יומן הימים — T-646 משימה 1 (81 ימי ריפליי, הקוד של 23.10)")
    P("")
    P("אמת: פתיחה = v2 (מה שהעץ ראה אחרי הנעילה); סוג-יום = ייחוס-דלתון חוקי (IB, הרחבה שהתקבלה = 2 סגירות, מיקום-הסגירה). "
      "ריפליי = הרנס T-640 (live, ‎.env של 23.10); $ = של ההרנס בגודל החוזים האמיתי; נק׳ = לחוזה אחד.")
    P("")
    tot = sum(x["r_usd"] or 0 for x in full)
    P("**סה״כ %d ימים מלאים:** ריפליי %+.0f$ · ימים חיוביים %d · שליליים %d · בלי עסקה %d · רגליים שפוספסו Σ %.0f נק׳ · נתפסו Σ %.0f נק׳."
      % (len(full), tot, sum(1 for x in full if (x["r_usd"] or 0) > 0), sum(1 for x in full if (x["r_usd"] or 0) < 0),
         sum(1 for x in full if not x["r_n"]), sum(x["missed_pts"] or 0 for x in full), sum(x["caught_pts"] or 0 for x in full)))
    P("")
    P("## לפי תא: סוג-פתיחה (v2) × סוג-יום (ייחוס)")
    P("")
    P("| פתיחה | סוג-יום | ימים | ריפליי $ | ממוצע ליום | +/− | עסקאות | פוספס נק׳ | נתפס נק׳ | 'היה-יורה' נק׳ | חסימה מובילה |")
    P("|---|---|---|---|---|---|---|---|---|---|---|")
    for c in sorted(out["cells"], key=lambda c: c["usd"]):
        b = max(c["blocks"].items(), key=lambda kv: kv[1])[0] if c["blocks"] else "—"
        P("| %s | %s | %d | %+.0f | %+.0f | %d/%d | %d | %.0f | %.0f | %+.0f | %s |" % (
            ot_s(c["opening"]), FAM_HEB.get(c["fam"], c["fam"]), c["days"], c["usd"], c["usd"] / c["days"], c["pos"], c["neg"],
            c["n"], c["missed"], c["caught"], c["would"], b))
    P("")
    P("## יום אחר יום")
    P("")
    P("| תאריך | פתיחה (v2) | סוג-יום (ייחוס) | S1 בסוף-יום | תווית נכונה מ- (דק׳) | ריפליי: עסקאות · $ | לייב/דמו $ | פוספס (נק׳) | הפספוס הגדול | חסימה מובילה |")
    P("|---|---|---|---|---|---|---|---|---|---|")
    for x in rows:
        bm = x["big_miss"]
        P("| %s%s | %s | %s | %s%s | %s | %s · %+.0f | %s | %.0f | %s | %s |" % (
            x["date"], " (חלקי)" if x["partial"] else "", ot_s(x["opening"], x["v2_dir"]), x["day_type"],
            x["s1_eod"] or "—", "" if x["dt_ok"] in (None, True) else " ✗",
            ("%.0f" % x["first_ok_min"]) if x["first_ok_min"] is not None else "—",
            x["r_n"] or 0, x["r_usd"] or 0, ("%+.0f" % x["l_usd"]) if x["l_usd"] is not None else "—", x["missed_pts"] or 0,
            ("%s %s %.0f (%s)" % ("↑" if bm["dir"] == "LONG" else "↓", bm["t"], bm["pts"], ", ".join(bm["blocked"]) or "אף מועמד")) if bm else "—",
            ("%s ×%d" % tuple(x["top_block"])) if x["top_block"] else "—"))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "LEDGER.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(M) + "\n")
    print("ledger: %d rows (%d full) · %d cells · replay $%+.0f" % (len(rows), len(full), len(out["cells"]), tot))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "harness_out", "daymap", "t646-live"))
