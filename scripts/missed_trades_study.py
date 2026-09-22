#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""missed_trades_study.py — the moves we missed in the last N sessions, from candles /
volume / location — NOT from patterns (Michael 22.09 10:50: "תשלח סוכן על התנהלות 10 הימים
האחרונים ותיתן לי רשימה של עסקאות שפספסנו — לעבור על הנרות והווליום והמיקום, לאו דווקא על
תבניות, ולראות אם לכל סוג-יום ולסוג-עומק-מסחר יש דרך אחרת שכדאי היה לעבוד, ולייצר ענפים").

Per session: every zigzag leg ≥ max(10 pts, 1.5×ATR5) is a "move worth catching". For each
leg the IDEAL entry = the first bar in the leg's first half from which a trade (stop = that
bar's opposite extreme, ≤ 1 ATR) reaches 1.5×ATR before the stop. At that bar we record what
was VISIBLE (causal only): trigger-bar quality, range vs ATR, volume vs the last 5 bars,
delta vs session median, location vs the developing value area / IB / prior VA, bars from the
session extreme, with/against the day. Then what the SYSTEM did in the leg's window:
TOOK (live entry in the first 40% of the leg) · LATE · OPPOSITE · MISSED — and whether a
shadow producer fired within ±2 bars of the ideal entry (seen-but-blocked vs unseen).

Groups by day type × volume regime ("depth": session RTH volume vs the 10-session median:
HIGH ≥ 1.2×, LOW ≤ 0.8×) and prints the feature signature of the ideal entries per group —
the raw material for a branch in the tree grammar. Read-only. ~10 s.

  python3 scripts/missed_trades_study.py [--sessions 10] [--json out.json] [--md out.md]
"""
import os, sys, json, argparse, collections, statistics, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts")); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
import oracle_engine as oe
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem")

ap = argparse.ArgumentParser()
ap.add_argument("--sessions", type=int, default=10)
ap.add_argument("--json", default=os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data", "missed.json"))
ap.add_argument("--md", default=os.path.join(ROOT, "docs", "reports", "MISSED_TRADES_2026-09-22.md"))
args = ap.parse_args()

bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd on cd.ts=b.ts
 where b.symbol='MES' and b.ts >= now() - interval '40 days' and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""", {})
by_day = collections.defaultdict(list)
for b in bars:
    by_day[str(b["d"])].append(b)
alld = [d for d in sorted(by_day) if len(by_day[d]) >= 60]
days = alld[-args.sessions:]
prev_va = {}
for k, d in enumerate(alld):
    if k:
        pb = by_day[alld[k - 1]]; prev_va[d] = oe.compute_developing_va(pb, len(pb) - 1) if len(pb) > 5 else {}
dth = {str(r["date"]): r for r in read_all("select date, day_type, opening_type from v9_day_type_history where date >= :d", {"d": alld[0]})}
trades = read_all("""select id, mode, direction, entry_ts, entry_price, exit_ts, exit_price, exit_reason, pnl_usd, pattern_id_at_entry pat
  from v9_trades where entry_ts >= :since and mode in ('live','shadow') order by entry_ts""",
  {"since": dt.datetime.combine(dt.date.fromisoformat(days[0]), dt.time(0, 0), IL)})
tr_by_day = collections.defaultdict(list)
for t in trades:
    tr_by_day[t["entry_ts"].astimezone(IL).date().isoformat()].append(t)
sess_vol = {d: sum(float(b["v"] or 0) for b in by_day[d]) for d in alld}
med_vol = statistics.median([sess_vol[d] for d in alld[-10:]])

def zigzag(bs, thr):
    piv = []; mode = None; ext_i = 0; ext_p = bs[0]['c']
    for i, b in enumerate(bs):
        if mode is None:
            if b['h'] - ext_p >= thr: mode = 'up'; ext_i, ext_p = i, b['h']; piv.append((0, bs[0]['l'], 'L'))
            elif ext_p - b['l'] >= thr: mode = 'down'; ext_i, ext_p = i, b['l']; piv.append((0, bs[0]['h'], 'H'))
            continue
        if mode == 'up':
            if b['h'] > ext_p: ext_i, ext_p = i, b['h']
            elif ext_p - b['l'] >= thr: piv.append((ext_i, ext_p, 'H')); mode = 'down'; ext_i, ext_p = i, b['l']
        else:
            if b['l'] < ext_p: ext_i, ext_p = i, b['l']
            elif b['h'] - ext_p >= thr: piv.append((ext_i, ext_p, 'L')); mode = 'up'; ext_i, ext_p = i, b['h']
    piv.append((ext_i, ext_p, 'H' if mode == 'up' else 'L'))
    return piv

