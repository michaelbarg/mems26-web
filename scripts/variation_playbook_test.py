#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""variation_playbook_test.py — branches for the days that make up most of the year: the day opens with
a drive (or extends out of the IB) and ends far from where it opened, yet the EOD label says
"Variation". Michael 24.09 08:00: "אתמול זה יום של 80 נקודות… רוב הימים בשנה הם וריאציה או כאלה
שמסתיימים ככה — עליך לדאוג שיהיו לנו ענפים כדי לדעת איך לסחור את זה… גם אם תהיה טעות המערכת תדע
לבצע תיקון ומקסום נקודות היום עם חוזה 1."

Three CAUSAL entry rules (no EOD label, no hindsight — every condition uses bars[:i+1]) and six
single-contract exit styles, replayed on every RTH session in the DB (≈45), one open trade per
rule per session, re-entry allowed after the trade resolves:

  DRIVE  — bar 3 closes beyond the opening range (bars 1–2) in the direction the market has
           been moving since the open (the engine's OPENING_DRIVE STRICT shape); entry at that
           close (what the engine fires at 16:45); stop = far side of the 3-bar range + 1 tick,
           cap 15 pts, skip if > 25 (T-428 structural stop).
  CONT   — after the IB (bar ≥ 12): price is extended beyond the IB in direction d (or the day
           opened with a drive in d), a pullback of ≥2 bars against d just ended, and this bar is
           a trigger bar with d (close in its extreme 30%); stop = pullback extreme + 1 tick,
           cap 1.5×ATR. This is the "with the extension after a pullback" row of the tree — and
           the SELF-CORRECTION: it fires whether or not the drive was taken.
  BREAK  — after the IB: with-day structure break (close beyond the last 5 bars in d) on a
           trigger bar, price already extended in d; stop = 1×ATR (min 5). The re-entry when the
           leg resumes without a clean pullback.

Exit styles (one contract, first touch on 5-min bars, EOD close, $5/pt, $1.30/side):
  T1 = 1.5R · T2 = 2.5R · T3 = 4R · TRAIL (chandelier 1×ATR after +1R) · BE (stop to entry
  after +1R, else T1) · TSTOP (T1, but scratch at the close of bar+6 if MFE < 0.5×ATR).
R = stop distance. Output: the table per rule × exit, the per-day-type split (EOD label — for
reading only), and the 23.09 trades explicitly.  python3 scripts/variation_playbook_test.py
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
ap.add_argument("--sessions", type=int, default=60)
ap.add_argument("--focus", default="2026-09-23")
ap.add_argument("--out", default=os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data"))
args = ap.parse_args()
TODAY = dt.datetime.now(IL).date().isoformat()
COMM = 2.60; TICK = 0.25

bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd on cd.ts=b.ts
 where b.symbol='MES' and b.ts >= now() - interval '90 days' and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""", {})
by_day = collections.defaultdict(list)
for b in bars: by_day[str(b["d"])].append(b)
alld = [d for d in sorted(by_day) if len(by_day[d]) >= 60]
days = alld[-args.sessions:]
dth = {str(r["date"]): r for r in read_all("select date, day_type, opening_type from v9_day_type_history where date >= :d", {"d": alld[0]})}

# ── exits ─────────────────────────────────────────────────────────────────────
def simulate(bs, i, short, stop_px, atr):
    """Entry at close of bar i. Returns pts per exit style + resolution index of the T1 style."""
    ep = bs[i]["c"]; R = abs(ep - stop_px)
    if R <= 0: return None
    tg = {"T1": 1.5 * R, "T2": 2.5 * R, "T3": 4.0 * R}
    res = {}; end_i = {}
    n = len(bs)
    for name, td in tg.items():
        out = None; ei = n - 1
        for j in range(i + 1, n):
            x = bs[j]; adv = (x["h"] - ep) if short else (ep - x["l"]); fav = (ep - x["l"]) if short else (x["h"] - ep)
            if adv >= R: out = -R; ei = j; break          # stop first (conservative: same bar → stop)
            if fav >= td: out = td; ei = j; break
        if out is None: out = (ep - bs[-1]["c"]) if short else (bs[-1]["c"] - ep)
        res[name] = out; end_i[name] = ei
    # TRAIL: chandelier 1×ATR from the extreme, armed after +1R; BE: stop→entry after +1R then T1; TSTOP
    mfe = 0.0; ext = ep; armed = False; trail = None; be = None; be_armed = False; ts_ = None; ei_tr = n - 1
    for j in range(i + 1, n):
        x = bs[j]; adv = (x["h"] - ep) if short else (ep - x["l"]); fav = (ep - x["l"]) if short else (x["h"] - ep)
        mfe = max(mfe, fav)
        if trail is None:
            if not armed:
                if adv >= R: trail = -R; ei_tr = j
                elif fav >= R: armed = True; ext = x["l"] if short else x["h"]
            if armed and trail is None:
                ext = min(ext, x["l"]) if short else max(ext, x["h"])
                tstop_px = ext + atr if short else ext - atr
                if (x["h"] >= tstop_px) if short else (x["l"] <= tstop_px): trail = (ep - tstop_px) if short else (tstop_px - ep); ei_tr = j
        if be is None:
            if be_armed and adv >= 0: be = 0.0
            elif adv >= R: be = -R
            elif fav >= tg["T1"]: be = tg["T1"]
            elif fav >= R: be_armed = True
        if ts_ is None:
            if adv >= R: ts_ = -R
            elif fav >= tg["T1"]: ts_ = tg["T1"]
            elif j - i >= 6 and mfe < 0.5 * atr: ts_ = (ep - x["c"]) if short else (x["c"] - ep)
        if trail is not None and be is not None and ts_ is not None: break
    eod = (ep - bs[-1]["c"]) if short else (bs[-1]["c"] - ep)
    res["TRAIL"] = trail if trail is not None else eod; res["BE"] = be if be is not None else eod; res["TSTOP"] = ts_ if ts_ is not None else eod
    # MAX = best excursion before the STOP would have been hit (full day)
    mx = 0.0
    for j in range(i + 1, n):
        x = bs[j]; adv = (x["h"] - ep) if short else (ep - x["l"]); fav = (ep - x["l"]) if short else (x["h"] - ep)
        mx = max(mx, fav)
        if adv >= R: break
    res["MAX"] = mx
    return dict(pts={k: round(v, 2) for k, v in res.items()}, R=round(R, 2), end_i=end_i["T1"], end_trail=ei_tr)

# ── rules ─────────────────────────────────────────────────────────────────────
def drive_signal(bs):
    """At the close of bar 2 (16:45:00): the engine's drive shape. Returns (short, stop_px) or None."""
    if len(bs) < 3: return None
    b0, b1, b2 = bs[0], bs[1], bs[2]
    or_hi, or_lo = max(b0["h"], b1["h"]), min(b0["l"], b1["l"])
    down = b2["c"] < or_lo and b1["c"] <= b0["c"] and b2["c"] < b2["o"]
    up = b2["c"] > or_hi and b1["c"] >= b0["c"] and b2["c"] > b2["o"]
    if not (down or up): return None
    short = down
    stop = (max(b0["h"], b1["h"], b2["h"]) + TICK) if short else (min(b0["l"], b1["l"], b2["l"]) - TICK)
    risk = abs(stop - b2["c"])
    if risk > 25: return None
    if risk > 15: stop = b2["c"] + 15 if short else b2["c"] - 15
    return short, stop

def drive_signal_lite(bs):
    if len(bs) < 3: return None
    b0, b1, b2 = bs[0], bs[1], bs[2]
    or_hi, or_lo = max(b0["h"], b1["h"]), min(b0["l"], b1["l"])
    down = b2["c"] < or_lo and b2["c"] < b2["o"]; up = b2["c"] > or_hi and b2["c"] > b2["o"]
    if not (down or up): return None
    short = down
    stop = (max(b0["h"], b1["h"], b2["h"]) + TICK) if short else (min(b0["l"], b1["l"], b2["l"]) - TICK)
    risk = abs(stop - b2["c"])
    if risk > 25: return None
    if risk > 15: stop = b2["c"] + 15 if short else b2["c"] - 15
    return 2, short, stop

def drive_signal_late(bs):
    """First bar k in 3..5 that closes beyond the 3-bar opening range, with bar k-1 also closed on that side of the OR midpoint."""
    if len(bs) < 6: return None
    or_hi = max(x["h"] for x in bs[:3]); or_lo = min(x["l"] for x in bs[:3]); mid = (or_hi + or_lo) / 2
    for k in range(3, 6):
        b = bs[k]; prev = bs[k - 1]
        down = b["c"] < or_lo and prev["c"] < mid and b["c"] < b["o"]; up = b["c"] > or_hi and prev["c"] > mid and b["c"] > b["o"]
        if down or up:
            short = down
            stop = (max(x["h"] for x in bs[:k + 1]) + TICK) if short else (min(x["l"] for x in bs[:k + 1]) - TICK)
            risk = abs(stop - b["c"])
            if risk > 25: return None
            if risk > 15: stop = b["c"] + 15 if short else b["c"] - 15
            return k, short, stop
    return None

def day_dir_so_far(bs, i, atr):
    mo = (bs[i]["c"] - bs[0]["o"]) / atr
    return "SHORT" if mo <= -0.5 else "LONG" if mo >= 0.5 else None

RULES = ["DRIVE", "DRIVE_LITE", "DRIVE_LATE", "CONT", "CONT_X", "CONT_1S", "BREAK"]
res = {r: [] for r in RULES}
for d in days:
    bs = by_day[d]; meta = dth.get(d, {}); dtype = meta.get("day_type") or "?"
    atr0 = oe.compute_atr(bs, min(20, len(bs) - 1)) or 6.0
    busy = {r: -1 for r in RULES}
    drive = drive_signal(bs)
    drive_dir = ("SHORT" if drive[0] else "LONG") if drive else None
    # DRIVE — one per day at bar 2
    if drive:
        short, stop = drive[0], drive[1]
        s = simulate(bs, 2, short, stop, atr0)
        if s: res["DRIVE"].append(dict(day=d, dt=dtype, t=str(bs[2]["t"])[:5], dir="SHORT" if short else "LONG", ep=bs[2]["c"], stop=stop, **s)); busy["DRIVE"] = s["end_i"]
    dl = drive_signal_lite(bs)
    if dl:
        k, short, stop = dl; s = simulate(bs, k, short, stop, atr0)
        if s: res["DRIVE_LITE"].append(dict(day=d, dt=dtype, t=str(bs[k]["t"])[:5], dir="SHORT" if short else "LONG", ep=bs[k]["c"], stop=stop, **s))
        if not drive_dir: drive_dir = "SHORT" if short else "LONG"
    dlt = drive_signal_late(bs)
    if dlt:
        k, short, stop = dlt; s = simulate(bs, k, short, stop, atr0)
        if s: res["DRIVE_LATE"].append(dict(day=d, dt=dtype, t=str(bs[k]["t"])[:5], dir="SHORT" if short else "LONG", ep=bs[k]["c"], stop=stop, **s))
        if not drive_dir: drive_dir = "SHORT" if short else "LONG"
    ib_h = max(x["h"] for x in bs[:12]); ib_l = min(x["l"] for x in bs[:12])
    for i in range(12, len(bs) - 3):
        atr = oe.compute_atr(bs, i) or atr0
        for short in (False, True):
            d_ = "SHORT" if short else "LONG"
            f = rl.features(bs, i, short, None, atr_fallback=atr0)
            if not f: continue
            ext_in_dir = (bs[i]["c"] < ib_l) if short else (bs[i]["c"] > ib_h)
            with_dir = ext_in_dir or (drive_dir == d_ and day_dir_so_far(bs, i, atr) == d_)
            ibw = max(ib_h - ib_l, 1.0)
            ses_lo = min(x["l"] for x in bs[:i + 1]); ses_hi = max(x["h"] for x in bs[:i + 1])
            real_ext = ((ib_l - ses_lo) >= 0.25 * ibw) if short else ((ses_hi - ib_h) >= 0.25 * ibw)
            with_dir_x = (real_ext and ext_in_dir) or (drive_dir == d_ and day_dir_so_far(bs, i, atr) == d_)
            other_ext = (ses_hi > ib_h + TICK) if short else (ses_lo < ib_l - TICK)
            one_sided = (ext_in_dir and not other_ext) or (drive_dir == d_ and day_dir_so_far(bs, i, atr) == d_ and not other_ext)
            # CONT: extended (or drive day) + pullback just ended + trigger bar with d
            if busy["CONT"] < i and with_dir and f["pullback_before"] and f["trigger_ok"] and f["range_ge_08atr"]:
                seq = bs[max(0, i - 4):i]
                stop = (max(x["h"] for x in seq) + TICK) if short else (min(x["l"] for x in seq) - TICK)
                risk = abs(stop - bs[i]["c"])
                if risk > 1.5 * atr: stop = bs[i]["c"] + 1.5 * atr if short else bs[i]["c"] - 1.5 * atr
                if risk >= 1.0:
                    s = simulate(bs, i, short, stop, atr)
                    if s: res["CONT"].append(dict(day=d, dt=dtype, t=str(bs[i]["t"])[:5], dir=d_, ep=bs[i]["c"], stop=round(stop, 2), **s)); busy["CONT"] = s["end_i"]
            if busy["CONT_X"] < i and with_dir_x and f["pullback_before"] and f["trigger_ok"] and f["range_ge_08atr"]:
                seq = bs[max(0, i - 4):i]
                stop = (max(x["h"] for x in seq) + TICK) if short else (min(x["l"] for x in seq) - TICK)
                risk = abs(stop - bs[i]["c"])
                if risk > 1.5 * atr: stop = bs[i]["c"] + 1.5 * atr if short else bs[i]["c"] - 1.5 * atr
                if risk >= 1.0:
                    s = simulate(bs, i, short, stop, atr)
                    if s: res["CONT_X"].append(dict(day=d, dt=dtype, t=str(bs[i]["t"])[:5], dir=d_, ep=bs[i]["c"], stop=round(stop, 2), **s)); busy["CONT_X"] = s["end_i"]
            if busy["CONT_1S"] < i and one_sided and f["pullback_before"] and f["trigger_ok"] and f["range_ge_08atr"]:
                seq = bs[max(0, i - 4):i]
                stop = (max(x["h"] for x in seq) + TICK) if short else (min(x["l"] for x in seq) - TICK)
                risk = abs(stop - bs[i]["c"])
                if risk > 1.5 * atr: stop = bs[i]["c"] + 1.5 * atr if short else bs[i]["c"] - 1.5 * atr
                if risk >= 1.0:
                    s = simulate(bs, i, short, stop, atr)
                    if s: res["CONT_1S"].append(dict(day=d, dt=dtype, t=str(bs[i]["t"])[:5], dir=d_, ep=bs[i]["c"], stop=round(stop, 2), i=i, **s)); busy["CONT_1S"] = s["end_i"]
            # BREAK: with-day structure break on a trigger bar, already extended in d
            if busy["BREAK"] < i and ext_in_dir and f["structure_break"] and f["trigger_ok"]:
                stop = bs[i]["c"] + max(5.0, atr) if short else bs[i]["c"] - max(5.0, atr)
                s = simulate(bs, i, short, stop, atr)
                if s: res["BREAK"].append(dict(day=d, dt=dtype, t=str(bs[i]["t"])[:5], dir=d_, ep=bs[i]["c"], stop=round(stop, 2), **s)); busy["BREAK"] = s["end_i"]

EXITS = ["T1", "T2", "T3", "TRAIL", "BE", "TSTOP"]
def summ(rows, ex):
    n = len(rows)
    if not n: return dict(n=0, win=0, usd=0.0, per=0.0, avg=0.0)
    p = [r["pts"][ex] for r in rows]; usd = sum(x * 5 - COMM for x in p)
    return dict(n=n, win=round(100 * sum(1 for x in p if x > 0) / n), usd=round(usd, 2), per=round(usd / n, 2), avg=round(sum(p) / n, 2))

out = {"generated": dt.datetime.now(IL).isoformat(timespec="minutes"), "sessions": days, "rules": {}, "focus": args.focus, "focus_trades": {}}
print(f"{'rule':6s} {'N':>4}  " + "  ".join(f"{e:>14s}" for e in EXITS) + "   (Σ$ · win%)")
for r in RULES:
    rows = res[r]; line = f"{r:6s} {len(rows):4d}  "
    out["rules"][r] = {"n": len(rows), "exits": {e: summ(rows, e) for e in EXITS}, "by_day_type": {}}
    for e in EXITS:
        s = summ(rows, e); line += f"  {s['usd']:+8.0f}$ {s['win']:3d}%"
    print(line)
    bydt = collections.defaultdict(list)
    for x in rows: bydt[x["dt"]].append(x)
    for k, v in sorted(bydt.items(), key=lambda kv: -len(kv[1])):
        best = max(EXITS, key=lambda e: summ(v, e)["usd"]); sb = summ(v, best)
        out["rules"][r]["by_day_type"][k] = {"n": len(v), "best_exit": best, "usd": sb["usd"], "win": sb["win"], "T1": summ(v, "T1")["usd"], "TRAIL": summ(v, "TRAIL")["usd"], "T2": summ(v, "T2")["usd"]}
        print(f"        {k:16s} n={len(v):3d}  T1 {summ(v,'T1')['usd']:+7.0f}$  T2 {summ(v,'T2')['usd']:+7.0f}$  TRAIL {summ(v,'TRAIL')['usd']:+7.0f}$  best {best} {sb['usd']:+.0f}$ ({sb['win']}%)")
    ft = [x for x in rows if x["day"] == args.focus]
    out["focus_trades"][r] = ft
    for x in ft:
        print(f"        ★ {args.focus} {x['t']} {x['dir']} @{x['ep']} stop {x['stop']} R={x['R']} → " + " · ".join(f"{e} {x['pts'][e]:+.2f}" for e in EXITS) + f" · MAX {x['pts']['MAX']:+.2f}")

# combined single-contract day P&L on the focus day and on every day, using per-rule best exit (chosen on the whole sample)
best_exit = {r: max(EXITS, key=lambda e: summ(res[r], e)["usd"]) for r in RULES}
out["best_exit"] = best_exit
def day_pnl(d, exits=None):
    tot = 0.0; n = 0
    for r in RULES:
        ex = (exits or best_exit)[r]
        for x in res[r]:
            if x["day"] == d: tot += x["pts"][ex] * 5 - COMM; n += 1
    return tot, n
per_day = {d: day_pnl(d) for d in days}
out["per_day"] = {d: {"usd": round(v[0], 2), "n": v[1], "dt": dth.get(d, {}).get("day_type") or "?"} for d, v in per_day.items()}
tot = sum(v[0] for v in per_day.values()); pos = sum(1 for v in per_day.values() if v[0] > 0); neg = sum(1 for v in per_day.values() if v[0] < 0)
print(f"\nbest exits {best_exit} · {len(days)} sessions Σ {tot:+.0f}$ · days + {pos} / − {neg} / flat {len(days)-pos-neg} · focus {args.focus}: {per_day.get(args.focus, (0,0))[0]:+.2f}$ over {per_day.get(args.focus, (0,0))[1]} trades")
byt = collections.defaultdict(list)
for d, v in per_day.items(): byt[dth.get(d, {}).get("day_type") or "?"].append(v[0])
for k, v in sorted(byt.items(), key=lambda kv: -len(kv[1])): print(f"   {k:16s} days={len(v):2d}  Σ {sum(v):+7.0f}$  avg/day {sum(v)/len(v):+6.1f}$")
out["by_day_type_days"] = {k: {"days": len(v), "usd": round(sum(v), 2), "avg": round(sum(v) / len(v), 2)} for k, v in byt.items()}
# ── the playbook as ONE account: one contract, one position at a time, DRIVE_LATE→T2 then CONT_1S→T1 ──
PB = {"DRIVE_LATE": "T2", "CONT_1S": "T1"}
def _end_index(bs, i, short, ep, R, ex):
    """bar index where the chosen exit style resolves (stop or target), EOD otherwise"""
    mult = {"T1": 1.5, "T2": 2.5, "T3": 4.0}.get(ex, 1.5)
    for j in range(i + 1, len(bs)):
        b = bs[j]; adv = (b["h"] - ep) if short else (ep - b["l"]); fav = (ep - b["l"]) if short else (b["h"] - ep)
        if adv >= R or fav >= mult * R: return j
    return len(bs) - 1
pb_days = {}
for d in days:
    bs = by_day[d]; taken = []; free_from = -1; cands = []
    for x in res["DRIVE_LATE"]:
        if x["day"] == d:
            k = next((j for j in range(3, 6) if str(bs[j]["t"])[:5] == x["t"]), 3); cands.append((k, "DRIVE_LATE", x))
    for x in res["CONT_1S"]:
        if x["day"] == d: cands.append((x["i"], "CONT_1S", x))
    cands.sort(key=lambda c: c[0])
    for i, rule, x in cands:
        if i <= free_from: continue
        ex = PB[rule]; pts = x["pts"][ex]
        taken.append(dict(rule=rule, t=x["t"], dir=x["dir"], ep=x["ep"], stop=x["stop"], exit=ex, pts=pts, usd=round(pts * 5 - COMM, 2)))
        free_from = _end_index(bs, i, x["dir"] == "SHORT", x["ep"], x["R"], ex)
    pb_days[d] = dict(dt=dth.get(d, {}).get("day_type") or "?", trades=taken, usd=round(sum(t["usd"] for t in taken), 2))
tot = sum(v["usd"] for v in pb_days.values()); pos = sum(1 for v in pb_days.values() if v["usd"] > 0); neg = sum(1 for v in pb_days.values() if v["usd"] < 0)
ntr = sum(len(v["trades"]) for v in pb_days.values()); nw = sum(1 for v in pb_days.values() for t in v["trades"] if t["pts"] > 0)
print(f"\nPLAYBOOK (one contract, one position at a time: DRIVE_LATE→T2, CONT_1S→T1): {len(days)} sessions · {ntr} trades · win {100*nw/max(ntr,1):.0f}% · Σ {tot:+.0f}$ · days + {pos} / − {neg} / flat {len(days)-pos-neg}")
byt = collections.defaultdict(list)
for d, v in pb_days.items(): byt[v["dt"]].append(v["usd"])
for k, v in sorted(byt.items(), key=lambda kv: -len(kv[1])): print(f"   {k:16s} days={len(v):2d}  Σ {sum(v):+7.0f}$  avg/day {sum(v)/len(v):+6.1f}$")
fd = pb_days.get(args.focus)
if fd:
    print(f"   ★ {args.focus} ({fd['dt']}): {fd['usd']:+.2f}$ — " + " · ".join(f"{t['rule']} {t['t']} {t['dir']} @{t['ep']} → {t['exit']} {t['pts']:+.2f} ({t['usd']:+.0f}$)" for t in fd["trades"]))
worst = sorted(pb_days.items(), key=lambda kv: kv[1]["usd"])[:3]; best = sorted(pb_days.items(), key=lambda kv: -kv[1]["usd"])[:3]
print("   worst:", ", ".join(f"{d} {v['usd']:+.0f}$ ({v['dt']}, {len(v['trades'])} tr)" for d, v in worst)); print("   best: ", ", ".join(f"{d} {v['usd']:+.0f}$ ({v['dt']}, {len(v['trades'])} tr)" for d, v in best))
out["playbook"] = dict(rules=PB, sessions=len(days), trades=ntr, win=round(100 * nw / max(ntr, 1)), usd=round(tot, 2), days_pos=pos, days_neg=neg,
                       by_day_type={k: dict(days=len(v), usd=round(sum(v), 2), avg=round(sum(v) / len(v), 2)) for k, v in byt.items()}, per_day=pb_days)
os.makedirs(args.out, exist_ok=True)
json.dump(out, open(os.path.join(args.out, "variation_playbook.json"), "w"), ensure_ascii=False, indent=0, default=str)
print(f"→ data/variation_playbook.json")
