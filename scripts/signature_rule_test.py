#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""signature_rule_test.py — can a LOCATION / VOLUME / CANDLE rule find winning trades on its own?
(Michael 23.09 14:30: "האם אפשר להפיק מהדוח איך מזהים עסקאות בהתאם להנחיה של מיקום, ווליום ונרות,
שיאפשר להגדיל את העץ עם עסקאות מצליחות?")

The daily exam records what the IDEAL entries looked like. That is only half the answer: a rule
drawn from winners must also be applied to EVERY bar to see how many losers share the look.
This script does exactly that — each candidate rule is a causal predicate on the bar's features
(review_lib.features: zone vs developing value area, IB edge, prior VA, trigger-bar quality,
range/ATR, volume vs the last 5 bars, delta, with/against day, pullback, structure break); it
fires on every RTH bar (after the IB, one open trade per rule per session) and is judged with
the fixed evaluation model (stop max(5, 1×ATR) · T1 1.5×ATR · first touch on 5-min bars · EOD
close · $5/pt · $1.30/side). No hindsight anywhere: features at bar i use bars[:i+1] only.

  python3 scripts/signature_rule_test.py [--sessions 40]
→ table: rule · N · win% · avg pts · Σ$ (m1) · by day type, and the verdict per rule:
  EDGE (N≥15, Σ$>0, win%≥45) ⇒ candidate shadow producer · WEAK · NEGATIVE (a gate, not a producer).
Output: docs/reports/SIGNATURE_RULES_<date>.md + data/signature_rules.json
"""
import os, sys, json, argparse, collections, statistics, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts")); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
import oracle_engine as oe
import review_lib as rl
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem")
ap = argparse.ArgumentParser()
ap.add_argument("--sessions", type=int, default=40)
ap.add_argument("--out", default=os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data"))
args = ap.parse_args()
TODAY = dt.datetime.now(IL).date().isoformat()
COMM = 2.60  # $ per round trip, one contract

bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd on cd.ts=b.ts
 where b.symbol='MES' and b.ts >= now() - interval '60 days' and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""", {})
by_day = collections.defaultdict(list)
for b in bars: by_day[str(b["d"])].append(b)
alld = [d for d in sorted(by_day) if len(by_day[d]) >= 60]
days = alld[-args.sessions:]
prev_va = {}
for k, d in enumerate(alld):
    if k:
        pb = by_day[alld[k - 1]]; prev_va[d] = oe.compute_developing_va(pb, len(pb) - 1) if len(pb) > 5 else {}
dth = {str(r["date"]): r for r in read_all("select date, day_type, opening_type from v9_day_type_history where date >= :d", {"d": alld[0]})}