def features(bs, i, short, d):
    atr = oe.compute_atr(bs, i) or 0
    if atr <= 0: return None
    b = bs[i]
    deltas = [abs(float(x['delta'])) for x in bs[:i] if x['delta'] is not None]
    med_d = statistics.median(deltas) if len(deltas) > 5 else None
    dr = (float(b['delta']) / med_d) if (b['delta'] is not None and med_d) else None
    dev = oe.compute_developing_va(bs, i - 1) if i >= 4 else {}
    zone = oe.classify_zone_vs_developing_va(b['c'], dev) if dev else 'UNKNOWN'
    pv = prev_va.get(d) or {}
    near_prev = bool(pv) and (abs(b['c'] - pv.get('val', 1e9)) <= 0.5 * atr or abs(b['c'] - pv.get('vah', 1e9)) <= 0.5 * atr)
    hi_i = max(range(i + 1), key=lambda k: bs[k]['h']); lo_i = min(range(i + 1), key=lambda k: bs[k]['l'])
    bsh, bsl = i - hi_i, i - lo_i; at_extreme = (bsl == 0) if short else (bsh == 0)
    mo = (b['c'] - bs[0]['o']) / atr; with_day = (mo <= -0.5) if short else (mo >= 0.5)
    ib_h = max(x['h'] for x in bs[:12]); ib_l = min(x['l'] for x in bs[:12])
    ext = 'up' if b['c'] > ib_h else 'down' if b['c'] < ib_l else 'none'; with_ext = (ext == 'down' and short) or (ext == 'up' and not short)
    near_ib_edge = abs(b['c'] - ib_l) <= 0.5 * atr or abs(b['c'] - ib_h) <= 0.5 * atr
    rng = b['h'] - b['l']; cp = ((b['c'] - b['l']) / rng) if rng > 0 else 0.5
    trigger_ok = (cp >= 0.7) if not short else (cp <= 0.3); body = abs(b['c'] - b['o']) / rng if rng > 0 else 0
    vols = [float(x['v'] or 0) for x in bs[max(0, i - 5):i]]; vmed = statistics.median(vols) if vols else 0
    vr = (float(b['v']) / vmed) if vmed > 0 else None
    seq = bs[max(0, i - 4):i]; pull = sum(1 for x in seq[-3:] if ((x['c'] < x['o']) if not short else (x['c'] > x['o'])))
    prev5 = bs[max(0, i - 5):i]
    brk = ((b['c'] < min(x['l'] for x in prev5)) if short else (b['c'] > max(x['h'] for x in prev5))) if prev5 else False
    return dict(atr=round(atr, 2), hour=str(b['t'])[:5], ph=('A' if i < 3 else 'B' if i < 12 else 'C' if i < 54 else 'D'), zone=zone,
                near_prev_edge=near_prev, near_ib_edge=near_ib_edge, at_extreme=at_extreme, bars_from_extreme=(bsl if short else bsh),
                with_day=with_day, with_ext=with_ext, ext=ext, move_from_open_atr=round(mo, 2), trigger_ok=trigger_ok, body_ge_50=body >= 0.5,
                range_atr=round(rng / atr, 2), range_ge_08atr=rng >= 0.8 * atr, vol_trig=(vr is not None and vr >= 1.3),
                vol_ratio=round(vr, 2) if vr else None, delta_with=(dr is not None and ((dr <= -1) if short else (dr >= 1))),
                delta_ratio=round(dr, 2) if dr is not None else None, pullback_before=pull >= 2, structure_break=brk,
                ib_h=ib_h, ib_l=ib_l, poc=dev.get('poc') if dev else None, vah=dev.get('vah') if dev else None, val=dev.get('val') if dev else None)

ZONE_HEB = {"ABOVE_VA": "מעל הבטן", "BELOW_VA": "מתחת לבטן", "IN_VA": "בתוך הבטן", "AT_POC": "על ה-POC", "UNKNOWN": "?"}

