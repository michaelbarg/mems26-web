#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super-agent T1 — DOCTRINE (thesis) entries prototyped offline on the bars, independent of the pattern detectors:
R1 VA-edge rejection (responsive): after the IB lock, on a day with no accepted range extension yet, a bar pokes <= 4
   ticks beyond the developing VAL/VAH (or the prior day's) and closes back inside -> enter at the close toward value;
   stop = the rejection extreme ∓ 2 ticks; T1 = the developing POC (else 1.5R); T0 = +3 pts.
R2 Open-drive pullback (initiative with the drive): opening read as OPEN_DRIVE on the first 6 bars; the first later
   bar that pulls back to within 2 pts of the opening-range edge and closes with the drive -> enter at the close;
   stop = the opening print ∓ 2 ticks (return through the origin = thesis wrong); T1 = +1.5R; T0 = +3.
R3 IB-break acceptance (initiative): a close beyond the IB edge followed by a bar that holds beyond it -> enter at that
   bar's close; stop = IB edge ∓ 4 ticks (back inside = rejected); T1 = IB edge + IB width (measured move); T0 = +3.
Every rule fires at most once per side per session; one trade at a time per session (slot). Reports n, T0/T1 hit rates,
expectancy (1 contract), by rule and by day type reference.   usage: thesis_entries.py <sessions.txt> [--db=mems26_hist]"""
import sys, subprocess, collections, pandas as pd
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
args = [a for a in sys.argv[1:] if not a.startswith("--")]; opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
DB = opt.get("db", "mems26_hist"); TICK = 0.25; PT = 5.0; COMM = 2.6; T0 = 3.0
sessions = sum((open(a).read().split() for a in args), [])
def q(sql): return subprocess.run([PSQL, "-d", DB, "-Atc", sql], capture_output=True, text=True).stdout.strip().splitlines()
raw = q("select (ts at time zone 'America/New_York')::date, to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close from v9_bars_5min_woodies "
        "where symbol='MES' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts")
BARS = collections.defaultdict(list)
for line in raw: d, il, o, h, l, c = line.split("|"); BARS[d].append((il, float(o), float(h), float(l), float(c)))
traw = q("select (created_at at time zone 'America/New_York')::date, to_char(created_at at time zone 'Asia/Jerusalem','HH24:MI'), poc, vah, val from v9_tpo_history where poc is not null order by created_at")
TPO = collections.defaultdict(list)
for line in traw: d, il, poc, vah, val = line.split("|"); TPO[d].append((il, float(poc), float(vah), float(val)))
DAYS = sorted(BARS)
def profile(bars):
    prof = collections.defaultdict(set)
    for i, b in enumerate(bars):
        p = b[3]
        while p <= b[2] + 1e-9: prof[round(p / TICK) * TICK].add(i // 6); p += TICK
    cnt = {p: len(v) for p, v in prof.items()}; tot = sum(cnt.values()); mid = (max(cnt) + min(cnt)) / 2
    poc = max(cnt, key=lambda p: (cnt[p], -abs(p - mid))); lo = hi = poc; acc = cnt[poc]
    while acc < 0.7 * tot:
        up, dn = cnt.get(round((hi + TICK) / TICK) * TICK, 0), cnt.get(round((lo - TICK) / TICK) * TICK, 0)
        if up >= dn and up > 0: hi = round((hi + TICK) / TICK) * TICK; acc += up
        elif dn > 0: lo = round((lo - TICK) / TICK) * TICK; acc += dn
        else: break
    return poc, hi, lo
def tpo_asof(d, il):
    best = None
    for row in TPO.get(d) or []:
        if row[0] <= il: best = row
        else: break
    return best
def sim(bars, i, d, e, stop, t1):
    fill = e; mfe = 0.0; t0 = 0
    for k in range(i + 1, len(bars)):
        _, o, h, l, c = bars[k]
        if (l <= stop) if d == 1 else (h >= stop): return d * (stop - fill), "STOP", t0
        mfe = max(mfe, d * ((h if d == 1 else l) - fill)); t0 = int(mfe >= T0)
        if (h >= t1) if d == 1 else (l <= t1): return d * (t1 - fill), "T1", 1
    return d * (bars[-1][4] - fill), "EOD", t0
def ref_open(bars):
    o = bars[0][1]; closes = [b[4] for b in bars[:6]]; lows = [b[3] for b in bars[:6]]; highs = [b[2] for b in bars[:6]]
    if all(c > o for c in closes[1:]) and min(lows[1:]) >= o - 2 * TICK: return 1
    if all(c < o for c in closes[1:]) and max(highs[1:]) <= o + 2 * TICK: return -1
    return 0
def ref_daytype(bars):
    ibh, ibl = max(b[2] for b in bars[:12]), min(b[3] for b in bars[:12]); ib = max(ibh - ibl, TICK)
    def acc(side):
        run = 0
        for b in bars[12:]:
            run = run + 1 if ((b[4] > ibh + 2 * TICK) if side == "up" else (b[4] < ibl - 2 * TICK)) else 0
            if run >= 2: return True
        return False
    sides = int(acc("up")) + int(acc("dn")); hi, lo = max(b[2] for b in bars), min(b[3] for b in bars); rng = hi - lo; rib = rng / ib; cp = (bars[-1][4] - lo) / rng if rng else .5
    if sides == 0: return "Nontrend" if rib <= 1.15 else "Normal"
    if sides == 2: return "Neutral"
    return "Trend" if rib >= 2.0 and (cp >= .85 or cp <= .15) else "Normal_Variation"
rows = []
for s in sessions:
    bars = BARS.get(s) or []
    if len(bars) < 40: continue
    i_prev = DAYS.index(s) - 1 if s in DAYS else -1
    prev = profile(BARS[DAYS[i_prev]]) if i_prev >= 0 and len(BARS[DAYS[i_prev]]) >= 30 else None
    dtype = ref_daytype(bars); ibh, ibl = max(b[2] for b in bars[:12]), min(b[3] for b in bars[:12]); ibw = ibh - ibl
    o = bars[0][1]; orh, orl = bars[0][2], bars[0][3]; drive = ref_open(bars)
    fired = set(); busy_until = -1
    def fire(rule, i, d, e, stop, t1):
        global busy_until
        if (rule, d) in fired or i < busy_until: return
        pts, ex, t0 = sim(bars, i, d, e, stop, t1); fired.add((rule, d))
        xi = next((k for k in range(i + 1, len(bars)) if ((bars[k][3] <= stop) if d == 1 else (bars[k][2] >= stop)) or ((bars[k][2] >= t1) if d == 1 else (bars[k][3] <= t1))), len(bars) - 1)
        busy_until = xi
        rows.append(dict(session=s, rule=rule, il=bars[i][0], dir="LONG" if d == 1 else "SHORT", R=round(abs(e - stop), 2), t1_dist=round(abs(t1 - e), 2),
                         pts=round(pts, 2), net=round(pts * PT - COMM, 2), exit=ex, t0=t0, t1hit=int(ex == "T1"), dtype=dtype))
    ext_up = ext_dn = 0
    for i in range(1, len(bars) - 1):
        il, bo, bh, bl, bc = bars[i]
        # R2 open-drive pullback (bars 4..12)
        if drive and 3 <= i <= 12:
            if drive == 1 and bl <= orh + 2 and bc > bo and bc > orh: fire("R2_drive_pullback", i, 1, bc, o - 2 * TICK, bc + 1.5 * (bc - (o - 2 * TICK)))
            if drive == -1 and bh >= orl - 2 and bc < bo and bc < orl: fire("R2_drive_pullback", i, -1, bc, o + 2 * TICK, bc - 1.5 * ((o + 2 * TICK) - bc))
        if i >= 12:
            # acceptance tracking beyond the IB
            ext_up = ext_up + 1 if bc > ibh + 2 * TICK else 0; ext_dn = ext_dn + 1 if bc < ibl - 2 * TICK else 0
            # R3 IB-break acceptance: 2nd consecutive close beyond, and this bar held beyond the edge
            if ext_up == 2 and bl >= ibh - 2 * TICK: fire("R3_ib_break", i, 1, bc, ibh - 4 * TICK, ibh + ibw)
            if ext_dn == 2 and bh <= ibl + 2 * TICK: fire("R3_ib_break", i, -1, bc, ibl + 4 * TICK, ibl - ibw)
            # R1 VA-edge rejection on a day without accepted extension so far
            tp = tpo_asof(s, il); va = (tp[1], tp[2], tp[3]) if tp else (prev[0], prev[1], prev[2]) if prev else None
            if va and ext_up < 2 and ext_dn < 2:
                poc, vah, val = va
                if bl < val and bl >= val - 4 * TICK and bc > val and poc > bc: fire("R1_va_edge", i, 1, bc, bl - 2 * TICK, poc)
                if bh > vah and bh <= vah + 4 * TICK and bc < vah and poc < bc: fire("R1_va_edge", i, -1, bc, bh + 2 * TICK, poc)
S = pd.DataFrame(rows)
def summ(g): return pd.Series({"n": len(g), "R": g.R.median(), "t1_dist": g.t1_dist.median(), "T0(3)%": 100 * g.t0.mean(), "T1%": 100 * g.t1hit.mean(), "E$": g.net.mean(), "Σ$": g.net.sum()})
print(f"{len(S)} thesis entries over {S.session.nunique()} sessions (one trade at a time per session)")
print("\nby rule:"); print(S.groupby("rule").apply(summ).round(1).to_string())
print("\nby rule x direction:"); print(S.groupby(["rule", "dir"]).apply(summ).round(1).to_string())
print("\nby rule x day-type reference (EOD, hindsight — for orientation):"); print(S.groupby(["rule", "dtype"]).apply(summ).round(1).to_string())
if opt.get("out"): S.to_csv(opt["out"], index=False)