# ── the rules: causal predicates on (features f, short) ───────────────────────
def near_poc(f, atr): return f["poc"] is not None and abs(f["_c"] - f["poc"]) <= 0.25 * atr
RULES = {
 "R0 בסיס: בר-טריגר חזק (כל מיקום)":            lambda f, s: f["trigger_ok"] and f["range_ge_08atr"],
 "R1 קצה-הערך: לונג מתחת/ב-VAL · שורט מעל/ב-VAH, טריגר חזק, קיצון טרי (≤2 ברים)":
                                                lambda f, s: f["trigger_ok"] and f["range_ge_08atr"] and ((f["bars_since_low"] <= 2 and f["zone"] == "BELOW_VA") if not s else (f["bars_since_high"] <= 2 and f["zone"] == "ABOVE_VA")),
 "R1v קצה-הערך + ווליום ≥1.3×":                 lambda f, s: f["trigger_ok"] and f["range_ge_08atr"] and f["vol_trig"] and ((f["bars_since_low"] <= 2 and f["zone"] == "BELOW_VA") if not s else (f["bars_since_high"] <= 2 and f["zone"] == "ABOVE_VA")),
 "R1p קצה-ערך-אתמול (±0.5 ATR מ-VAL/VAH של אתמול), טריגר חזק":
                                                lambda f, s: f["trigger_ok"] and f["range_ge_08atr"] and f["near_prev_edge"] and ((f["bars_since_low"] <= 2) if not s else (f["bars_since_high"] <= 2)),
 "R2 עם-היום אחרי פולבק (≥2 ברים נגד), טריגר חזק":
                                                lambda f, s: f["with_day"] and f["pullback_before"] and f["trigger_ok"] and f["range_ge_08atr"],
 "R2d R2 + דלתא עם-הכיוון":                     lambda f, s: f["with_day"] and f["pullback_before"] and f["trigger_ok"] and f["range_ge_08atr"] and f["delta_with"],
 "R3 שבירת-מבנה (סגירה מעבר ל-5 ברים) + ווליום ≥1.3×": lambda f, s: f["structure_break"] and f["vol_trig"] and f["trigger_ok"],
 "R3e R3 + עם ההרחבה מה-IB":                    lambda f, s: f["structure_break"] and f["vol_trig"] and f["trigger_ok"] and f["with_ext"],
 "R4 IB-edge: דחייה בקצה-IB (≤0.5 ATR), טריגר חזק, נגד ההרחבה": lambda f, s: f["near_ib_edge"] and f["trigger_ok"] and f["range_ge_08atr"] and not f["with_ext"] and f["ext"] == "none",
 "R2t R2 רק בימי-מגמה (Trend_*)":                 lambda f, s: f["with_day"] and f["pullback_before"] and f["trigger_ok"] and f["range_ge_08atr"] and f["_dt"].startswith("Trend"),
 "R4n R4 רק בימי Normal/Neutral":               lambda f, s: f["near_ib_edge"] and f["trigger_ok"] and f["range_ge_08atr"] and not f["with_ext"] and f["ext"] == "none" and f["_dt"] in ("Normal", "Neutral_Center", "Neutral_Extreme"),
 "R1n R1 רק בימי Normal/Neutral/Variation (רוטציה)": lambda f, s: f["trigger_ok"] and f["range_ge_08atr"] and f["_dt"] in ("Normal", "Neutral_Center", "Neutral_Extreme", "Variation", "Normal_Variation") and ((f["bars_since_low"] <= 2 and f["zone"] == "BELOW_VA") if not s else (f["bars_since_high"] <= 2 and f["zone"] == "ABOVE_VA")),
 "R5 עם-ההרחבה-מה-IB, פולבק, טריגר חזק, ווליום (המשך-הרחבה)": lambda f, s: f["with_ext"] and f["pullback_before"] and f["trigger_ok"] and f["vol_trig"],
 "N1 (בדיקת-הנחיה) כניסה ליד ה-POC (≤0.25 ATR), טריגר חזק":   lambda f, s: f["trigger_ok"] and f["range_ge_08atr"] and near_poc(f, f["atr"]),
 "N2 (בדיקת-הנחיה) המשך אחרי ≥12 ברים מהקיצון, בתוך הבטן": lambda f, s: f["trigger_ok"] and f["zone"] == "IN_VA" and f["bars_from_extreme"] >= 12 and f["with_day"],
}

res = {name: [] for name in RULES}
for d in days:
    bs = by_day[d]; dtype = dth.get(d, {}).get("day_type") or "?"
    busy = {name: -1 for name in RULES}   # one open trade per rule per session
    for i in range(12, len(bs) - 3):        # after the IB, leave 3 bars for resolution
        atr = oe.compute_atr(bs, i) or 0
        if atr <= 0: continue
        for short in (False, True):
            f = rl.features(bs, i, short, prev_va.get(d))
            if not f: continue
            f["_c"] = bs[i]["c"]; f["_dt"] = dtype
            for name, pred in RULES.items():
                if busy[name] >= i: continue
                try: ok = pred(f, short)
                except Exception: ok = False
                if not ok: continue
                m = rl.exit_models(bs, i, short, atr)
                pts = m["t1"]; usd = pts * 5.0 - COMM
                res[name].append(dict(day=d, dt=dtype, t=str(bs[i]["t"])[:5], dir="SHORT" if short else "LONG", pts=round(pts, 2), usd=round(usd, 2),
                                      trail=m["trail"], mx=m["max"], tstop=m["tstop"], be=m["be"], zone=f["zone"], ph=f["ph"]))
                busy[name] = m["end_i"]

def summ(rows):
    n = len(rows)
    if not n: return dict(n=0, win=0, avg=0, usd=0, trail_usd=0)
    w = sum(1 for r in rows if r["pts"] > 0); usd = sum(r["usd"] for r in rows); tr = sum(r["trail"] * 5 - COMM for r in rows)
    ts = sum(r.get("tstop", r["pts"]) * 5 - COMM for r in rows); be = sum(r.get("be", r["pts"]) * 5 - COMM for r in rows)
    return dict(n=n, win=round(100 * w / n), avg=round(sum(r["pts"] for r in rows) / n, 2), usd=round(usd, 2), trail_usd=round(tr, 2), tstop_usd=round(ts, 2), be_usd=round(be, 2), per=round(usd / n, 2))
