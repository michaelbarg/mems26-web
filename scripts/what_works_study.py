#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""what_works_study.py — "מה מביא לנו תוצאה טובה יותר" (Michael 22.09 13:20).

Takes EVERY system entry (live + shadow) since --since, recomputes what was visible at the
entry bar CAUSALLY from the bars (developing value area, bars since the session extreme,
with/against the day, phase, volume ratio, trigger strength) and prices each entry under the
ONE fixed evaluation model in three exit variants, then compares groups:

  1. rotation days (Normal / Neutral_* / Variation, live label at entry): WHERE the entry was —
     fade at the edge (long near/below VAL, short near/above VAH) · middle / POC · continuation
     through the edge (long near VAH / above, short near VAL / below)
  2. trend days: with the trend at a FRESH extreme (0-1 bars) vs after a PULLBACK (≥2 bars) vs
     against the trend
  3. exits, same entries: as executed (books) · fixed T1=1.5×ATR (1 contract) · 2-leg ladder ·
     trailing structural stop (chandelier 1×ATR after +1×ATR), EOD close

Read-only. Output: markdown report + JSON for the phone page.
  python3 scripts/what_works_study.py [--since 2026-08-15] [--md ...] [--json ...]
"""
import os, sys, json, argparse, collections, statistics, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem"); TICK = 0.25; USD = 5.0; SLIP = 0.5; COMM = 1.3

ap = argparse.ArgumentParser()
ap.add_argument("--since", default="2026-08-15")
ap.add_argument("--md", default=os.path.join(ROOT, "docs", "reports", "WHAT_WORKS_2026-09-22.md"))
ap.add_argument("--json", default=os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data", "whatworks.json"))
args = ap.parse_args()

bars = read_all("""select ts, open o, high h, low l, close c, volume v from v9_bars_5min_woodies
  where symbol='MES' and ts >= :since and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by ts""",
  {"since": args.since})
by_day = collections.defaultdict(list)
for b in bars:
    t = b["ts"].astimezone(IL)
    by_day[t.date().isoformat()].append({"ts": b["ts"], "il": t, "o": float(b["o"]), "h": float(b["h"]), "l": float(b["l"]), "c": float(b["c"]), "v": float(b["v"] or 0)})
trades = read_all("""select id, mode, direction, entry_ts, entry_price, exit_ts, exit_price, exit_reason, pnl_usd, day_type_at_entry dt, pattern_id_at_entry pat
  from v9_trades where mode in ('live','shadow') and state='CLOSED' and entry_ts >= :since and pnl_usd is not null order by entry_ts""", {"since": args.since})

def atr14(bs, i):
    trs = []
    for k in range(max(1, i - 13), i + 1):
        trs.append(max(bs[k]["h"] - bs[k]["l"], abs(bs[k]["h"] - bs[k-1]["c"]), abs(bs[k]["l"] - bs[k-1]["c"])))
    return statistics.mean(trs) if trs else None

def dev_va(bs):
    cl = [round(b["c"] / TICK) * TICK for b in bs]
    if len(cl) < 4: return None
    poc = collections.Counter(cl).most_common(1)[0][0]; s = sorted(cl); n = len(s); k = int(round(0.7 * n)); best = None
    for i in range(0, n - k + 1):
        w = s[i + k - 1] - s[i]
        if best is None or w < best[0]: best = (w, s[i], s[i + k - 1])
    return {"poc": poc, "val": best[1], "vah": best[2]}

def loc_bucket(px, d, va, atr):
    if not va: return "?"
    tol = max(1.0, 0.5 * atr)
    if d == "LONG":
        if px <= va["val"] + tol: return "edge-fade"          # long at/below VAL
        if px >= va["vah"] - tol: return "continuation"       # long at/above VAH
    else:
        if px >= va["vah"] - tol: return "edge-fade"          # short at/above VAH
        if px <= va["val"] + tol: return "continuation"
    return "mid/POC"

def price_models(bs, i, d, atr):
    """entry at open of bar i+1 ± slip; returns dict of $ for 1c-T1, 2-leg, trail."""
    if i + 1 >= len(bs) or not atr: return None
    sign = 1 if d == "LONG" else -1
    e = bs[i + 1]["o"] + sign * SLIP / 2
    stop0 = e - sign * max(5.0, 1.0 * atr); t1 = e + sign * 1.5 * atr; t2 = e + sign * 2.5 * atr
    def walk(targets, trail=False):
        cur = stop0; done = [False] * len(targets); out = [0.0] * len(targets); best = e
        for j in range(i + 1, len(bs)):
            hi, lo = bs[j]["h"], bs[j]["l"]
            if trail:
                fav = hi if sign > 0 else lo
                if sign * (fav - e) > sign * (best - e): best = fav
                if sign * (best - e) >= 1.0 * atr: cur = max(cur, best - 1.0 * atr) if sign > 0 else min(cur, best + 1.0 * atr)
            for k, t in enumerate(targets):
                if done[k]: continue
                ht = False if t is None else ((hi >= t) if sign > 0 else (lo <= t)); hs = (lo <= cur) if sign > 0 else (hi >= cur)
                if ht and hs: out[k] = 0.0; done[k] = True          # AMBIG: unassigned
                elif ht: out[k] = sign * (t - e); done[k] = True; cur = e if k == 0 else cur
                elif hs: out[k] = sign * (cur - e); done[k] = True
            if all(done): break
        for k in range(len(targets)):
            if not done[k]: out[k] = sign * (bs[-1]["c"] - e)
        return sum(out) * USD - COMM * len(targets)
    return {"m1": walk([t1]), "m2": walk([t1, t2]), "trail": walk([None], trail=True)}

recs = []
for t in trades:
    d0 = t["entry_ts"].astimezone(IL).date().isoformat(); bs = by_day.get(d0)
    if not bs: continue
    i = max((k for k, b in enumerate(bs) if b["ts"] <= t["entry_ts"]), default=None)
    if i is None or i < 3: continue
    d = t["direction"]; atr = atr14(bs, i) or 5.0; e = float(t["entry_price"])
    before = bs[:i + 1]
    hi_i = max(range(i + 1), key=lambda k: bs[k]["h"]); lo_i = min(range(i + 1), key=lambda k: bs[k]["l"])
    bsx = (i - hi_i) if d == "LONG" else (i - lo_i)
    mo = (bs[i]["c"] - bs[0]["o"]) / atr
    with_day = (mo >= 0.5) if d == "LONG" else (mo <= -0.5); against = (mo <= -0.5) if d == "LONG" else (mo >= 0.5)
    va = dev_va(before[:-1]); loc = loc_bucket(e, d, va, atr)
    lab = t["dt"] or "?"; fam = "trend" if lab.startswith("Trend") else "rotation" if lab in ("Normal", "Neutral_Center", "Neutral_Extreme", "Variation", "Normal_Variation") else "unknown"
    hm = bs[i]["il"].hour * 60 + bs[i]["il"].minute; phase = "A" if hm < 1005 else "B" if hm < 1050 else "C" if hm < 1260 else "D"
    pm = price_models(bs, i, d, atr)
    if not pm: continue
    recs.append(dict(id=t["id"], mode=t["mode"], pat=t["pat"], d=d, day=d0, fam=fam, lab=lab, loc=loc, bsx=bsx, with_day=with_day, against=against,
                     phase=phase, books=float(t["pnl_usd"]), **pm))

def summ(rs):
    if not rs: return None
    n = len(rs)
    def s(key): v = [r[key] for r in rs]; return dict(sum=round(sum(v)), avg=round(sum(v) / n, 1), win=round(100 * sum(1 for x in v if x > 0) / n))
    return dict(n=n, books=s("books"), m1=s("m1"), m2=s("m2"), trail=s("trail"))

out = {"generated": dt.datetime.now(IL).isoformat(timespec="minutes"), "since": args.since, "n": len(recs), "tables": []}
def table(title, groups):
    rows = []
    for name, rs in groups:
        sm = summ(rs)
        if sm and sm["n"] >= 5: rows.append(dict(name=name, **sm))
    out["tables"].append(dict(title=title, rows=rows))

rot = [r for r in recs if r["fam"] == "rotation"]; trd = [r for r in recs if r["fam"] == "trend"]
table("ימי-רוטציה (Normal / Neutral / Variation) — איפה הכניסה", [
    ("קצה-ערך (לונג ב-VAL · שורט ב-VAH)", [r for r in rot if r["loc"] == "edge-fade"]),
    ("אמצע / POC", [r for r in rot if r["loc"] == "mid/POC"]),
    ("המשך דרך הקצה (לונג ב-VAH · שורט ב-VAL)", [r for r in rot if r["loc"] == "continuation"]),
])
table("ימי-רוטציה — לפי סוג-יום, קצה-ערך בלבד", [
    (lab, [r for r in rot if r["loc"] == "edge-fade" and r["lab"] == lab]) for lab in ("Normal", "Neutral_Center", "Neutral_Extreme", "Variation")])
table("ימי-מגמה — תזמון וכיוון", [
    ("עם-המגמה · קיצון טרי (0-1 ברים)", [r for r in trd if r["with_day"] and r["bsx"] <= 1]),
    ("עם-המגמה · אחרי פולבק (2-5 ברים)", [r for r in trd if r["with_day"] and 2 <= r["bsx"] <= 5]),
    ("עם-המגמה · פולבק עמוק (6+ ברים)", [r for r in trd if r["with_day"] and r["bsx"] >= 6]),
    ("נגד-המגמה", [r for r in trd if r["against"]]),
])
table("שלב-היום — כל הכניסות עם-הכיוון", [
    (f"שלב {p}", [r for r in recs if r["with_day"] and r["phase"] == p]) for p in "ABCD"])
table("יציאות — אותן כניסות, ארבע דרכים (ימי-מגמה, עם-המגמה)", [
    ("כל הכניסות עם-המגמה בימי-מגמה", [r for r in trd if r["with_day"]])])
table("יציאות — ימי-רוטציה, קצה-ערך", [("כניסות בקצה-ערך", [r for r in rot if r["loc"] == "edge-fade"])])
table("לייב בלבד (מה שבאמת נסחר) — לפי משפחת-יום", [
    ("מגמה", [r for r in recs if r["mode"] == "live" and r["fam"] == "trend"]),
    ("רוטציה", [r for r in recs if r["mode"] == "live" and r["fam"] == "rotation"]),
    ("לא-מסווג בכניסה", [r for r in recs if r["mode"] == "live" and r["fam"] == "unknown"])])

os.makedirs(os.path.dirname(args.json), exist_ok=True)
json.dump(out, open(args.json, "w"), ensure_ascii=False, indent=0)
md = [f"# מה מביא תוצאה טובה יותר — {len(recs)} כניסות (לייב+צל) מאז {args.since}", "",
      "**מודל-הערכה קבוע:** כניסה בפתיחת הבר הבא ±0.25, סטופ 1×ATR (מינימום 5), T1=1.5×ATR, T2=2.5×ATR, BE אחרי T1, נגיעה-ראשונה, AMBIG לא מיוחס, סגירה EOD, $5/נק׳, עמלה $1.30. **טרייל** = אחרי +1×ATR הסטופ רודף במרחק 1×ATR מהקיצון. **ספרים** = מה שבאמת נרשם.", ""]
for tb in out["tables"]:
    md += [f"## {tb['title']}", "", "| קבוצה | N | ספרים Σ$ (win%) | T1 קבוע 1c Σ$ (win%) | סולם-2 Σ$ | טרייל Σ$ (win%) |", "|---|---|---|---|---|---|"]
    for r in tb["rows"]:
        md.append(f"| {r['name']} | {r['n']} | {r['books']['sum']} ({r['books']['win']}%) | {r['m1']['sum']} ({r['m1']['win']}%) | {r['m2']['sum']} | {r['trail']['sum']} ({r['trail']['win']}%) |")
    md.append("")
open(args.md, "w", encoding="utf-8").write("\n".join(md))
print(f"entries {len(recs)} → {args.md}")
for tb in out["tables"]:
    print("==", tb["title"])
    for r in tb["rows"]:
        print(f"   {r['name'][:44]:44s} N={r['n']:4d} books {r['books']['sum']:7d} ({r['books']['win']:3d}%)  m1 {r['m1']['sum']:7d} ({r['m1']['win']:3d}%)  m2 {r['m2']['sum']:7d}  trail {r['trail']['sum']:7d} ({r['trail']['win']:3d}%)")
