#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_scorecard.py — the opinion quality of every gate and every shadow producer, on ALL their candidates
(not only the ideal ones): what did the candidates each gate refused go on to do?

For every route in the baseline replay (58 clean sessions, the engine of today) that was BLOCKED by a gate or
routed SHADOW_ONLY, the candidate is simulated on the bars with its own stop and a 1.5R target (the fixed
evaluation model; first touch, EOD close, 1 contract, $2.60 RT). Candidates are scored independently (this is
the gate's opinion quality, not a portfolio) — a gate whose refused candidates sum positive is a gate that
costs money; one whose refused candidates sum negative is doing its job. Same for shadow-only producers.

Output: docs/reports/GATE_SCORECARD_<date>.md · render_mobile_relay/static/docs/data/gate_scorecard.json
"""
import collections, datetime as dt, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem"); COMM = 2.60; TODAY = dt.datetime.now(IL).date().isoformat()
B = os.path.join(ROOT, "harness_out", "t458")
sessions = sorted(os.path.basename(p)[8:18] for p in glob.glob(os.path.join(B, "branch1_*.json")))

def bars_of(d):
    rows = read_all("""select ts, high h, low l, close c from v9_bars_5min_woodies where symbol='MES'
      and (ts at time zone 'Asia/Jerusalem')::date = :d and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by ts""", {"d": d})
    return [dict(ts=r["ts"], h=float(r["h"]), l=float(r["l"]), c=float(r["c"])) for r in rows]

def sim(after, short, ep, st):
    R = abs(ep - st); tgt = 1.5 * R
    for b in after:
        hit_stop = (b["h"] >= st) if short else (b["l"] <= st)
        fav = (ep - b["l"]) if short else (b["h"] - ep)
        if hit_stop: return -R
        if fav >= tgt: return tgt
    return ((ep - after[-1]["c"]) if short else (after[-1]["c"] - ep)) if after else 0.0

def parse(s):
    return dt.datetime.fromisoformat(s.replace(" ", "T"))

rows = []
for d in sessions:
    p = os.path.join(B, f"r15_{d}.json")
    if not os.path.exists(p): p = os.path.join(B, f"branch1_{d}.json")
    j = json.load(open(p)); bs = bars_of(d)
    if not bs: continue
    for r in j.get("routes") or []:
        res = r.get("result") or {}
        if res.get("live"): kind = "LIVE"; key = "LIVE"
        elif r.get("blocked_by"): kind = "GATE"; key = str(r["blocked_by"]).split(" ")[0]
        elif r.get("live_blocked_by"): kind = "GATE"; key = str(r["live_blocked_by"]).split(" ")[0]
        elif res.get("shadow"): kind = "SHADOW"; key = r.get("classification") or "?"
        else: continue
        ep = float(r.get("entry") or 0); st = float(r.get("stop") or 0); short = r.get("direction") == "SHORT"
        R = abs(ep - st)
        if ep <= 0 or st <= 0 or R < 1.0 or R > 30: continue
        t0 = parse(r["_dbg_clock"]["sg_now"]); after = [b for b in bs if b["ts"] > t0]
        if not after: continue
        pts = sim(after, short, ep, st)
        rows.append(dict(d=d, kind=kind, key=key, producer=r.get("classification"), dir=r.get("direction"), il=(r.get("il") or "")[:5],
                         phase=("A" if r["il"] < "16:45" else "B" if r["il"] < "17:30" else "C" if r["il"] < "21:00" else "D"), R=round(R, 2), pts=round(pts, 2), usd=round(pts * 5 - COMM, 1)))

def table(rs, keyf):
    m = collections.defaultdict(lambda: dict(n=0, w=0, usd=0.0))
    for r in rs:
        k = keyf(r); m[k]["n"] += 1; m[k]["w"] += (r["pts"] > 0); m[k]["usd"] += r["usd"]
    return m
gates = table([r for r in rows if r["kind"] == "GATE"], lambda r: r["key"])
shadow = table([r for r in rows if r["kind"] == "SHADOW"], lambda r: r["key"])
live = table([r for r in rows if r["kind"] == "LIVE"], lambda r: r["producer"])
gate_phase = table([r for r in rows if r["kind"] == "GATE"], lambda r: r["key"] + " · " + r["phase"])
gate_dir = table([r for r in rows if r["kind"] == "GATE"], lambda r: r["key"] + " · " + r["dir"])

L = []; A = L.append
A(f"# כרטיס-הציונים של השערים והמפיקים — {len(sessions)} סשנים ({TODAY})")
A("")
A("**השאלה:** מה עשו המועמדים שכל שער סירב להם, ומה עשו המועמדים שכל מפיק-צל הציע? כל מועמד מדומה על הברים עם הסטופ שלו ויעד 1.5R, חוזה 1, אחרי עמלות, **באופן בלתי-תלוי** (איכות-הדעה של השער, לא תיק). "
  "שער שהמועמדים-שסירב-להם מסתכמים **חיובי** עולה לנו כסף; שער שהם מסתכמים **שלילי** עושה את עבודתו.")
A("")
A("## 1 · השערים")
A("")
A("| שער | מועמדים שנחסמו | win% | Σ$ אילו היו נלקחים | ממוצע/מועמד | פסק |")
A("|---|---|---|---|---|---|")
for k, v in sorted(gates.items(), key=lambda kv: -kv[1]["usd"]):
    verdict = "❌ עולה כסף" if v["usd"] > 100 and v["n"] >= 15 else ("✅ מגן" if v["usd"] < -100 and v["n"] >= 15 else "≈ ניטרלי / מדגם קטן")
    A(f"| {k} | {v['n']} | {100*v['w']/max(v['n'],1):.0f}% | {v['usd']:+,.0f}$ | {v['usd']/max(v['n'],1):+.1f}$ | {verdict} |")
A("")
A("## 2 · מפיקי-הצל (מה שהם הציעו, בלתי-תלוי)")
A("")
A("| מפיק-צל | מועמדים | win% | Σ$ | ממוצע/מועמד |")
A("|---|---|---|---|---|")
for k, v in sorted(shadow.items(), key=lambda kv: -kv[1]["usd"]):
    A(f"| {k} | {v['n']} | {100*v['w']/max(v['n'],1):.0f}% | {v['usd']:+,.0f}$ | {v['usd']/max(v['n'],1):+.1f}$ |")
A("")
A("## 3 · מה שכן ירה לייב, לפי מפיק (אותו מודל-הערכה)")
A("")
A("| מפיק | עסקאות | win% | Σ$ |")
A("|---|---|---|---|")
for k, v in sorted(live.items(), key=lambda kv: -kv[1]["usd"]):
    A(f"| {k} | {v['n']} | {100*v['w']/max(v['n'],1):.0f}% | {v['usd']:+,.0f}$ |")
A("")
A("## 4 · השערים לפי שלב וכיוון (איפה בדיוק השער טועה)")
A("")
A("| שער · שלב/כיוון | n | win% | Σ$ |")
A("|---|---|---|---|")
for m in (gate_phase, gate_dir):
    for k, v in sorted(m.items(), key=lambda kv: -kv[1]["usd"]):
        if v["n"] >= 10: A(f"| {k} | {v['n']} | {100*v['w']/max(v['n'],1):.0f}% | {v['usd']:+,.0f}$ |")
md = "\n".join(L)
mp = os.path.join(ROOT, "docs", "reports", f"GATE_SCORECARD_{TODAY}.md"); open(mp, "w", encoding="utf-8").write(md)
od = os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data"); os.makedirs(od, exist_ok=True)
json.dump(dict(generated=dt.datetime.now(IL).isoformat(timespec="minutes"), sessions=len(sessions), gates=gates, shadow=shadow, live=live,
               gate_phase=gate_phase, gate_dir=gate_dir, n_rows=len(rows)), open(os.path.join(od, "gate_scorecard.json"), "w"), ensure_ascii=False, default=str)
print(f"routes scored: {len(rows)}")
for k, v in sorted(gates.items(), key=lambda kv: -kv[1]["usd"]):
    print(f"  GATE   {k:34s} n={v['n']:4d} win {100*v['w']/max(v['n'],1):3.0f}% Σ{v['usd']:+9.0f}$")
for k, v in sorted(shadow.items(), key=lambda kv: -kv[1]["usd"]):
    print(f"  SHADOW {k:34s} n={v['n']:4d} win {100*v['w']/max(v['n'],1):3.0f}% Σ{v['usd']:+9.0f}$")
print("→", mp)