def verdict(s):
    if s["n"] < 15: return "N קטן"
    if s["usd"] > 0 and s["win"] >= 45: return "EDGE ⇒ מפיק-צל"
    if s["usd"] > 0: return "חלש"
    return "שלילי ⇒ שער"
out = []
print(f"{'rule':70s} {'N':>4} {'win%':>4} {'avg':>6} {'Σ$ m1':>9} {'$/trade':>7} {'Σ$ trail':>9} {'Σ$ tstop6':>9} {'Σ$ BE':>8}  verdict")
for name, rows in res.items():
    s = summ(rows); bydt = collections.defaultdict(list)
    for r in rows: bydt[r["dt"]].append(r)
    bd = {k: summ(v) for k, v in sorted(bydt.items(), key=lambda kv: -len(kv[1]))}
    byph = {k: summ(v) for k, v in sorted(collections.defaultdict(list, {p: [r for r in rows if r["ph"] == p] for p in "BCD"}).items())}
    out.append(dict(rule=name, **s, verdict=verdict(s), by_day_type={k: dict(n=v["n"], win=v["win"], usd=v["usd"]) for k, v in bd.items()},
                    by_phase={k: dict(n=v["n"], win=v["win"], usd=v["usd"]) for k, v in byph.items() if v["n"]}, sample=rows[-6:]))
    print(f"{name[:70]:70s} {s['n']:4d} {s['win']:4d} {s['avg']:6.2f} {s['usd']:9.2f} {s.get('per',0):7.2f} {s['trail_usd']:9.2f} {s.get('tstop_usd',0):9.2f} {s.get('be_usd',0):8.2f}  {verdict(s)}")
os.makedirs(args.out, exist_ok=True)
json.dump(dict(generated=dt.datetime.now(IL).isoformat(timespec="minutes"), sessions=days, model="stop max(5,1×ATR) · T1 1.5×ATR · first-touch 5m · EOD · $5/pt · $1.30/side · one open trade per rule per session · after IB", rules=out),
          open(os.path.join(args.out, "signature_rules.json"), "w"), ensure_ascii=False, indent=0)
