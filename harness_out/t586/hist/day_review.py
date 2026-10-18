#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super-agent T1 — DAY REVIEW (Michael 18.10 17:1x: "עובר על שעות המסחר של כל יום"): one markdown per session from the
harness output + the bars: the S1 story (opening lock, IB, day-type transitions), the prior-day value the tree used vs the
real one, and EVERY live-eligible candidate with Dalton's five answers as the system saw them (what is the market trying ·
how well · where vs value · who controls · where the thesis is wrong) next to what the system did and what the bars did
afterwards (MFE / T1 / stop). The reviewer (Michael) tags each line ✓/✗ — that is the LEARNING_DOCTRINE §2 step 3.
usage: day_review.py <TAG> <session> [--db=mems26_hist] [--cand=<cand.csv>] [--out=<dir>]"""
import sys, os, json, subprocess, pandas as pd
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
args = [a for a in sys.argv[1:] if not a.startswith("--")]; opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
TAG, S = args[0], args[1]; DB = opt.get("db", "mems26_hist"); OUT = opt.get("out", "harness_out/t592/day_reviews"); os.makedirs(OUT, exist_ok=True)
j = json.load(open(f"harness_out/t466/{TAG}_{S}.json"))
def q(sql): return subprocess.run([PSQL, "-d", DB, "-Atc", sql], capture_output=True, text=True).stdout.strip().splitlines()
bars = [(r.split("|")[0], *map(float, r.split("|")[1:5])) for r in q(f"select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close from v9_bars_5min_woodies "
        f"where symbol='MES' and (ts at time zone 'America/New_York')::date='{S}' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts")]
cand = None
if opt.get("cand") and os.path.exists(opt["cand"]):
    c = pd.read_csv(opt["cand"]); cand = c[c.session == S]
L = []
L.append(f"# סקירת-יום {S} — `{TAG}` (סוכן-T1, יום-אחר-יום)\n")
# S1 story
s1 = j.get("s1") or []
lock = next((x for x in s1 if x.get("ot_locked")), None); ib = next((x for x in s1 if x.get("ib_locked")), None)
trans = []; last = None
for x in s1:
    p = x.get("published")
    if p and p != last: trans.append(f"{x['il']} {p}"); last = p
if bars:
    o = bars[0][1]; hi = max(b[2] for b in bars); lo = min(b[3] for b in bars); ibh = max(b[2] for b in bars[:12]); ibl = min(b[3] for b in bars[:12])
    L.append(f"**הברים:** פתיחה {o} · IB {ibl}–{ibh} ({ibh-ibl:.2f}) · טווח {lo}–{hi} ({hi-lo:.2f}) · סגירה {bars[-1][4]} · {len(bars)} ברים\n")
L.append(f"**S1:** סוג-פתיחה נעול {lock['il'] if lock else '—'} = **{lock['ot_locked'] if lock else '—'}** · IB ננעל {ib['il'] if ib else '—'} · תוויות-יום: {' → '.join(trans) or '—'}\n")
pt = j.get("prev_tpo") or {}; pdc = j.get("pd_ctx") or {}
L.append(f"**ערך-האתמול שהעץ ראה:** POC {pt.get('poc')} · VAH {pt.get('vah')} · VAL {pt.get('val')} (רוחב {(pt.get('vah') or 0)-(pt.get('val') or 0):.2f}) · אתמול H/L/C {pdc.get('pd_high')}/{pdc.get('pd_low')}/{pdc.get('pd_close')}\n")
# candidates
L.append("\n## המועמדים (חיים-כשירים: עברו את העץ והשערים; shadow-only ו-NO_LABEL לא כאן)\n")
L.append("| שעה | תבנית | כיוון | 1·מה השוק מנסה (פתיחה/מבנה/יום) | 2·כמה טוב (ווליום/דלתא) | 3·איפה מול ערך | 4·מי שולט (סוג-כניסה/הטיה) | 5·איפה התזה מופרכת (סטופ · R) | העץ | מה קרה | תיוג |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|")
trades = {str(t.get("trade_id")): t for t in j.get("trades") or []}
n = 0
for r in j.get("routes") or []:
    res = r.get("result") or {}
    if r.get("blocked_by") or r.get("shadow_only") or not (res.get("live") or r.get("live_blocked_by") == "live_slot_occupied"): continue
    v = (r.get("tree_v3") or {}).get("vec") or {}; tv = r.get("tree_v3") or {}
    tid = str(((r.get("exec") or {}).get("live") or {}).get("trade_id")); t = trades.get(tid)
    entry, stop = r.get("entry"), r.get("stop"); R = abs(float(entry) - float(stop)) if entry and stop else None
    if t: what = f"**נלקח** → {t.get('outcome')} {t.get('pnl_usd'):+.2f}$ (יציאה {t.get('exit_il')}, MFE {t.get('mfe_pts')} נק׳)"
    else: what = "סלוט תפוס" if r.get("live_blocked_by") == "live_slot_occupied" else "—"
    cs = ""
    if cand is not None:
        m = cand[(cand.il == r["il"][:5]) & (cand.pattern == r.get("classification"))]
        if len(m): mm = m.iloc[0]; cs = f" · סימולציה: {mm.exit} {mm.pts:+.2f} נק׳, MFE {mm.mfe_r:.2f}R"
    L.append(f"| {r['il'][:5]} | {r.get('classification')} | {r.get('direction')} | {v.get('opening_type')} / {v.get('structure')} / {v.get('day_type')} ({v.get('phase')}) | {v.get('volume')} / {v.get('delta')} | {v.get('zone')} (אתמול: {v.get('prior_zone')}) | {v.get('kind')} / {v.get('rel_bias')} | {stop} · R {R:.2f} | {tv.get('leaf')} `{tv.get('id')}` | {what}{cs} | ☐ |")
    n += 1
L.append(f"\n{n} מועמדים חיים-כשירים · עסקאות {len(trades)} · P&L יום {sum(float(t.get('pnl_usd') or 0) for t in trades.values()):+.2f}$ ברוטו\n")
L.append("\n**תיוג (מייקל):** לכל שורה — תזה ✓/✗ · מיקום ✓/✗ · סטופ ✓/✗ · יעד ✓/✗ · ההחלטה של העץ ✓/✗. שורה עם ✗ = פריט-ביקורת → תיקון-שורש → ריצה-מחדש של היום.\n")
p = os.path.join(OUT, f"{S}.md"); open(p, "w", encoding="utf-8").write("\n".join(L)); print(p, n, "candidates")
