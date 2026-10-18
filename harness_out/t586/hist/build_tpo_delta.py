#!/usr/bin/env python3
"""T-586 · step 4 — from the merged 5-min series build what the live export feeds the harness with:
  tpo_history.csv  — 30-min TPO snapshots per RTH session (ET): 09:30:05 = the GLOBEX profile, then 10:00…15:30 (+5 s)
                     with the developing RTH profile (POC / VAH / VAL by TPO count, 70 % value area, Dalton pairs, 0.25 levels)
                     and the IB (first 60 min; first 30 min at the 10:00 snapshot) — calibrated vs the live rows of 08.10.
  tpo_sessions.csv — per trading date: CASH (full RTH) and GLOBEX (18:00 prev → 09:30) summaries.
  delta.csv        — per RTH 5-min bar: delta = ask − bid volume, cumulative within the RTH session.
usage: build_tpo_delta.py <merged.csv> <outdir>"""
import sys, os, collections, datetime, pandas as pd, numpy as np
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York"); INC = 0.25
src, outdir = sys.argv[1], sys.argv[2]
m = pd.read_csv(src)
t = pd.to_datetime(m["ts"], unit="s", utc=True).dt.tz_convert(ET)
m["et"] = t; m["tm"] = t.dt.hour * 60 + t.dt.minute
# trading date: RTH bars → their ET date; overnight bars (>= 18:00 ET) → next trading date (weekends: Sunday 18:00 → Monday)
def tdate(row_et, tm):
    d = row_et.date()
    if tm >= 18 * 60:
        d = d + datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d = d + datetime.timedelta(days=1)
    return d
m["tdate"] = [tdate(e, tm) for e, tm in zip(m["et"], m["tm"])]

def profile(bars, bracket_start_tm):
    lv = collections.defaultdict(set)
    for h, l, tm in bars:
        br = (tm - bracket_start_tm) // 30
        p = round(l / INC) * INC
        while p <= h + 1e-9:
            lv[round(p, 2)].add(br); p += INC
    if not lv:
        return None
    cnt = {p: len(s) for p, s in lv.items()}; tot = sum(cnt.values()); prices = sorted(cnt)
    mid = (prices[0] + prices[-1]) / 2
    poc = max(prices, key=lambda p: (cnt[p], -abs(p - mid)))
    lo = hi = poc; acc = cnt[poc]
    while acc < 0.7 * tot:
        up = [p for p in prices if p > hi][:2]; dn = [p for p in prices if p < lo][-2:]
        su = sum(cnt[p] for p in up); sd = sum(cnt[p] for p in dn)
        if su >= sd and up: hi = up[-1]; acc += su
        elif dn: lo = dn[0]; acc += sd
        else: break
    return poc, hi, lo, prices[-1], prices[0]

hist_rows, sess_rows, delta_rows = [], [], []
def ib_class(w):
    return "NARROW" if w <= 12 else ("MEDIUM" if w <= 25 else "WIDE")
for d, g in m.groupby("tdate", sort=True):
    rth = g[(g["tm"] >= 570) & (g["tm"] < 960)].sort_values("ts")
    glb = g[(g["tm"] >= 18 * 60) | (g["tm"] < 570)].sort_values("ts")
    if len(rth) < 12:
        continue
    base = datetime.datetime.combine(d, datetime.time(9, 30), tzinfo=ET)
    # GLOBEX profile (brackets from 18:00 prev day; tm of overnight bars wraps — use minutes since 18:00)
    if len(glb) >= 6:
        gb = [(float(r.high), float(r.low), ((r.tm - 18 * 60) % (24 * 60))) for r in glb.itertuples()]
        gp = profile(gb, 0)
        if gp:
            poc, vah, val, rh, rl = gp
            hist_rows.append((base + datetime.timedelta(seconds=5), poc, vah, val, None, None))
            sess_rows.append((f"GLOBEX_{d}", "GLOBEX", d, (base - datetime.timedelta(hours=15, minutes=30)).astimezone(datetime.timezone.utc),
                              poc, vah, val, rh, rl, int(glb["volume"].sum()), None, None, 0, len({x[2] // 30 for x in gb}), None, None))
    bars = [(float(r.high), float(r.low), int(r.tm)) for r in rth.itertuples()]
    for k in range(1, 13):                                  # snapshots 10:00 … 15:30 (+5 s)
        snap_tm = 570 + 30 * k
        upto = [b for b in bars if b[2] < snap_tm]
        pr = profile(upto, 570)
        if not pr:
            continue
        ibb = [b for b in upto if b[2] < 630]
        ibh, ibl = (max(b[0] for b in ibb), min(b[1] for b in ibb)) if ibb else (None, None)
        hist_rows.append((base + datetime.timedelta(minutes=30 * k, seconds=5), pr[0], pr[1], pr[2], ibh, ibl))
    full = profile(bars, 570); ibb = [b for b in bars if b[2] < 630]
    if not full or not ibb:          # a session without first-hour bars (sparse back-month days) — no CASH summary
        continue
    ibh, ibl = max(b[0] for b in ibb), min(b[1] for b in ibb); ibw = round(ibh - ibl, 2)
    sess_rows.append((f"CASH_{d}", "CASH", d, base.astimezone(datetime.timezone.utc), full[0], full[1], full[2], full[3], full[4],
                      int(rth["volume"].sum()), ibh, ibl, 1, len({b[2] // 30 for b in bars}), ibw, ib_class(ibw)))
    cum = 0
    for r in rth.itertuples():
        dl = int(r.ask_vol) - int(r.bid_vol); cum += dl
        delta_rows.append((int(r.ts), dl, cum, "UP" if dl > 0 else ("DOWN" if dl < 0 else "FLAT")))
os.makedirs(outdir, exist_ok=True)
pd.DataFrame(hist_rows, columns=["created_at", "poc", "vah", "val", "ib_high", "ib_low"]).to_csv(f"{outdir}/tpo_history.csv", index=False)
pd.DataFrame(sess_rows, columns=["session_id", "session_type", "trading_date", "opened_ts", "poc_price", "vah_price", "val_price", "range_high",
                                 "range_low", "total_volume", "ib_high", "ib_low", "ib_locked", "letter_count", "ib_width", "ib_class"]).to_csv(f"{outdir}/tpo_sessions.csv", index=False)
pd.DataFrame(delta_rows, columns=["ts", "delta", "cumulative", "direction"]).to_csv(f"{outdir}/delta.csv", index=False)
print(f"tpo_history {len(hist_rows)} · tpo_sessions {len(sess_rows)} · delta {len(delta_rows)} → {outdir}")