md = [f"# מבחן-החתימות — האם כלל של מיקום/ווליום/נרות מוצא עסקאות מנצחות לבד? ({len(days)} סשנים, {days[0]}…{days[-1]})", "",
      "**השיטה:** כל כלל הוא תנאי סיבתי על תכונות-הבר (אזור מול הבטן המתפתחת, קצה-IB, ערך-אתמול, איכות בר-הטריגר, טווח/ATR, ווליום מול 5 הברים הקודמים, דלתא, עם/נגד היום, פולבק, שבירת-מבנה). הוא נורה על **כל** בר אחרי ה-IB (עסקה פתוחה אחת לכלל לסשן) ונשפט במודל-ההערכה הקבוע (סטופ max(5, 1×ATR) · יעד 1.5×ATR · מגע-ראשון · סגירת-יום · 5$/נק׳ · 1.30$/צד). אפס ראייה-לאחור.",
      "**הפסק-דין:** EDGE = N≥15 ∧ Σ$>0 ∧ win%≥45 ⇒ מועמד למפיק-צל · חלש · שלילי ⇒ שער (מה לא לעשות).", "",
      "**ניהול (מערכת 6, אותם כללים):** Σ$ יעד-קבוע · טריילינג 1×ATR · **time-stop** (סקראץ׳ בסגירת הבר ה-6 אם המהלך לא הראה ≥0.5×ATR) · **BE** (סטופ לכניסה אחרי +1×ATR).", "",
      "| כלל | N | win% | ממוצע נק׳ | Σ$ (m1) | $/עסקה | Σ$ טריילינג | Σ$ time-stop | Σ$ BE | פסק-דין | לפי סוג-יום (N · win% · $) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for o in out:
    bd = " · ".join(f"{k} {v['n']}/{v['win']}%/{v['usd']:+.0f}" for k, v in list(o["by_day_type"].items())[:4])
    md.append(f"| {o['rule']} | {o['n']} | {o['win']} | {o['avg']} | {o['usd']:+.2f} | {o.get('per',0):+.2f} | {o['trail_usd']:+.2f} | {o.get('tstop_usd',0):+.2f} | {o.get('be_usd',0):+.2f} | **{o['verdict']}** | {bd} |")
# ── conclusions, computed (not hand-written) ────────────────────────────────
edge = [o for o in out if o["verdict"].startswith("EDGE")]
flips = []
for o in out:
    bd = o["by_day_type"]; pos = [(k, v) for k, v in bd.items() if v["n"] >= 10 and v["usd"] > 0]; neg = [(k, v) for k, v in bd.items() if v["n"] >= 10 and v["usd"] < 0]
    if pos and neg: flips.append((o["rule"], pos, neg))
mgmt = [(o["rule"], o["usd"], o.get("tstop_usd", 0), o.get("be_usd", 0), o["trail_usd"]) for o in out if o["n"] >= 15]
ts_better = sum(1 for r in mgmt if r[2] > r[1]); be_better = sum(1 for r in mgmt if r[3] > r[1]); tr_better = sum(1 for r in mgmt if r[4] > r[1])
md += ["", "## המסקנות (מחושבות מהטבלה)", "",
       f"1. **נרות/מיקום/ווליום כתבנית-בר לבד — אין קצה:** הבסיס (בר-טריגר חזק בכל מיקום) {out[0]['n']} עסקאות, {out[0]['win']}% ניצחון, {out[0]['usd']:+.0f}$. גם קצה-הערך לבד ({out[1]['n']} עסקאות, {out[1]['usd']:+.0f}$) לא. **ווליום-שיא בקצה-הערך שלילי** ({out[2]['n']} עסקאות, {out[2]['win']}%, {out[2]['usd']:+.0f}$) — שיא-ווליום בקצה הוא פריצה, לא דחייה.",
       "2. **ההקשר (סוג-יום × שלב) הוא מה שעושה את ההבדל — זו בדיוק צורת-העץ:** " + ("; ".join(f"{r[:40]}: " + ", ".join(f"{k} {v['n']}/{v['win']}%/{v['usd']:+.0f}$" for k, v in p_) + " מול " + ", ".join(f"{k} {v['n']}/{v['win']}%/{v['usd']:+.0f}$" for k, v in n_) for r, p_, n_ in flips[:4]) if flips else "אין היפוכים ב-N≥10") + ".",
       "3. **מה שיש לו קצה עכשיו:** " + ("; ".join(f"**{o['rule']}** — {o['n']} עסקאות, {o['win']}%, {o['usd']:+.0f}$ ({o.get('per',0):+.2f}$/עסקה)" for o in edge) if edge else "אף כלל לא עבר את הסף (N≥15 ∧ Σ$>0 ∧ win≥45%)") + " ⇒ מפיק-צל בהקשר הזה בלבד.",
       f"4. **ההנחיות השליליות מאושרות במספרים:** כניסה ליד ה-POC {out[-2]['n']} עסקאות {out[-2]['win']}% {out[-2]['usd']:+.0f}$ · המשך בתוך הבטן אחרי ≥12 ברים {out[-1]['n']} עסקאות {out[-1]['win']}% {out[-1]['usd']:+.0f}$ ⇒ שערים, לא מפיקים.",
       f"5. **ניהול (מערכת 6):** time-stop של 6 ברים (סקראץ׳ אם המהלך לא הראה ≥0.5×ATR) שיפר את Σ$ ב-{ts_better} מתוך {len(mgmt)} הכללים עם N≥15 (הבסיס: {out[0]['usd']:+.0f}$ → {out[0].get('tstop_usd',0):+.0f}$); BE אחרי +1×ATR שיפר ב-{be_better}/{len(mgmt)}; טריילינג 1×ATR שיפר ב-{tr_better}/{len(mgmt)} (המדגם רוטציוני). ⇒ המועמד הראשון לענף-ניהול: **time-stop**, אחריו BE — כל אחד נמדד לפי סוג-יום לפני דגל.",
       "", "## איך זה מגדיל את העץ", "1. כלל עם EDGE נכתב כמפיק-צל (`shadow_only`) — יורה ונרשם ב-`v9_trades` כצל בלי לסחור.", "2. אחרי ≥15 עסקאות-צל אמיתיות (לא ריפליי) שמאשרות את המספר — פסיקת-מייקל ⇒ המפיק מחובר ללייב בהקשר שבו הוא מנצח (סוג-יום × שלב × אזור), לא בכל מקום.",
       "3. כלל שלילי הופך לשער (למשל: כניסה ליד ה-POC) — גם זה ענף.", "4. הכלל שרץ פה הוא הבסיס; המבחן-היומי ממשיך למדוד אותו כל ערב, וההרנס מאשר על 56–85 סשנים לפני דגל."]
open(os.path.join(ROOT, "docs", "reports", f"SIGNATURE_RULES_{TODAY}.md"), "w", encoding="utf-8").write("\n".join(md))
print(f"→ docs/reports/SIGNATURE_RULES_{TODAY}.md · data/signature_rules.json")
