#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super-agent T1 — R2 (open-drive pullback) in REAL TIME. thesis_entries.py read the drive on the first 6 bars but let
the entry fire from bar 4, i.e. bars 4-6 used bars 5-6 (lookahead). Here every variant uses only bars already closed:
  rt3  drive on the first 3 closed bars (the doctrine's 15-min read), entries from bar 4
  rt4  drive on the first 4 closed bars, entries from bar 5
  rt6  drive on the first 6 closed bars, entries from bar 7
  lock the SYSTEM's own opening lock (harness s1 timeline `ot_locked` == OPEN_DRIVE at its lock bar), entries after it
Drive (bars 1..K): every close beyond the session open on the drive side and no bar trading more than 2 ticks through
the open. Entry = first pullback bar (i >= K, i <= 12) whose low (high) comes within 2 pts of the opening-range edge
and that closes with the drive beyond the edge; stop = open -/+ 2 ticks; T1 = 1.5R (`pts15`) and, as the scalp
reference, +3 pts (`pts3`). One trade per session. usage:
  thesis_rt.py <sessions.txt> [--db=mems26_hist] [--lock=TAG] [--out=csv]"""
import sys, subprocess, collections, json, os, pandas as pd
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
args = [a for a in sys.argv[1:] if not a.startswith("--")]; opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
DB = opt.get("db", "mems26_hist"); TICK = 0.25; PT = 5.0; COMM = 2.6; T0 = 3.0; LOCK = opt.get("lock")
sessions = sum((open(a).read().split() for a in args), [])
def q(sql): return subprocess.run([PSQL, "-d", DB, "-Atc", sql], capture_output=True, text=True).stdout.strip().splitlines()
raw = q("select (ts at time zone 'America/New_York')::date, to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close from v9_bars_5min_woodies "
        "where symbol='MES' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts")
BARS = collections.defaultdict(list)
for line in raw: d, il, o, h, l, c = line.split("|"); BARS[d].append((il, float(o), float(h), float(l), float(c)))
def sim(bars, i, d, e, stop, t1):
    """returns (pts, exit, mfe) scoring from the bar after entry; stop checked before target on the same bar."""
    mfe = 0.0
    for k in range(i + 1, len(bars)):
        _, o, h, l, c = bars[k]
        if (l <= stop) if d == 1 else (h >= stop): return d * (stop - e), "STOP", mfe
        mfe = max(mfe, d * ((h if d == 1 else l) - e))
        if (h >= t1) if d == 1 else (l <= t1): return d * (t1 - e), "T1", mfe
    return d * (bars[-1][4] - e), "EOD", mfe
def drive_k(bars, k):
    """drive read on bars[0:k] only (all closed)."""
    o = bars[0][1]; closes = [b[4] for b in bars[:k]]; lows = [b[3] for b in bars[:k]]; highs = [b[2] for b in bars[:k]]
    if all(c > o for c in closes[1:]) and min(lows[1:]) >= o - 2 * TICK: return 1
    if all(c < o for c in closes[1:]) and max(highs[1:]) <= o + 2 * TICK: return -1
    return 0
def lock_drive(s, bars):
    """the system's own lock from the harness timeline: (direction, first bar index usable) or (0, None)."""
    p = f"harness_out/t466/{LOCK}_{s}.json"
    if not LOCK or not os.path.exists(p): return 0, None
    s1 = json.load(open(p)).get("s1") or []
    lk = next((r for r in s1 if r.get("ot_locked")), None)
    if not lk or lk["ot_locked"] != "OPEN_DRIVE": return 0, None
    ils = [b[0] for b in bars]
    if lk["il"] not in ils: return 0, None
    k = ils.index(lk["il"])              # the lock is written on the push of bar k -> bar k-1 is the last closed one
    ref = bars[k - 1][4] if k >= 1 else bars[0][4]
    return (1 if ref > bars[0][1] else -1), k
rows = []
for s in sessions:
    bars = BARS.get(s) or []
    if len(bars) < 40: continue
    o = bars[0][1]; orh, orl = bars[0][2], bars[0][3]
    variants = {"ref": (drive_k(bars, 6), 3), "rt3": (drive_k(bars, 3), 3), "rt4": (drive_k(bars, 4), 4), "rt6": (drive_k(bars, 6), 6)}   # ref = thesis_entries.py (lookahead on bars 4-6)
    if LOCK:
        d, k = lock_drive(s, bars); variants["lock"] = (d, k if k is not None else 99)
    for name, (drive, k0) in variants.items():
        if not drive: continue
        for i in range(k0, min(13, len(bars) - 1)):
            il, bo, bh, bl, bc = bars[i]
            hit = (drive == 1 and bl <= orh + 2 and bc > bo and bc > orh) or (drive == -1 and bh >= orl - 2 and bc < bo and bc < orl)
            if not hit: continue
            stop = o - drive * 2 * TICK; r = abs(bc - stop)
            p15, ex15, mfe = sim(bars, i, drive, bc, stop, bc + drive * 1.5 * r)
            p3, ex3, _ = sim(bars, i, drive, bc, stop, bc + drive * T0)
            pnt, exnt, mfe = sim(bars, i, drive, bc, stop, bc + drive * 1e6)        # no target: MFE until the stop / EOD (frontier input)
            rows.append(dict(session=s, variant=name, il=il, bar=i + 1, dir="LONG" if drive == 1 else "SHORT", R=round(r, 2), mfe=round(mfe, 2), pts_nt=round(pnt, 2), exit_nt=exnt,
                             pts15=round(p15, 2), net15=round(p15 * PT - COMM, 2), exit15=ex15, t1hit=int(ex15 == "T1"), t0=int(ex3 == "T1"),
                             pts3=round(p3, 2), net3=round(p3 * PT - COMM, 2), exit3=ex3))
            break
S = pd.DataFrame(rows)
if S.empty: print("no entries"); sys.exit(0)
def summ(g): return pd.Series({"n": len(g), "sessions": g.session.nunique(), "R": g.R.median(), "T0(3)%": 100 * g.t0.mean(), "T1(1.5R)%": 100 * g.t1hit.mean(),
                                "E15$": g.net15.mean(), "Σ15$": g.net15.sum(), "E3$": g.net3.mean(), "Σ3$": g.net3.sum(), "worst15$": g.net15.min()})
print(f"{len(S)} R2 entries over {S.session.nunique()} sessions ({len(sessions)} sessions asked), one per session per variant")
print("\nby variant (ref = lookahead as in thesis_entries.py; rt3/rt4/rt6 = drive read on closed bars only; lock = the system's own OPEN_DRIVE lock):")
print(S.groupby("variant").apply(summ).round(1).to_string())
print("\nby variant x direction:"); print(S.groupby(["variant", "dir"]).apply(summ).round(1).to_string())
S["month"] = S.session.str[:7]
for v in S.variant.unique():
    g = S[S.variant == v].groupby("month").net15.agg(["count", "sum"]); neg = int((g["sum"] < 0).sum())
    print(f"\n{v}: months {len(g)}, negative months {neg}, worst month {g['sum'].min():.1f}$")
if opt.get("out"): S.to_csv(opt["out"], index=False)
