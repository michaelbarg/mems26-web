#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super-agent T1 — R4 "gap outside yesterday's range that fails" (from the 27.02.26 day review: open below the prior
range, no follow-through, the market traded back to value all day while the system shorted twice). Dalton: an open
outside the prior day's range is high-risk/high-opportunity; if it does not continue away, it returns to the range/value.
Rule (fixed before measuring):  open above the prior day's HIGH (or below the LOW); after the first K closed bars the
session has NOT extended beyond the open by more than X = 25% of the gap (continuation failed); the first later bar
(i <= 18) that closes back toward the range beyond the opening bar's close -> enter toward the range; stop = the session
extreme so far +/- 2 ticks; T1 = the prior day's range edge (the gap fill); T0 = +3. One trade per session.
Variants K=3 and K=6. usage: thesis_r4.py <sessions.txt> [--db=mems26_hist] [--out=csv]"""
import sys, subprocess, collections, pandas as pd
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
args = [a for a in sys.argv[1:] if not a.startswith("--")]; opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
DB = opt.get("db", "mems26_hist"); TICK = 0.25; PT = 5.0; COMM = 2.6; T0 = 3.0
sessions = sum((open(a).read().split() for a in args), [])
def q(sql): return subprocess.run([PSQL, "-d", DB, "-Atc", sql], capture_output=True, text=True).stdout.strip().splitlines()
BARS = collections.defaultdict(list)
for line in q("select (ts at time zone 'America/New_York')::date, to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close from v9_bars_5min_woodies "
              "where symbol='MES' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts"):
    d, il, o, h, l, c = line.split("|"); BARS[d].append((il, float(o), float(h), float(l), float(c)))
DAYS = sorted(BARS)
def sim(bars, i, d, e, stop, t1):
    mfe = 0.0
    for k in range(i + 1, len(bars)):
        _, o, h, l, c = bars[k]
        if (l <= stop) if d == 1 else (h >= stop): return d * (stop - e), "STOP", mfe
        mfe = max(mfe, d * ((h if d == 1 else l) - e))
        if (h >= t1) if d == 1 else (l <= t1): return d * (t1 - e), "T1", mfe
    return d * (bars[-1][4] - e), "EOD", mfe
rows = []; gaps = 0
for s in sessions:
    bars = BARS.get(s) or []; i_prev = DAYS.index(s) - 1 if s in DAYS else -1
    if len(bars) < 40 or i_prev < 0 or len(BARS[DAYS[i_prev]]) < 30: continue
    prev = BARS[DAYS[i_prev]]; pdh, pdl = max(b[2] for b in prev), min(b[3] for b in prev)
    o = bars[0][1]
    if o > pdh: d = -1; edge = pdh; gap = o - pdh          # gap up -> the fill trade is SHORT toward the prior high
    elif o < pdl: d = 1; edge = pdl; gap = pdl - o
    else: continue
    gaps += 1
    for K in (3, 6):
        ext = max((b[2] for b in bars[:K])) - o if d == -1 else o - min(b[3] for b in bars[:K])     # extension AWAY from the range
        if ext > 0.25 * gap: continue                                                               # continuation -> no fill trade
        c0 = bars[0][4]
        for i in range(K, min(19, len(bars) - 1)):
            il, bo, bh, bl, bc = bars[i]
            if (d == -1 and bc < bo and bc < c0) or (d == 1 and bc > bo and bc > c0):
                hi = max(b[2] for b in bars[:i + 1]); lo = min(b[3] for b in bars[:i + 1])
                stop = (hi + 2 * TICK) if d == -1 else (lo - 2 * TICK); r = abs(bc - stop); t1 = edge
                if d * (t1 - bc) <= 0: break                                                        # already filled
                pts, ex, mfe = sim(bars, i, d, bc, stop, t1); p3, ex3, _ = sim(bars, i, d, bc, stop, bc + d * T0)
                rows.append(dict(session=s, K=K, il=il, bar=i + 1, dir="LONG" if d == 1 else "SHORT", gap=round(gap, 2), R=round(r, 2), t1_dist=round(abs(t1 - bc), 2),
                                 pts=round(pts, 2), net=round(pts * PT - COMM, 2), exit=ex, t1hit=int(ex == "T1"), t0=int(ex3 == "T1"), mfe=round(mfe, 2)))
                break
S = pd.DataFrame(rows)
print(f"sessions asked {len(sessions)} · opened outside the prior range {gaps} · entries {len(S)}")
if S.empty: sys.exit(0)
def summ(g): return pd.Series({"n": len(g), "gap": g.gap.median(), "R": g.R.median(), "t1_dist": g.t1_dist.median(), "T0(3)%": 100 * g.t0.mean(), "T1%": 100 * g.t1hit.mean(),
                                "E$": g.net.mean(), "Σ$": g.net.sum(), "worst$": g.net.min(), "stop%": 100 * (g.exit == "STOP").mean()})
print(S.groupby("K").apply(summ).round(1).to_string()); print(S.groupby(["K", "dir"]).apply(summ).round(1).to_string())
S["month"] = S.session.str[:7]
for K in (3, 6):
    g = S[S.K == K].groupby("month").net.sum(); print(f"K={K}: months {len(g)}, negative {int((g < 0).sum())}, worst month {g.min():.0f}$")
if opt.get("out"): S.to_csv(opt["out"], index=False)