def describe(f, short):
    p = []
    p.append("בר-טריגר חזק (סגירה ב-30% הקיצוניים)" if f["trigger_ok"] else "בר-טריגר חלש")
    p.append(f"טווח {f['range_atr']}×ATR" + (" ✓" if f["range_ge_08atr"] else ""))
    if f["vol_ratio"] is not None: p.append(f"ווליום ×{f['vol_ratio']} מול 5 הברים הקודמים" + (" ✓" if f["vol_trig"] else ""))
    if f["delta_ratio"] is not None: p.append(f"דלתא ×{f['delta_ratio']} מהחציון" + (" עם-הכיוון ✓" if f["delta_with"] else ""))
    p.append("שבירת-מבנה (סגירה מעבר ל-5 הברים הקודמים)" if f["structure_break"] else ("אחרי פולבק" if f["pullback_before"] else "המשך"))
    loc = ZONE_HEB.get(f["zone"], f["zone"])
    if f["near_ib_edge"]: loc += ", ליד קצה-IB"
    if f["near_prev_edge"]: loc += ", ליד ערך-אתמול"
    p.append("מיקום: " + loc + (f", {f['bars_from_extreme']} ברים מהקיצון" if f["bars_from_extreme"] else ", על הקיצון"))
    p.append(("עם" if f["with_day"] else "נגד/בלי") + " כיוון-היום" + (", עם ההרחבה" if f["with_ext"] else ""))
    return " · ".join(p)

