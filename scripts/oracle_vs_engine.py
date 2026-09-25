#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""oracle_vs_engine.py — every session, the full-vision path vs what the engine did at those moments
(Michael 25.09 01:00, Q5: "הדמיה של כל יום — המסלול ואיפה היה צריך להיכנס … כדי שהעץ יתאים את עצמו").

For each clean session (the 58 of the replay baseline):
  1. FULL VISION  — review_lib: zigzag legs worth catching (≥ max(12, 1.5×ATR) pts) and the IDEAL causal entry
     of each (first confirmable bar: a 1×ATR stop behind it holds until 1.5×ATR).
  2. THE ENGINE   — the real engine's routes from the baseline replay (harness_out/t458/r15_*.json on drive sessions,
     branch1_*.json otherwise): every producer candidate with its final gate outcome.
  3. THE JOIN     — for each ideal entry: candidates in the same direction within ±2 bars (±10 min) →
     status LIVE (fired) · SHADOW_ONLY (a shadow-only producer saw it) · BLOCKED:<gate> · NO_PRODUCER.
  4. THE TABLE    — ideal $ (1.5×ATR target, 1 contract, $2.60 RT) by status, by gate, by producer, by day type, by phase:
     which gate costs how much, which signature has no producer, and how much of the full-vision ceiling
     the engine already captures. This is the learning loop's input: the row/gate that loses money is what changes.

Outputs: docs/reports/ORACLE_VS_ENGINE_<date>.md · render_mobile_relay/static/docs/data/oracle_vs_engine.json
"""
import collections, datetime as dt, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts")); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
import oracle_engine as oe
import review_lib as rl
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem"); COMM = 2.60; TODAY = dt.datetime.now(IL).date().isoformat()
B = os.path.join(ROOT, "harness_out", "t458")

sessions = sorted(os.path.basename(p)[8:18] for p in glob.glob(os.path.join(B, "branch1_*.json")))
bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd on cd.ts=b.ts
 where b.symbol='MES' and (b.ts at time zone 'Asia/Jerusalem')::date >= :a and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""", {"a": sessions[0]})
by_day = collections.defaultdict(list)
for b in bars: by_day[str(b["d"])].append(b)
dth = {str(r["date"]): r for r in read_all("select date, day_type, opening_type from v9_day_type_history where date >= :d", {"d": sessions[0]})}

def phase_of(i): return "A" if i < 3 else "B" if i < 12 else "C" if i < 54 else "D"

