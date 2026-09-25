#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""swing_turn_test.py — can a CAUSAL rule pick the rotation swings the full-vision oracle found?
(25.09: 151 of the 246 ideal entries on 58 sessions — +$7,972 of +$12,654 — are "against the day so far,
no IB extension": rotation swings of 12–30 pts, mostly 17:00–21:00, mostly inside/at value.)

The oracle's ideal entry is itself causal: after ≥2 of the last 3 bars went the other way (a pullback),
a trigger bar closes in the new direction (extreme 30% of its range, range ≥ 0.8×ATR). Applied to EVERY bar
this fires often; the question is which conditioning keeps the edge. Every candidate: entry = trigger close,
stop = extreme of the 4 bars before + tick (cap 1.5×ATR, min 1 pt), target 1.5R, first touch, EOD close,
one contract, $2.60 RT — the fixed evaluation model. Candidates scored independently (rule quality) AND as
one-position-at-a-time (playbook), per session.

  python3 scripts/swing_turn_test.py            # 58 sessions of the replay baseline
"""
import collections, datetime as dt, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts")); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
import oracle_engine as oe
import review_lib as rl
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem"); COMM = 2.60; TICK = 0.25; TODAY = dt.datetime.now(IL).date().isoformat()
B = os.path.join(ROOT, "harness_out", "t458")
sessions = sorted(os.path.basename(p)[8:18] for p in glob.glob(os.path.join(B, "branch1_*.json")))
bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd on cd.ts=b.ts
 where b.symbol='MES' and (b.ts at time zone 'Asia/Jerusalem')::date >= :a and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""", {"a": sessions[0]})
by_day = collections.defaultdict(list)
for b in bars: by_day[str(b["d"])].append(b)
dth = {str(r["date"]): r for r in read_all("select date, day_type from v9_day_type_history where date >= :d", {"d": sessions[0]})}

def sim(bs, i, short, ep, stop):
    R = abs(ep - stop); tgt = 1.5 * R
    for j in range(i + 1, len(bs)):
        b = bs[j]
        hit_stop = (b["h"] >= stop) if short else (b["l"] <= stop)
        fav = (ep - b["l"]) if short else (b["h"] - ep)
        if hit_stop: return -R, j
        if fav >= tgt: return tgt, j
    return ((ep - bs[-1]["c"]) if short else (bs[-1]["c"] - ep)), len(bs) - 1

cands = []
for d in sessions:
    bs = by_day.get(d) or []
    if len(bs) < 60: continue
    atr0 = oe.compute_atr(bs, min(20, len(bs) - 1)) or 6.0
    dtype = (dth.get(d, {}) or {}).get("day_type") or "?"
    for i in range(3, len(bs) - 3):
        for short in (True, False):
            f = rl.features(bs, i, short, None, atr_fallback=atr0)
            if not f or not (f["trigger_ok"] and f["range_ge_08atr"] and f["pullback_before"]): continue
            atr = f["atr"]
            seq = bs[max(0, i - 4):i]
            stop = (max(x["h"] for x in seq) + TICK) if short else (min(x["l"] for x in seq) - TICK)
            risk = abs(stop - bs[i]["c"])
            if risk > 1.5 * atr: stop = bs[i]["c"] + 1.5 * atr if short else bs[i]["c"] - 1.5 * atr; risk = 1.5 * atr
            if risk < 1.0: continue
            pts, end_i = sim(bs, i, short, bs[i]["c"], stop)
            cands.append(dict(d=d, dt=dtype, i=i, il=str(bs[i]["t"])[:5], dir="SHORT" if short else "LONG", ep=bs[i]["c"], R=round(risk, 2), pts=round(pts, 2), usd=round(pts * 5 - COMM, 1), end_i=end_i,
                              ph=f["ph"], zone=f["zone"], with_day=f["with_day"], with_ext=f["with_ext"], at_extreme=f["at_extreme"], bars_from_extreme=f["bars_from_extreme"],
                              vol_trig=f["vol_trig"], delta_with=f["delta_with"], near_ib=f["near_ib_edge"], structure_break=f["structure_break"], hour=str(bs[i]["t"])[:2]))
def summ(rows):
    n = len(rows); w = sum(1 for r in rows if r["pts"] > 0); u = sum(r["usd"] for r in rows)
    return n, (100 * w / n if n else 0), u, (u / n if n else 0)
def playbook(rows):
    """one position at a time per session, candidates in time order"""
    tot = 0.0; n = 0; w = 0; byd = collections.defaultdict(float)
    for d in sessions:
        busy = -1
        for r in sorted([r for r in rows if r["d"] == d], key=lambda r: r["i"]):
            if r["i"] <= busy: continue
            busy = r["end_i"]; tot += r["usd"]; n += 1; w += r["pts"] > 0; byd[d] += r["usd"]
    pos = sum(1 for v in byd.values() if v > 0); neg = sum(1 for v in byd.values() if v < 0)
    return n, (100 * w / n if n else 0), tot, pos, neg