rows = []; groups = collections.defaultdict(list)
for d in days:
    bs = by_day[d]
    atr0 = oe.compute_atr(bs, min(20, len(bs) - 1)) or 6.0
    piv = zigzag(bs, max(4.0, 1.0 * atr0))
    legs = []
    for (i0, p0, k0), (i1, p1, k1) in zip(piv, piv[1:]):
        if i1 > i0: legs.append(dict(i0=i0, i1=i1, pts=abs(p1 - p0), short=(p1 < p0), p0=p0, p1=p1))
    legs = [l for l in legs if l['pts'] >= max(12.0, 1.5 * atr0) and l['i0'] >= 2 and (l['i1'] - l['i0']) >= 3]
    legs = sorted(legs, key=lambda l: -l['pts'])[:5]; legs.sort(key=lambda l: l['i0'])
    vr = sess_vol[d] / med_vol if med_vol else 1.0
    depth = "HIGH" if vr >= 1.2 else "LOW" if vr <= 0.8 else "NORMAL"
    meta = dth.get(d, {}); dtype = (meta.get("day_type") or "?")
    live = [t for t in tr_by_day[d] if t["mode"] == "live"]; shadow = [t for t in tr_by_day[d] if t["mode"] == "shadow"]
    for leg in legs:
        short = leg['short']; dirn = "SHORT" if short else "LONG"
        t0 = bs[leg['i0']]['ts']; t1 = bs[leg['i1']]['ts']
        half = leg['i0'] + max(1, (leg['i1'] - leg['i0']) // 2)
        found = None
        for i in range(leg['i0'], half + 1):
            atr = oe.compute_atr(bs, i) or atr0
            b = bs[i]; ep = b['c']
            stop = (min(b['h'] + 0.25, ep + 1.0 * atr) if short else max(b['l'] - 0.25, ep - 1.0 * atr))
            target = ep - 1.5 * atr if short else ep + 1.5 * atr
            ok = False
            for x in bs[i + 1:leg['i1'] + 1]:
                hit_s = (x['h'] >= stop) if short else (x['l'] <= stop)
                hit_t = (x['l'] <= target) if short else (x['h'] >= target)
                if hit_s: break
                if hit_t: ok = True; break
            if ok:
                f = features(bs, i, short, d)
                if f:
                    captured = (ep - bs[leg['i1']]['l']) if short else (bs[leg['i1']]['h'] - ep)
                    found = dict(i=i, ep=ep, stop=round(abs(stop - ep), 2), captured=round(captured, 2), f=f)
                break
        # what the system did inside the leg window
        win_live = [t for t in live if t0 <= t["entry_ts"] <= t1]
        same = [t for t in win_live if t["direction"] == dirn]; opp = [t for t in win_live if t["direction"] != dirn]
        verdict = "MISSED" if found else "UNCATCHABLE"
        if same:
            first = min(same, key=lambda t: t["entry_ts"])
            frac = (first["entry_ts"] - t0).total_seconds() / max((t1 - t0).total_seconds(), 1)
            verdict = "TOOK" if frac <= 0.4 else "LATE"
        elif opp:
            verdict = "OPPOSITE"
        seen = []
        if found:
            ti = bs[found['i']]['ts']
            seen = sorted({t["pat"] for t in shadow if t["direction"] == dirn and abs((t["entry_ts"] - ti).total_seconds()) <= 12 * 60})
        rows.append(dict(day=d, day_type=dtype, opening=meta.get("opening_type") or "?", depth=depth, vol_ratio=round(vr, 2),
                         dir=dirn, start=str(bs[leg['i0']]['t'])[:5], end=str(bs[leg['i1']]['t'])[:5], pts=round(leg['pts'], 1),
                         from_px=leg['p0'], to_px=leg['p1'], verdict=verdict,
                         took=[dict(id=t["id"], pat=t["pat"], time=t["entry_ts"].astimezone(IL).strftime("%H:%M"), pnl=t["pnl_usd"]) for t in same + opp],
                         ideal=(dict(time=found['f']['hour'], price=found['ep'], stop=found['stop'], captured=found['captured'],
                                     desc=describe(found['f'], short), seen_by=seen, **{k: found['f'][k] for k in
                                     ('zone', 'trigger_ok', 'range_atr', 'vol_ratio', 'delta_ratio', 'structure_break', 'pullback_before',
                                      'with_day', 'with_ext', 'at_extreme', 'bars_from_extreme', 'near_ib_edge', 'near_prev_edge', 'ph')}) if found else None)))
        groups[(dtype, depth)].append(rows[-1])

# ── group signatures → branch proposals ──────────────────────────────────────
FLAGS = ['with_day', 'with_ext', 'at_extreme', 'near_ib_edge', 'near_prev_edge', 'trigger_ok', 'structure_break', 'pullback_before']
def sig(rs):
    ideal = [r["ideal"] for r in rs if r["ideal"]]
    if not ideal: return {}
    out = {f: round(100 * sum(1 for x in ideal if x.get(f)) / len(ideal)) for f in FLAGS}
    out["range_ge_08atr"] = round(100 * sum(1 for x in ideal if x["range_atr"] >= 0.8) / len(ideal))
    out["vol_trig"] = round(100 * sum(1 for x in ideal if (x["vol_ratio"] or 0) >= 1.3) / len(ideal))
    out["delta_with"] = round(100 * sum(1 for x in ideal if x["delta_ratio"] is not None and abs(x["delta_ratio"]) >= 1) / len(ideal))
    out["n"] = len(ideal)
    out["zones"] = dict(collections.Counter(ZONE_HEB.get(x["zone"], x["zone"]) for x in ideal).most_common(3))
    out["phases"] = dict(collections.Counter(x["ph"] for x in ideal).most_common(4))
    return out

summary = []
for (dtype, depth), rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    missed = [r for r in rs if r["verdict"] in ("MISSED", "OPPOSITE")]
    s = sig(rs)
    strong = [k for k in ('with_day', 'trigger_ok', 'range_ge_08atr', 'vol_trig', 'delta_with', 'structure_break', 'with_ext', 'at_extreme', 'near_ib_edge') if s.get(k, 0) >= 70]
    summary.append(dict(day_type=dtype, depth=depth, legs=len(rs), missed=len(missed), missed_pts=round(sum(r["pts"] for r in missed), 1),
                        took=sum(1 for r in rs if r["verdict"] == "TOOK"), late=sum(1 for r in rs if r["verdict"] == "LATE"),
                        opposite=sum(1 for r in rs if r["verdict"] == "OPPOSITE"), signature=s, strong=strong,
                        sessions=sorted({r["day"] for r in rs})))

os.makedirs(os.path.dirname(args.json), exist_ok=True)
json.dump(dict(generated=dt.datetime.now(IL).isoformat(timespec="minutes"), sessions=days, med_vol=med_vol,
               legs=rows, groups=summary), open(args.json, "w"), ensure_ascii=False, default=str, indent=0)

# ── markdown report ───────────────────────────────────────────────────────────
DEPTH_HEB = {"HIGH": "עומק גבוה (ווליום ≥1.2× החציון)", "NORMAL": "עומק רגיל", "LOW": "עומק נמוך (≤0.8×)"}
V_HEB = {"TOOK": "✅ נלקחה", "LATE": "🕒 נלקחה מאוחר", "OPPOSITE": "❌ נכנסנו הפוך", "MISSED": "⭕ פוספסה", "UNCATCHABLE": "⚪ לא ניתנת-לתפיסה (בלי בר-אישור עם סטופ ≤1 ATR)"}
md = [f"# העסקאות שפספסנו — {len(days)} סשנים אחרונים ({days[0]} … {days[-1]})", "",
      "**מקור:** מייקל 22.09 10:50 — *\"רשימה של עסקאות שפספסנו — לעבור על הנרות, הווליום והמיקום, לאו דווקא על תבניות; לכל סוג-יום ולסוג-עומק-מסחר דרך אחרת; לייצר ענפים\"*.",
      "**שיטה:** כל מהלך ≥ max(10 נק', 1.5×ATR) בזיגזג של הסשן; הכניסה-האידיאלית = הבר הראשון בחצי הראשון של המהלך שממנו עסקה (סטופ ≤1 ATR מאחורי הבר) מגיעה ל-1.5×ATR לפני הסטופ; מה שנראה בבר הזה — סיבתי בלבד. \"עומק\" = ווליום-הסשן מול חציון 10 הסשנים.", "",
      f"סה\"כ מהלכים: {len(rows)} · נלקחו {sum(1 for r in rows if r['verdict']=='TOOK')} · מאוחר {sum(1 for r in rows if r['verdict']=='LATE')} · הפוך {sum(1 for r in rows if r['verdict']=='OPPOSITE')} · **פוספסו {sum(1 for r in rows if r['verdict']=='MISSED')} ({sum(r['pts'] for r in rows if r['verdict']=='MISSED'):.0f} נק')**", "",
      "## 1 · לפי סוג-יום × עומק — מה משותף לכניסות-האידיאליות (⇒ הענף)", "",
      "| סוג-יום | עומק | מהלכים | פוספסו (נק') | חתימה (% מהכניסות-האידיאליות) | ענף מוצע |", "|---|---|---|---|---|---|"]
for g in summary:
    s = g["signature"]; sgn = ", ".join(f"{k} {v}%" for k, v in s.items() if isinstance(v, int) and k not in ("n",)) if s else "—"
    branch = ("עם-היום + טריגר-חזק + טווח ≥0.8ATR" if all(k in g["strong"] for k in ("with_day", "trigger_ok", "range_ge_08atr")) else
              "שבירת-מבנה + ווליום" if all(k in g["strong"] for k in ("structure_break", "vol_trig")) else
              " + ".join(g["strong"]) if g["strong"] else "אין חתימה חזקה (N קטן)")
    md.append(f"| {g['day_type']} | {DEPTH_HEB[g['depth']]} | {g['legs']} | {g['missed']} ({g['missed_pts']}) | N={s.get('n',0)} · {sgn} · אזורים {s.get('zones',{})} · שלבים {s.get('phases',{})} | {branch} |")
md += ["", "## 2 · הרשימה — יום אחרי יום", ""]
for d in days:
    rs = [r for r in rows if r["day"] == d]
    if not rs: continue
    r0 = rs[0]
    md.append(f"### {d} — {r0['day_type']} · פתיחה {r0['opening']} · {DEPTH_HEB[r0['depth']]} (×{r0['vol_ratio']})")
    for r in rs:
        line = f"- **{r['start']}→{r['end']} {r['dir']} {r['pts']} נק'** ({r['from_px']:.2f}→{r['to_px']:.2f}) — {V_HEB[r['verdict']]}"
        if r["took"]: line += " · " + ", ".join(f"#{t['id']} {t['pat']} {t['time']} ({t['pnl'] if t['pnl'] is not None else '—'}$)" for t in r["took"])
        md.append(line)
        if r["ideal"]:
            i = r["ideal"]
            md.append(f"  - כניסה-אידיאלית **{i['time']} @{i['price']:.2f}** (סטופ {i['stop']} נק', היה נותן {i['captured']} נק'): {i['desc']}")
            md.append(f"  - מפיקי-צל שראו את זה (±10 דק'): {', '.join(i['seen_by']) if i['seen_by'] else '**אף אחד**'}")
        else:
            md.append("  - לא נמצאה כניסה מחזיקה בחצי הראשון (המהלך נסע בלי לתת בר-אישור עם סטופ ≤1 ATR)")
    md.append("")
os.makedirs(os.path.dirname(args.md), exist_ok=True)
open(args.md, "w", encoding="utf-8").write("\n".join(md))
print(f"legs {len(rows)} · missed {sum(1 for r in rows if r['verdict']=='MISSED')} · json → {args.json} · md → {args.md}")
for g in summary:
    print(f"  {g['day_type']:16s} {g['depth']:6s} legs={g['legs']:2d} missed={g['missed']:2d} ({g['missed_pts']} pts) took={g['took']} late={g['late']} opp={g['opposite']} strong={g['strong']}")
