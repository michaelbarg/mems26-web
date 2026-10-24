#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-643 - per-trade Dalton card DATA (Michael 24.10: "נתייחס לכל עסקה בודדת וננהל אותה היטב").

Read-only. For each trade: execution - the day's context (yesterday's RTH value by TPO + volume POC, yesterday's
range/close, overnight range, today's open and where it opened, IB) - the references AHEAD and BEHIND at the entry
(computed from bars closed before the entry: no look-ahead) - bars from 8 before the signal bar to the exit (+4) -
the path to EOD: MFE/MAE in R to the exit and to the close, which references were reached before the original stop.

  python3 harness_out/t643/cards.py 3164 3220 ... > harness_out/t643/cards_demo.txt
  python3 harness_out/t643/cards.py --json harness_out/t643/cards_demo.json 3164 3220 ...
"""
import os, sys, json, argparse, collections, datetime as dt
ROOT = "/Users/michael/Downloads/mems26_web_git"
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem"); ET = ZoneInfo("America/New_York")
TICK = 0.25; PT = 5.0

ap = argparse.ArgumentParser()
ap.add_argument("ids", nargs="+", type=int)
ap.add_argument("--json", default=None)
ap.add_argument("--no-bars", action="store_true")
ap.add_argument("--bars-before", type=int, default=8)
ap.add_argument("--bars-after", type=int, default=None, help="cap the bars printed after the entry bar")
ap.add_argument("--sim", action="store_true", help="M-REF management simulation per trade (T-643 phase 2)")
ap.add_argument("--rules", action="store_true", help="entry-rule candidates R1/R2/R3 per trade (T-643)")
args = ap.parse_args()

trades = read_all("""select id, mode, direction, entry_ts, entry_price, stop, t1, t2, t3, t1_hit_ts, t2_hit_ts, t3_hit_ts,
  stop_hit_ts, exit_ts, exit_price, exit_reason, pnl_usd, pnl_r, quality, pattern_id_at_entry pat, day_type_at_entry dt_entry,
  firing_system from v9_trades where id = any(:ids) order by entry_ts""", {"ids": args.ids})
if not trades: sys.exit("no trades")

d_first = min(t["entry_ts"] for t in trades).astimezone(ET).date() - dt.timedelta(days=12)
d_last = max(t["entry_ts"] for t in trades).astimezone(ET).date() + dt.timedelta(days=1)
bars = read_all("""select b.ts, b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd
 on cd.ts = b.ts where b.symbol = 'MES' and b.ts >= :a and b.ts < :b order by b.ts""",
 {"a": dt.datetime.combine(d_first, dt.time(0, 0), ET), "b": dt.datetime.combine(d_last, dt.time(23, 59), ET)})
for b in bars:
    for k in ("o", "h", "l", "c"): b[k] = float(b[k])
    b["v"] = float(b["v"] or 0); b["delta"] = (float(b["delta"]) if b["delta"] is not None else None)
    e = b["ts"].astimezone(ET); b["et"] = e; b["il"] = b["ts"].astimezone(IL)

rth = collections.defaultdict(list)
for b in bars:
    t = b["et"].time()
    if dt.time(9, 30) <= t < dt.time(16, 0): rth[b["et"].date()].append(b)
days = sorted(d for d in rth if len(rth[d]) >= 60)

def prev_day(d):
    p = [x for x in days if x < d]
    return p[-1] if p else None

def eth_bars(d):
    p = prev_day(d)
    if not p: return []
    a = dt.datetime.combine(p, dt.time(18, 0), ET); z = dt.datetime.combine(d, dt.time(9, 30), ET)
    return [b for b in bars if a <= b["et"] < z]

def ticks(lo, hi):
    n = int(round((hi - lo) / TICK))
    return [round((lo + k * TICK) / TICK) * TICK for k in range(n + 1)]

def value_area(counts, frac=0.70):
    if not counts: return None
    px = sorted(counts); tot = sum(counts.values())
    mid = (px[0] + px[-1]) / 2.0
    poc = max(px, key=lambda p: (counts[p], -abs(p - mid)))
    i = j = px.index(poc); acc = counts[poc]
    while acc < frac * tot and (i > 0 or j < len(px) - 1):
        up = sum(counts[px[k]] for k in range(j + 1, min(j + 3, len(px))))
        dn = sum(counts[px[k]] for k in range(max(i - 2, 0), i))
        if up >= dn and j < len(px) - 1:
            k2 = min(j + 2, len(px) - 1); acc += up; j = k2
        elif i > 0:
            k2 = max(i - 2, 0); acc += dn; i = k2
        else:
            k2 = min(j + 2, len(px) - 1); acc += up; j = k2
    return {"poc": poc, "val": px[i], "vah": px[j]}

def tpo_profile(bs):
    """30-min periods from the first bar: each price touched in a period = 1 TPO."""
    if not bs: return {}
    t0 = bs[0]["et"]; per = collections.defaultdict(list)
    for b in bs: per[int((b["et"] - t0).total_seconds() // 1800)].append(b)
    cnt = collections.Counter()
    for k, pb in per.items():
        for p in ticks(min(x["l"] for x in pb), max(x["h"] for x in pb)): cnt[p] += 1
    return cnt

def vol_profile(bs):
    cnt = collections.Counter()
    for b in bs:
        tk = ticks(b["l"], b["h"])
        for p in tk: cnt[p] += b["v"] / len(tk)
    return cnt

def day_ctx(d):
    bs = rth[d]; p = prev_day(d); pb = rth.get(p) or []
    c = {"day": str(d), "prev": str(p) if p else None}
    if pb:
        va = value_area(tpo_profile(pb)); vva = value_area(vol_profile(pb))
        c.update(p_vah=va["vah"], p_val=va["val"], p_poc=va["poc"], p_vpoc=vva["poc"], p_vvah=vva["vah"], p_vval=vva["val"],
                 p_hi=max(x["h"] for x in pb), p_lo=min(x["l"] for x in pb), p_close=pb[-1]["c"])
    eb = eth_bars(d)
    if eb: c.update(on_hi=max(x["h"] for x in eb), on_lo=min(x["l"] for x in eb))
    o = bs[0]["o"]; c["open"] = o
    if pb:
        if c["p_val"] <= o <= c["p_vah"]: c["open_loc"] = "בתוך הערך של אתמול"
        elif c["p_lo"] <= o <= c["p_hi"]: c["open_loc"] = "מחוץ לערך, בתוך הטווח של אתמול (%s)" % ("מעל VAH" if o > c["p_vah"] else "מתחת VAL")
        else: c["open_loc"] = "מחוץ לטווח של אתמול (%s)" % ("מעל השיא" if o > c["p_hi"] else "מתחת לשפל")
    ib = bs[:12]; c["ib_hi"] = max(x["h"] for x in ib); c["ib_lo"] = min(x["l"] for x in ib)
    c["hi"] = max(x["h"] for x in bs); c["lo"] = min(x["l"] for x in bs); c["close"] = bs[-1]["c"]
    fva = value_area(tpo_profile(bs)); c.update(vah=fva["vah"], val=fva["val"], poc=fva["poc"])
    c["ext_up"] = c["hi"] - c["ib_hi"]; c["ext_dn"] = c["ib_lo"] - c["lo"]
    return c

def f(x, n=2):
    if x is None: return "—"
    try: return ("%%.%df" % n) % float(x)
    except Exception: return str(x)

def hm(ts):
    return ts.astimezone(IL).strftime("%H:%M") if ts else "—"

# ── M-REF: management by references (T-643 phase 2) ─────────────────────────────────────────────────────────────
# My per-trade read (phase 1): the trade's relation to the day's initiative decides the allocation (Dalton נ1).
CLS = {3515: "balance", 3582: "balance", 3763: "counter", 3799: "counter", 3544: "with", 3784: "with", 3749: "with"}
# Dalton stop for the CORRECT entries whose stop sat inside the noise (beyond the defining level + 2 ticks).
STOP_FIX = {3544: 7709.75, 3763: 7685.50, 3799: 7685.50, 3749: 7745.00}
def sim_ref(bs, eb, short, ep, s0, ahead, ctr, cls, after="structure", time_budget=True):
    sg = -1 if short else 1; tk = TICK
    R = abs(ep - s0)
    if not R or not ctr: return None
    tg = []; last = None
    for n, p, dd in ahead:
        need = 0.8 * R if last is None else last + 0.5 * R
        if dd >= need:
            tg.append((n, p - sg * tk, dd)); last = dd
        if len(tg) == 3: break
    qty = int(ctr)
    if cls == "counter": alloc = [qty]
    elif cls == "balance": alloc = [qty - qty // 2, qty // 2] if qty > 1 else [qty]
    else: alloc = {1: [1], 2: [1, 1], 3: [1, 1, 1], 4: [2, 1, 1], 5: [2, 2, 1]}.get(qty, [qty])
    legs = [[q, (tg[k][1] if k < len(tg) else None)] for k, q in enumerate(alloc)]
    if cls == "with" and len(legs) >= 3:
        legs[-1][1] = None   # Dalton נ1/נ5: with the initiative the runner is not capped — it trails on structure after T2
    stop = s0; pnl = 0.0; open_q = qty; hit = []; mfe = 0.0; ev = []
    path = [b for b in bs[eb:] if b["et"].time() < dt.time(15, 55)]
    for k, b in enumerate(path):
        if (short and b["h"] >= stop) or ((not short) and b["l"] <= stop):
            pnl += sg * (stop - ep) * open_q; ev.append("%s סטופ %s×%d" % (b["il"].strftime("%H:%M"), f(stop), open_q)); open_q = 0; break
        if k > 0:
            for leg in legs:
                if leg[0] > 0 and leg[1] is not None and ((short and b["l"] <= leg[1]) or ((not short) and b["h"] >= leg[1])):
                    pnl += sg * (leg[1] - ep) * leg[0]; ev.append("%s יעד %s×%d" % (b["il"].strftime("%H:%M"), f(leg[1]), leg[0]))
                    open_q -= leg[0]; leg[0] = 0; hit.append(leg[1])
                    if after == "be":
                        if len(hit) == 1: stop = ep + sg * tk
                    else:
                        seg = path[:k + 1] if len(hit) == 1 else path[max(0, k - 2):k + 1]
                        sx = (max(x["h"] for x in seg) + tk) if short else (min(x["l"] for x in seg) - tk)
                        stop = min(stop, sx) if short else max(stop, sx)
            if open_q == 0: break
        fav = (ep - b["l"]) if short else (b["h"] - ep)
        mfe = max(mfe, fav)
        if time_budget and not hit and k == 4 and mfe < 0.5 * R:
            pnl += sg * (b["c"] - ep) * open_q; ev.append("%s זמן %s×%d" % (b["il"].strftime("%H:%M"), f(b["c"]), open_q)); open_q = 0; break
        if len(hit) >= 2 and open_q > 0 and after != "be":
            seg = path[max(0, k - 2):k + 1]
            sx = (max(x["h"] for x in seg) + tk) if short else (min(x["l"] for x in seg) - tk)
            stop = min(stop, sx) if short else max(stop, sx)
    if open_q > 0:
        c = path[-1]["c"]; pnl += sg * (c - ep) * open_q; ev.append("סוף-יום %s×%d" % (f(c), open_q))
    return dict(pnl=pnl * PT, R=R, tg=tg, alloc=alloc, ev=ev)
SIM = []; RULES = []

out = []; js = []; shown_days = set()
for t in trades:
    d = t["entry_ts"].astimezone(ET).date(); bs = rth.get(d) or []
    if len(bs) < 20: out.append("## #%d — no bars for %s" % (t["id"], d)); continue
    C = day_ctx(d)
    if d not in shown_days:
        shown_days.add(d)
        out.append("=" * 100)
        out.append("# DAY %s (IL) · prev %s" % (C["day"], C["prev"]))
        out.append("אתמול: VA(TPO) %s–%s POC %s · vPOC %s (vVA %s–%s) · H/L %s/%s · close %s | ON H/L %s/%s | open %s — %s" % (
            f(C.get("p_val")), f(C.get("p_vah")), f(C.get("p_poc")), f(C.get("p_vpoc")), f(C.get("p_vval")), f(C.get("p_vvah")),
            f(C.get("p_hi")), f(C.get("p_lo")), f(C.get("p_close")), f(C.get("on_hi")), f(C.get("on_lo")), f(C["open"]), C.get("open_loc", "—")))
        out.append("היום: IB %s–%s (%s נק׳) · H/L %s/%s · close %s · הרחבה למעלה %s / למטה %s · VA סופי(TPO) %s–%s POC %s" % (
            f(C["ib_lo"]), f(C["ib_hi"]), f(C["ib_hi"] - C["ib_lo"]), f(C["hi"]), f(C["lo"]), f(C["close"]), f(C["ext_up"]), f(C["ext_dn"]),
            f(C["val"]), f(C["vah"]), f(C["poc"])))
        out.append("30 דק׳ (IL  O  H  L  C  V  Δ):")
        t0 = bs[0]["et"]; per = collections.defaultdict(list)
        for b in bs: per[int((b["et"] - t0).total_seconds() // 1800)].append(b)
        for k in sorted(per):
            pb = per[k]; dl = [x["delta"] for x in pb if x["delta"] is not None]
            out.append("  %s  %s %s %s %s  %6d  %s" % (pb[0]["il"].strftime("%H:%M"), f(pb[0]["o"]), f(max(x["h"] for x in pb)), f(min(x["l"] for x in pb)),
                       f(pb[-1]["c"]), int(sum(x["v"] for x in pb)), f(sum(dl), 0) if dl else "—"))
    ets = t["entry_ts"]; short = t["direction"] == "SHORT"; sg = -1 if short else 1
    i = max((k for k, b in enumerate(bs) if b["ts"] + dt.timedelta(minutes=5) <= ets), default=0)
    eb = i + 1  # the entry bar
    q = t["quality"] or {}; md = q.get("metadata") or {}; sit = md.get("situation") or {}
    ep = float(t["entry_price"]); s0 = md.get("stop_initial") or q.get("entry_stop") or t["stop"]; s0 = float(s0) if s0 is not None else None
    R = abs(ep - s0) if s0 else None
    ctr = q.get("contracts") or md.get("contracts")
    # references at the entry (bars 0..i are closed)
    seen = bs[:i + 1]
    refs = []
    def add(name, px):
        if px is not None: refs.append((name, float(px)))
    for k, nm in (("p_vah", "VAH-אתמול"), ("p_val", "VAL-אתמול"), ("p_poc", "POC-אתמול"), ("p_hi", "שיא-אתמול"), ("p_lo", "שפל-אתמול"),
                  ("p_close", "סגירת-אתמול"), ("on_hi", "שיא-לילה"), ("on_lo", "שפל-לילה")):
        add(nm, C.get(k))
    add("פתיחה", C["open"])
    # older sessions (2-5 back): H/L/POC/VA edges - the references beyond yesterday's range
    pp = prev_day(d); back = []
    for _ in range(4):
        pp = prev_day(pp) if pp else None
        if pp: back.append(pp)
    for od in back:
        ob = rth.get(od) or []
        if not ob: continue
        ova = value_area(tpo_profile(ob)); tag = od.strftime("%d.%m")
        add("שיא-%s" % tag, max(x["h"] for x in ob)); add("שפל-%s" % tag, min(x["l"] for x in ob))
        add("POC-%s" % tag, ova["poc"]); add("VAH-%s" % tag, ova["vah"]); add("VAL-%s" % tag, ova["val"])
    if i >= 11:
        add("IBH", C["ib_hi"]); add("IBL", C["ib_lo"])
    add("שיא-הסשן", max(x["h"] for x in seen)); add("שפל-הסשן", min(x["l"] for x in seen))
    hr = bs[max(0, i - 11):i + 1]
    add("שיא-שעה", max(x["h"] for x in hr)); add("שפל-שעה", min(x["l"] for x in hr))
    if len(seen) >= 6:
        dva = value_area(tpo_profile(seen))
        add("POC-מתפתח", dva["poc"]); add("VAH-מתפתח", dva["vah"]); add("VAL-מתפתח", dva["val"])
    else:
        dva = {}
    def dedupe(lst):
        o = []
        for n, p, dd in lst:
            if o and abs(o[-1][2] - dd) <= 0.75 and not n.startswith(("VAH-אתמול", "VAL-אתמול", "POC-אתמול", "IB", "שיא-הסשן", "שפל-הסשן")):
                continue
            o.append((n, p, dd))
        return o
    ahead = dedupe(sorted([(n, p, sg * (p - ep)) for n, p in refs if sg * (p - ep) >= TICK], key=lambda x: x[2]))
    behind = dedupe(sorted([(n, p, -sg * (p - ep)) for n, p in refs if -sg * (p - ep) >= 0], key=lambda x: x[2]))
    # path
    path = bs[eb:]
    xts = t["exit_ts"]
    stop_bar = None; mfe = mae = 0.0; mfe_t = None; reach = {}
    mfe_x = mae_x = 0.0
    for b in path:
        fav = (ep - b["l"]) if short else (b["h"] - ep); adv = (b["h"] - ep) if short else (ep - b["l"])
        if xts is None or b["ts"] < xts:
            mfe_x = max(mfe_x, fav); mae_x = max(mae_x, adv)
        if stop_bar is None:
            for n, p, dist in ahead:
                if n not in reach and fav >= dist: reach[n] = b
            if R and adv >= R - 1e-9: stop_bar = b
        if fav > mfe: mfe = fav; mfe_t = b
        mae = max(mae, adv)
    ml = read_all("select ts, action, value from v9_trade_management_log where trade_id = :id order by ts", {"id": t["id"]})
    tz = lambda x: (abs(float(x) - ep) / R) if (x is not None and R) else None
    L = []
    L.append("-" * 100)
    L.append("## #%d · %s %s IL · %s %s · %s · %sc · %s @%s · P&L $%s" % (t["id"], C["day"], hm(ets), t["pat"], t["direction"], t["mode"],
             ctr or "?", t["exit_reason"], f(t["exit_price"]), f(t["pnl_usd"])))
    L.append("כניסה %s · סטופ %s (R=%s נק׳) · T1 %s (%sR) · T2 %s (%sR) · T3 %s (%sR) · יציאה %s %s" % (
        f(ep), f(s0), f(R), f(t["t1"]), f(tz(t["t1"]), 1), f(t["t2"]), f(tz(t["t2"]), 1), f(t["t3"]), f(tz(t["t3"]), 1), hm(t["exit_ts"]), f(t["exit_price"])))
    L.append("מערכת: פתיחה %s · יום %s (conf %s) · שלב %s · אזור %s · dir_hint %s · הרחבה %s %s · IB נעול %s" % (
        sit.get("opening_type"), sit.get("day_type") or t["dt_entry"], f(sit.get("day_type_conf")), sit.get("phase"), sit.get("zone"),
        sit.get("dir_hint"), sit.get("extension"), f(sit.get("extension_pts"), 1), sit.get("ib_locked")))
    L.append("מיקום מול אתמול: כניסה %s · VA-אתמול %s–%s · %s" % (f(ep), f(C.get("p_val")), f(C.get("p_vah")),
             ("מעל VAH-אתמול" if ep > (C.get("p_vah") or 1e9) else "מתחת VAL-אתמול" if ep < (C.get("p_val") or -1e9) else "בתוך הערך של אתמול")))
    if dva: L.append("ערך מתפתח בכניסה (TPO): %s–%s POC %s · IB %s" % (f(dva["val"]), f(dva["vah"]), f(dva["poc"]),
             ("%s–%s" % (f(C["ib_lo"]), f(C["ib_hi"]))) if i >= 11 else "עדיין נבנה"))
    L.append("לפנינו: " + " · ".join("%s %s (%s נק׳=%sR)" % (n, f(p), f(dd), f(dd / R, 2) if R else "—") for n, p, dd in ahead[:6]))
    inside = [(n, p, dd) for n, p, dd in behind if R and dd < R]
    if s0 and inside:
        nb = inside[-1]; stop_note = "הסטופ %s = %s נק׳ מעבר ל-%s %s (הרמה האחרונה בתוך הסיכון)" % (f(s0), f(R - nb[2]), nb[0], f(nb[1]))
    elif s0:
        stop_note = "הסטופ %s לפני כל רמה מאחור (הקרובה: %s)" % (f(s0), ("%s %s, %s נק׳" % (behind[0][0], f(behind[0][1]), f(behind[0][2]))) if behind else "אין")
    else:
        stop_note = ""
    L.append("מאחורינו: " + " · ".join("%s %s (%s נק׳)" % (n, f(p), f(dd)) for n, p, dd in behind[:5]) + " | " + stop_note)
    L.append("מסלול: MFE עד היציאה %s נק׳ (%sR) · MAE %s (%sR) | עד הסגירה: MFE %s (%sR) ב-%s · MAE %s (%sR) | סטופ-מקורי נגע: %s" % (
        f(mfe_x), f(mfe_x / R, 2) if R else "—", f(mae_x), f(mae_x / R, 2) if R else "—", f(mfe), f(mfe / R, 2) if R else "—",
        mfe_t["il"].strftime("%H:%M") if mfe_t else "—", f(mae), f(mae / R, 2) if R else "—", stop_bar["il"].strftime("%H:%M") if stop_bar else "לא"))
    L.append("ייחוסים שהושגו לפני הסטופ: " + (" · ".join("%s ב-%s" % (n, reach[n]["il"].strftime("%H:%M")) for n, p, dd in ahead if n in reach) or "אף אחד"))
    L.append("ניהול: " + " | ".join("%s %s %s" % (hm(r["ts"]), r["action"], json.dumps(r["value"], ensure_ascii=False)[:70]) for r in ml if r["action"] not in ("TARGET_REALISM",)) )
    if not args.no_bars:
        a = max(0, i - args.bars_before)
        xi = next((k for k, b in enumerate(bs) if xts and b["ts"] <= xts < b["ts"] + dt.timedelta(minutes=5)), len(bs) - 1)
        z = min(len(bs), max(xi, eb) + 5)
        if args.bars_after is not None: z = min(z, eb + args.bars_after + 1)
        L.append("ברים (IL  O  H  L  C  V  Δ  ±fav/adv מהכניסה):")
        for k in range(a, z):
            b = bs[k]; mark = "◀סיגנל" if k == i else ("▶כניסה" if k == eb else ("✖יציאה" if k == xi else ""))
            fav = (b["h"] - ep) if not short else (ep - b["l"]); adv = (ep - b["l"]) if not short else (b["h"] - ep)
            L.append("  %s %s %s %s %s %6d %6s  %s" % (b["il"].strftime("%H:%M"), f(b["o"]), f(b["h"]), f(b["l"]), f(b["c"]), int(b["v"]),
                     f(b["delta"], 0), mark + ((" fav%+.2f adv%+.2f" % (fav, adv)) if k >= eb else "")))
        if z < len(bs):
            rest = bs[z:]
            hi = max(rest, key=lambda x: x["h"]); lo = min(rest, key=lambda x: x["l"])
            L.append("  אחר כך עד הסגירה: שיא %s ב-%s · שפל %s ב-%s · סגירה %s" % (f(hi["h"]), hi["il"].strftime("%H:%M"), f(lo["l"]), lo["il"].strftime("%H:%M"), f(bs[-1]["c"])))
    if args.rules:
        sb = bs[i]; atr_i = sum(max(bs[k]["h"] - bs[k]["l"], abs(bs[k]["h"] - bs[k - 1]["c"]), abs(bs[k]["l"] - bs[k - 1]["c"])) for k in range(max(1, i - 13), i + 1)) / max(1, min(14, i))
        # R1 accepted extension against the trade: >=3 of the last 6 closes beyond the IB edge on the stop side, delta with the extension
        r1 = None
        if i >= 11:
            last6 = bs[max(12, i - 5):i + 1]
            if short:
                beyond = [x for x in last6 if x["c"] > C["ib_hi"]]
            else:
                beyond = [x for x in last6 if x["c"] < C["ib_lo"]]
            dsum = sum((x["delta"] or 0) for x in beyond)
            ok_delta = (dsum > 0) if short else (dsum < 0)
            r1 = (len(beyond), int(dsum), len(beyond) >= 3 and ok_delta)
        # R2 position in the last-hour range, measured from the stop-side extreme (0 = at the stop-side edge, 1 = far edge)
        h12 = bs[max(0, i - 11):i + 1]; hh = max(x["h"] for x in h12); ll = min(x["l"] for x in h12); rg = max(hh - ll, TICK)
        pos = ((hh - ep) / rg) if short else ((ep - ll) / rg)
        tested = (sb["h"] >= hh - 0.5) if short else (sb["l"] <= ll + 0.5)
        # R3 opening chase: first 60 min, entry within 0.25 ATR of the session extreme in the trade direction, after a push bar
        sess = bs[:i + 1]; ext_hi = max(x["h"] for x in sess); ext_lo = min(x["l"] for x in sess)
        push = (sb["o"] - sb["c"]) if short else (sb["c"] - sb["o"])
        at_ext = (ep - ext_lo <= 0.4 * atr_i) if short else (ext_hi - ep <= 0.4 * atr_i)
        r3 = i < 12 and at_ext
        RULES.append((t["id"], r1, round(pos, 2), tested, r3, round(push / atr_i, 2) if atr_i else None, round(atr_i, 2)))
    if args.sim:
        cls = CLS.get(t["id"], "with")
        sfix = STOP_FIX.get(t["id"], s0)
        # references ahead re-measured against the stop actually simulated (R may change with the Dalton stop)
        r_orig = sim_ref(bs, eb, short, ep, s0, ahead, ctr, cls, "structure", False)
        r_be = sim_ref(bs, eb, short, ep, s0, ahead, ctr, cls, "be", False)
        r_fix = sim_ref(bs, eb, short, ep, sfix, ahead, ctr, cls, "structure", False) if sfix != s0 else None
        r_nt = sim_ref(bs, eb, short, ep, sfix, ahead, ctr, cls, "structure", True)
        SIM.append((t, cls, r_orig, r_be, r_fix, r_nt))
    out.append("\n".join(L))
    js.append(dict(id=t["id"], day=C["day"], time=hm(ets), pat=t["pat"], dir=t["direction"], ep=ep, stop0=s0, R=R, ctr=ctr,
                   t1=t["t1"], t2=t["t2"], t3=t["t3"], exit=t["exit_reason"], exit_px=t["exit_price"], pnl=t["pnl_usd"],
                   mfe_x=mfe_x, mae_x=mae_x, mfe=mfe, mae=mae, stop_touched=stop_bar is not None,
                   ahead=[(n, p, dd) for n, p, dd in ahead[:6]], behind=[(n, p, dd) for n, p, dd in behind[:5]],
                   reached=[n for n, p, dd in ahead if n in reach], ctx={k: v for k, v in C.items()}))
if args.rules:
    print("id | R1 (closes beyond IB on stop side, Σdelta, accepted?) | R2 pos-from-stop-edge | signal bar tested edge | R3 opening chase | push/ATR | ATR")
    for r in RULES: print(" | ".join(str(x) for x in r))
elif not args.sim:
    print("\n".join(out))
if args.sim:
    print("| # | סוג | חוזים | בפועל $ | M-REF מבנה $ | M-REF BE $ | סטופ-דלתון $ | +תקציב-זמן $ | T1/T2/T3 (R) | אירועים (מבנה) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    tot = collections.Counter()
    for t, cls, a, b, c, nt in SIM:
        if not a: continue
        tot["act"] += float(t["pnl_usd"] or 0); tot["a"] += a["pnl"]; tot["b"] += b["pnl"]; tot["c"] += (c or a)["pnl"]; tot["nt"] += nt["pnl"]
        print("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (t["id"], cls, "-".join(str(x) for x in a["alloc"]), f(t["pnl_usd"]), f(a["pnl"]), f(b["pnl"]),
              f(c["pnl"]) if c else "=", f(nt["pnl"]), " / ".join("%s %s (%.1f)" % (n, f(p), dd / a["R"]) for n, p, dd in a["tg"]), " · ".join(a["ev"]) + ((" ‖ סטופ-דלתון R=%s: %s · %s" % (f(c["R"]), " / ".join("%s %s" % (n, f(p)) for n, p, dd in c["tg"]), " · ".join(c["ev"]))) if c else "")))
    print("| Σ | | | %s | %s | %s | %s | %s | | |" % (f(tot["act"]), f(tot["a"]), f(tot["b"]), f(tot["c"]), f(tot["nt"])))
if args.json:
    json.dump(js, open(args.json, "w"), ensure_ascii=False, indent=1, default=str)