variants = collections.OrderedDict([
    ("ALL swing turns", lambda r: True),
    ("phase C only", lambda r: r["ph"] == "C"),
    ("phase C+D", lambda r: r["ph"] in ("C", "D")),
    ("17:00-21:00", lambda r: "17" <= r["hour"] <= "20"),
    ("against the day so far", lambda r: not r["with_day"]),
    ("with the day so far", lambda r: r["with_day"]),
    ("at value edge (ABOVE/BELOW_VA)", lambda r: r["zone"] in ("ABOVE_VA", "BELOW_VA")),
    ("inside value (IN_VA)", lambda r: r["zone"] == "IN_VA"),
    ("at the session extreme (bars_from_extreme≤1)", lambda r: r["bars_from_extreme"] <= 1),
    ("near IB edge", lambda r: r["near_ib"]),
    ("volume trigger ≥1.3×", lambda r: r["vol_trig"]),
    ("delta with", lambda r: r["delta_with"]),
    ("against day · phase C · vol_trig", lambda r: (not r["with_day"]) and r["ph"] == "C" and r["vol_trig"]),
    ("against day · at extreme · phase C", lambda r: (not r["with_day"]) and r["bars_from_extreme"] <= 1 and r["ph"] == "C"),
    ("against day · value edge · phase C", lambda r: (not r["with_day"]) and r["zone"] in ("ABOVE_VA", "BELOW_VA") and r["ph"] == "C"),
    ("with day · with_ext (the CONT rule)", lambda r: r["with_day"] and r["with_ext"]),
    ("Variation days only", lambda r: r["dt"] == "Variation"),
    ("Normal/Neutral days only", lambda r: r["dt"] in ("Normal", "Neutral_Center", "Neutral_Extreme")),
])
L = []; A = L.append
A(f"# מבחן סיבוב-הנדנדה (swing-turn) — הכלל הסיבתי של הכניסה האידיאלית על כל הברים, {len(sessions)} סשנים ({TODAY})")
A("")
A("**הרקע:** 151 מ-246 הכניסות האידיאליות (+7,972$ מ-+12,654$) הן סיבובים נגד כיוון-היום בלי הרחבת-IB, רובם 17:00–21:00. הכלל: ≥2 מ-3 הברים הקודמים נגד, בר-טריגר בכיוון החדש (סגירה ב-30% הקיצוניים, טווח ≥0.8×ATR), סטופ = קיצון 4 הברים הקודמים + טיק (תקרה 1.5×ATR), יעד 1.5R. מודל-הערכה קבוע, חוזה 1, אחרי עמלות.")
A("")
A("| התניה | מועמדים | win% | Σ$ בלתי-תלוי | ממוצע | פלייבוק (פוזיציה אחת): עסקאות · win% · Σ$ · ימים +/− |")
A("|---|---|---|---|---|---|")
out = {}
for name, fn in variants.items():
    rows = [r for r in cands if fn(r)]
    n, w, u, avg = summ(rows); pn, pw, pu, pp, pneg = playbook(rows)
    out[name] = dict(n=n, win=round(w), usd=round(u, 1), avg=round(avg, 2), pb_n=pn, pb_win=round(pw), pb_usd=round(pu, 1), pb_pos=pp, pb_neg=pneg)
    A(f"| {name} | {n} | {w:.0f}% | {u:+,.0f}$ | {avg:+.1f}$ | {pn} · {pw:.0f}% · **{pu:+,.0f}$** · {pp}/{pneg} |")
    print(f"{name:44s} n={n:5d} win {w:3.0f}% Σ{u:+8.0f}$ avg {avg:+5.1f}$ | playbook n={pn:4d} win {pw:3.0f}% Σ{pu:+8.0f}$ days +{pp}/−{pneg}")
A("")
A("**קריאה:** התניה שמשאירה מספר חיובי גם בעמודת-הפלייבוק (פוזיציה אחת בכל רגע) היא מועמדת למפיק — ואז הרנס יום-כולל במנוע מכריע (הלקח של 24.09: מספר-מועמדים ≠ מספר-יום).")
mp = os.path.join(ROOT, "docs", "reports", f"SWING_TURN_{TODAY}.md"); open(mp, "w", encoding="utf-8").write("\n".join(L))
od = os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data"); os.makedirs(od, exist_ok=True)
json.dump(dict(generated=dt.datetime.now(IL).isoformat(timespec="minutes"), sessions=len(sessions), candidates=len(cands), variants=out), open(os.path.join(od, "swing_turn.json"), "w"), ensure_ascii=False)
print("→", mp)
