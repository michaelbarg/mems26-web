#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super-agent T1 — R3 (IB-break acceptance) with REAL-TIME trend evidence. thesis_entries.py showed R3 pays only on
hindsight Trend days (+70$/trade, 72% T1) and loses elsewhere. The doctrine's real-time signs of a trend day, fixed in
advance (Dalton): (a) open-drive read on the first 3 closed bars in the break direction, (b) open outside the prior
day's RANGE (gap), (c) Σ delta from the open to the break bar with the break, (d) IB narrower than the trailing median.
Entry = 2nd consecutive close beyond the IB edge whose bar held the edge (as thesis_entries); stop = edge ∓ 4 ticks;
T1 = edge ± IB width (measured move). One trade per session, first break only.
usage: thesis_r3rt.py <sessions.txt> [--db=mems26_hist] [--out=csv]"""
import sys, subprocess, collections, pandas as pd
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
args = [a for a in sys.argv[1:] if not a.startswith("--")]; opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
DB = opt.get("db", "mems26_hist"); TICK = 0.25; PT = 5.0; COMM = 2.6
sessions = sum((open(a).read().split() for a in args), [])
def q(sql): return subprocess.run([PSQL, "-d", DB, "-Atc", sql], capture_output=True, text=True).stdout.strip().splitlines()
BARS = collections.defaultdict(list)
for line in q("select (ts at time zone 'America/New_York')::date, to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close from v9_bars_5min_woodies "
              "where symbol='MES' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts"):
    d, il, o, h, l, c = line.split("|"); BARS[d].append((il, float(o), float(h), float(l), float(c)))
DELTA = {}
for line in q("select (ts at time zone 'America/New_York')::date, to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), delta from v9_bars_cumulative_delta "
              "where (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts, case when source_version='hist' then 0 else 1 end"):
    d, il, dl = line.split("|")
    if dl not in ("", "None"): DELTA.setdefault((d, il), float(dl))
DAYS = sorted(BARS)
def sim(bars, i, d, e, stop, t1):
    mfe = 0.0
    for k in range(i + 1, len(bars)):
        _, o, h, l, c = bars[k]
        if (l <= stop) if d == 1 else (h >= stop): return d * (stop - e), "STOP", mfe
        mfe = max(mfe, d * ((h if d == 1 else l) - e))
        if (h >= t1) if d == 1 else (l <= t1): return d * (t1 - e), "T1", mfe
    return d * (bars[-1][4] - e), "EOD", mfe
def drive3(bars):
    o = bars[0][1]; cl = [b[4] for b in bars[:3]]; lo = [b[3] for b in bars[:3]]; hi = [b[2] for b in bars[:3]]
    if all(c > o for c in cl[1:]) and min(lo[1:]) >= o - 2 * TICK: return 1
    if all(c < o for c in cl[1:]) and max(hi[1:]) <= o + 2 * TICK: return -1
    return 0
rows = []; ibw_hist = []
for s in DAYS:
    bars = BARS[s]
    if len(bars) < 40: continue
    ibh, ibl = max(b[2] for b in bars[:12]), min(b[3] for b in bars[:12]); ibw = ibh - ibl
    ib_med = sorted(ibw_hist[-20:])[len(ibw_hist[-20:]) // 2] if ibw_hist else None     # trailing median of the last 20 sessions (known at the time)
    ibw_hist.append(ibw)
    if s not in sessions: continue
    i_prev = DAYS.index(s) - 1; prev = BARS[DAYS[i_prev]] if i_prev >= 0 else None
    pdh, pdl = (max(b[2] for b in prev), min(b[3] for b in prev)) if prev else (None, None)
    o = bars[0][1]; drv = drive3(bars); gap = None if pdh is None else (1 if o > pdh else (-1 if o < pdl else 0))
    hi, lo = max(b[2] for b in bars), min(b[3] for b in bars); rng = hi - lo; cp = (bars[-1][4] - lo) / rng if rng else .5
    trend_eod = int(rng / max(ibw, TICK) >= 2.0 and (cp >= .85 or cp <= .15))        # hindsight reference only
    ext_up = ext_dn = 0
    for i in range(12, len(bars) - 1):
        il, bo, bh, bl, bc = bars[i]
        ext_up = ext_up + 1 if bc > ibh + 2 * TICK else 0; ext_dn = ext_dn + 1 if bc < ibl - 2 * TICK else 0
        d = 1 if (ext_up == 2 and bl >= ibh - 2 * TICK) else (-1 if (ext_dn == 2 and bh <= ibl + 2 * TICK) else 0)
        if not d: continue
        edge = ibh if d == 1 else ibl; stop = edge - d * 4 * TICK; t1 = edge + d * ibw; r = abs(bc - stop)
        pts, ex, mfe = sim(bars, i, d, bc, stop, t1)
        dsum = sum((DELTA.get((s, bars[j][0])) or 0.0) for j in range(0, i + 1)); have_d = any((s, bars[j][0]) in DELTA for j in range(0, i + 1))
        rows.append(dict(session=s, il=il, bar=i + 1, dir="LONG" if d == 1 else "SHORT", R=round(r, 2), t1_dist=round(abs(t1 - bc), 2), ibw=round(ibw, 2),
                         pts=round(pts, 2), net=round(pts * PT - COMM, 2), exit=ex, t1hit=int(ex == "T1"), mfe=round(mfe, 2), trend_eod=trend_eod,
                         a_drive=int(drv == d), a_drive_against=int(drv == -d), b_gap=(None if gap is None else int(gap == d)), b_gap_any=(None if gap is None else int(gap != 0)),
                         c_delta=(int(d * dsum > 0) if have_d else None), d_narrow=(None if ib_med is None else int(ibw < ib_med)), hour=il[:2]))
        break
S = pd.DataFrame(rows)
if S.empty: print("no entries"); sys.exit(0)
def row(g, name): return {"cond": name, "n": len(g), "T1%": round(100 * g.t1hit.mean()) if len(g) else None, "E$": round(g.net.mean(), 1) if len(g) else None,
                          "Σ$": round(g.net.sum()) if len(g) else None, "trend_eod%": round(100 * g.trend_eod.mean()) if len(g) else None}
conds = [("all", S), ("hindsight Trend (reference)", S[S.trend_eod == 1]), ("(a) open-drive with break", S[S.a_drive == 1]), ("(a') open-drive against", S[S.a_drive_against == 1]),
         ("(b) open outside prior range, with break", S[S.b_gap == 1]), ("(b') open inside prior range", S[S.b_gap_any == 0]), ("(c) Σdelta open→break with break", S[S.c_delta == 1]),
         ("(c') Σdelta against", S[S.c_delta == 0]), ("(d) IB narrower than trailing median", S[S.d_narrow == 1]), ("(d') IB wider", S[S.d_narrow == 0]),
         ("(a)&(c)", S[(S.a_drive == 1) & (S.c_delta == 1)]), ("(b)&(c)", S[(S.b_gap == 1) & (S.c_delta == 1)]), ("(c)&(d)", S[(S.c_delta == 1) & (S.d_narrow == 1)]),
         ("(a)|(b) & (c)", S[((S.a_drive == 1) | (S.b_gap == 1)) & (S.c_delta == 1)]), ("break before 18:00 IL", S[S.hour < "18"]), ("break 18:00+ IL", S[S.hour >= "18"])]
print(f"R3 IB-break entries: {len(S)} over {S.session.nunique()} sessions ({len(sessions)} asked); R median {S.R.median():.1f}, T1 dist median {S.t1_dist.median():.1f}")
print(pd.DataFrame([row(g, n) for n, g in conds]).to_string(index=False))
if opt.get("out"): S.to_csv(opt["out"], index=False)