entries = []  # one row per ideal entry
for d in sessions:
    bs = by_day.get(d) or []
    if len(bs) < 60: continue
    p = os.path.join(B, f"r15_{d}.json")
    if not os.path.exists(p): p = os.path.join(B, f"branch1_{d}.json")
    j = json.load(open(p)); routes = j.get("routes") or []
    live_trades = j.get("trades") or []
    atr0 = oe.compute_atr(bs, min(20, len(bs) - 1)) or 6.0
    legs = rl.legs_of(bs, atr0)
    dtype = (dth.get(d, {}) or {}).get("day_type") or "?"
    for leg in legs:
        ie = rl.ideal_entry(bs, leg, atr0)
        if not ie: continue
        i = ie["i"]; short = leg["short"]; dirn = "SHORT" if short else "LONG"
        t_il = str(bs[i]["t"])[:5]
        ideal_pts = 1.5 * ie["atr"]; ideal_usd = ideal_pts * 5 - COMM
        # candidates within ±2 bars in the same direction; route 'il' is HH:MM:SS of the decision (bar close + 5 min)
        def bar_idx(il):
            hh, mm = int(il[:2]), int(il[3:5]); mins = (hh - 16) * 60 + mm - 30
            return int(mins // 5) - 1   # decision at the close of bar k happens at bar k+1's open
        cands = [r for r in routes if r.get("direction") == dirn and abs(bar_idx(r.get("il", "00:00")) - i) <= 2]
        status, gate, prod = "NO_PRODUCER", "", ""
        if cands:
            def rank(r):
                res = r.get("result") or {}
                if res.get("live"): return 0
                if r.get("live_blocked_by") == "live_slot_occupied": return 1
                if res.get("shadow") and not r.get("blocked_by"): return 2
                return 3
            best = min(cands, key=rank)
            k = rank(best)
            if k == 0: status = "LIVE"
            elif k == 1: status = "SLOT_OCCUPIED"
            elif k == 2: status = "SHADOW_ONLY"
            else: status = "BLOCKED"; gate = (best.get("blocked_by") or best.get("live_blocked_by") or "?").split(" ")[0]
            prod = best.get("classification") or ""
        # what the live trades in that window actually made (if any)
        got = 0.0
        for t in live_trades:
            fi = (t.get("fired_il") or "")[:5]
            if fi and abs(bar_idx(fi) - i) <= 2 and t.get("direction") == dirn:
                got += float(t.get("pnl_usd") or 0) - COMM
        entries.append(dict(d=d, dt=dtype, il=t_il, i=i, phase=phase_of(i), dir=dirn, ep=ie["ep"], atr=ie["atr"], leg_pts=round(leg["pts"], 2),
                            captured=ie["captured"], ideal_usd=round(ideal_usd, 1), status=status, gate=gate, producer=prod, got=round(got, 1),
                            f={k: ie["f"].get(k) for k in ("zone", "with_day", "with_ext", "ext", "pullback_before", "structure_break", "trigger_ok", "range_ge_08atr", "vol_trig", "near_ib_edge")}))

def agg(key):
    m = collections.defaultdict(lambda: dict(n=0, ideal=0.0, got=0.0))
    for e in entries:
        k = key(e); m[k]["n"] += 1; m[k]["ideal"] += e["ideal_usd"]; m[k]["got"] += e["got"]
    return m
tot_ideal = sum(e["ideal_usd"] for e in entries); tot_got = sum(e["got"] for e in entries)
by_status = agg(lambda e: e["status"] + (":" + e["gate"] if e["status"] == "BLOCKED" else ""))
by_gate = agg(lambda e: e["gate"] if e["status"] == "BLOCKED" else ("—" + e["status"]))
by_prod = agg(lambda e: e["producer"] or "—")
by_dt = agg(lambda e: e["dt"]); by_phase = agg(lambda e: e["phase"]); by_dir = agg(lambda e: e["dir"])
by_sig = agg(lambda e: ("with_ext" if e["f"]["with_ext"] else "no_ext") + "·" + ("pullback" if e["f"]["pullback_before"] else "break" if e["f"]["structure_break"] else "cont") + "·" + str(e["f"]["zone"]))

L = []; A = L.append
A(f"# הראייה-המלאה מול המנוע — כל הימים ({TODAY})")
A("")
A("**מייקל 25.09:** *\"הדמיה של כל יום — המסלול ואיפה היה צריך להיכנס בכל יום שצברנו, כדי להביא מקסימום רווח, ובהתאם לזה העץ יתאים את עצמו\"*.")
A("")
A(f"**{len(sessions)} סשנים · {len(entries)} כניסות-אידיאליות** (כל מהלך ≥ max(12, 1.5×ATR) נק׳; הכניסה האידיאלית = הבר הראשון שממנו סטופ של 1×ATR מחזיק עד 1.5×ATR). "
  f"תקרת-הראייה-המלאה במודל-ההערכה הקבוע (יעד 1.5×ATR, חוזה 1, אחרי עמלות): **{tot_ideal:+,.0f}$**. מה שהמנוע של היום לקח באותם חלונות: **{tot_got:+,.0f}$** ({100*tot_got/max(tot_ideal,1):.0f}%).")
A("")
A("## 1 · מה קרה לכל כניסה אידיאלית במנוע")
A("")
A("| סטטוס | כניסות | Σ אידיאלי | Σ שנלקח | % מהאידיאלי |")
A("|---|---|---|---|---|")
for k, v in sorted(by_status.items(), key=lambda kv: -kv[1]["ideal"]):
    A(f"| {k} | {v['n']} | {v['ideal']:+,.0f}$ | {v['got']:+,.0f}$ | {100*v['got']/max(v['ideal'],1):.0f}% |")
A("")
A("## 2 · השערים — כמה כל שער עלה (כניסות אידיאליות שנחסמו בו)")
A("")
A("| שער | כניסות | Σ אידיאלי שנחסם |")
A("|---|---|---|")
for k, v in sorted(by_gate.items(), key=lambda kv: -kv[1]["ideal"]):
    if not k.startswith("—"): A(f"| {k} | {v['n']} | {v['ideal']:+,.0f}$ |")
A("")
A("## 3 · המפיקים — מי ראה את הכניסות האידיאליות")
A("")
A("| מפיק | כניסות | Σ אידיאלי | Σ שנלקח |")
A("|---|---|---|---|")
for k, v in sorted(by_prod.items(), key=lambda kv: -kv[1]["n"])[:20]:
    A(f"| {k} | {v['n']} | {v['ideal']:+,.0f}$ | {v['got']:+,.0f}$ |")
A("")
A("## 4 · לפי סוג-יום · שלב · כיוון · חתימה")
A("")
A("| חתך | כניסות | Σ אידיאלי | Σ שנלקח | % |")
A("|---|---|---|---|---|")
for title, m in (("סוג-יום", by_dt), ("שלב", by_phase), ("כיוון", by_dir), ("חתימה (הרחבה·כניסה·מיקום)", by_sig)):
    for k, v in sorted(m.items(), key=lambda kv: -kv[1]["ideal"])[:12]:
        A(f"| {title}: {k} | {v['n']} | {v['ideal']:+,.0f}$ | {v['got']:+,.0f}$ | {100*v['got']/max(v['ideal'],1):.0f}% |")
A("")
A("## 5 · יום-אחר-יום — המסלול והכניסות האידיאליות")
A("")
A("| יום | סוג-יום | כניסה אידיאלית | מהלך | אידיאלי | המנוע | שער/מפיק | נלקח |")
A("|---|---|---|---|---|---|---|---|")
for e in entries:
    A(f"| {e['d']} | {e['dt']} | {e['il']} {e['dir']} @{e['ep']:g} ({e['phase']}) | {e['leg_pts']:g} נק׳ | {e['ideal_usd']:+.0f}$ | {e['status']} | {e['gate'] or e['producer']} | {e['got']:+.0f}$ |")
md = "\n".join(L)
mp = os.path.join(ROOT, "docs", "reports", f"ORACLE_VS_ENGINE_{TODAY}.md"); open(mp, "w", encoding="utf-8").write(md)
od = os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data"); os.makedirs(od, exist_ok=True)
json.dump(dict(generated=dt.datetime.now(IL).isoformat(timespec="minutes"), sessions=len(sessions), entries=entries, by_status=by_status, by_gate=by_gate,
               by_producer=by_prod, by_day_type=by_dt, by_phase=by_phase, by_signature=by_sig, tot_ideal=tot_ideal, tot_got=tot_got),
          open(os.path.join(od, "oracle_vs_engine.json"), "w"), ensure_ascii=False, default=str)
print(f"sessions={len(sessions)} entries={len(entries)} ideal Σ{tot_ideal:+.0f}$ got Σ{tot_got:+.0f}$ ({100*tot_got/max(tot_ideal,1):.0f}%)")
for k, v in sorted(by_status.items(), key=lambda kv: -kv[1]["ideal"])[:12]:
    print(f"  {k:40s} n={v['n']:3d} ideal {v['ideal']:+8.0f}$ got {v['got']:+7.0f}$")
print("→", mp)
