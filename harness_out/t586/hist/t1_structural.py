#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super-agent T1 — the same live-eligible candidates re-simulated with DOCTRINE geometry instead of pattern geometry:
stop = just beyond the nearest structural reference against the trade (session extreme so far, IB edge once locked,
developing VAL/VAH/POC, prior-day VAL/VAH/POC/low/high, opening range), T1 = the nearest structural reference ahead
that pays >= 1R (else 1.5R), T0 = +3 pts for the first contract. Prints T1-hit rate, expectancy and the 5-contract
ladder per cell against the pattern geometry on the same candidates.
usage: t1_structural.py <cand.csv> [--db=mems26_hist] [--nmin=25] [--key=opening_type,phase,day_type,kind,zone] [--buf=0.5] [--minr=2]"""
import sys, subprocess, collections, numpy as np, pandas as pd
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
f = next(a for a in sys.argv[1:] if not a.startswith("--")); opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
DB = opt.get("db", "mems26_hist"); NMIN = int(opt.get("nmin", 25)); BUF = float(opt.get("buf", 0.5)); MINR = float(opt.get("minr", 2))
KEY = opt.get("key", "opening_type,phase,day_type,kind,zone").split(","); TICK = 0.25; PT = 5.0; COMM = 2.6; T0 = 3.0
raw = subprocess.run([PSQL, "-d", DB, "-Atc", "select (ts at time zone 'America/New_York')::date, to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close "
                      "from v9_bars_5min_woodies where symbol='MES' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts"], capture_output=True, text=True).stdout
BARS = collections.defaultdict(list)
for line in raw.splitlines():
    d, il, o, h, l, c = line.split("|"); BARS[d].append((il, float(o), float(h), float(l), float(c)))
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
PREV = {}
for i, d in enumerate(DAYS):
    if i and len(BARS[DAYS[i - 1]]) >= 30:
        pb = BARS[DAYS[i - 1]]; poc, vah, val = profile(pb); PREV[d] = dict(poc=poc, vah=vah, val=val, high=max(b[2] for b in pb), low=min(b[3] for b in pb))
def mins(s): return int(s[:2]) * 60 + int(s[3:5])
def geometry(row, bars):
    """structural stop and T1 for a candidate fired at row.il"""
    m = mins(row.il); fm = (m // 5) * 5; idx = next((i for i, b in enumerate(bars) if mins(b[0]) >= fm), None)
    if idx is None: return None
    past = bars[:idx]; d = 1 if row.direction.upper() == "LONG" else -1; e = float(row.entry)
    refs = {}
    if past: refs["session_high"] = max(b[2] for b in past); refs["session_low"] = min(b[3] for b in past)
    if len(past) >= 12: refs["IB_high"] = max(b[2] for b in bars[:12]); refs["IB_low"] = min(b[3] for b in bars[:12])
    refs["open_range_high"], refs["open_range_low"] = bars[0][2], bars[0][3]
    for k in ("poc", "vah", "val"):
        v = getattr(row, k, None)
        if v == v and v is not None: refs["dev_" + k] = float(v)
    pv = PREV.get(row.session) or {}
    for k in ("poc", "vah", "val", "high", "low"): refs["prev_" + k] = pv.get(k)
    against = sorted([(d * (e - v), k, v) for k, v in refs.items() if v is not None and d * (e - v) >= MINR], key=lambda x: x[0])
    ahead = sorted([(d * (v - e), k, v) for k, v in refs.items() if v is not None and d * (v - e) > 0], key=lambda x: x[0])
    if not against: return None
    sdist, sname, sref = against[0]; stop = sref - d * BUF; R = abs(e - stop)
    t1c = [a for a in ahead if a[0] >= 1.0 * R]
    t1, tname = (t1c[0][2], t1c[0][1]) if t1c else (e + d * 1.5 * R, "1.5R")
    return idx, d, e, stop, R, t1, sname, tname
def sim(bars, idx, d, e, stop, t1):
    o, h, l = bars[idx][1], bars[idx][2], bars[idx][3]; fill = e if l <= e <= h else o
    stop = stop; mfe = 0.0; t0hit = 0; t1hit = 0; out = None
    for i in range(idx, len(bars)):
        _, o, h, l, c = bars[i]
        if (l <= stop) if d == 1 else (h >= stop): out = (d * (stop - fill), "STOP"); break
        mfe = max(mfe, d * ((h if d == 1 else l) - fill))
        if mfe >= T0: t0hit = 1
        if (h >= t1) if d == 1 else (l <= t1): out = (d * (t1 - fill), "T1"); t1hit = 1; break
    if out is None: out = (d * (bars[-1][4] - fill), "EOD")
    return out[0], out[1], mfe, t0hit, t1hit
df = pd.read_csv(f).fillna({"kind": "?", "opening_type": "?", "phase": "?", "day_type": "?", "zone": "?"})
elig = df.blocked_by.fillna("").astype(str).isin(["", "nan"]) & (df.shadow_only == 0) & ((df.taken == 1) | (df.live_blocked_by.fillna("") == "live_slot_occupied")) & (df.r_pts > 0) & (df.r_pts <= 20)
U = df[elig].copy(); U["cell"] = U[KEY].astype(str).agg("|".join, axis=1)
rows = []
for r in U.itertuples():
    bars = BARS.get(r.session) or []
    if len(bars) < 20: continue
    g = geometry(r, bars)
    if g is None: continue
    idx, d, e, stop, R, t1, sname, tname = g
    pts, ex, mfe, t0, t1h = sim(bars, idx, d, e, stop, t1)
    rows.append(dict(session=r.session, il=r.il, cell=r.cell, kind=r.kind, phase=r.phase, pattern=r.pattern, R_struct=round(R, 2), stop_ref=sname, t1_ref=tname,
                     t1_dist=round(abs(t1 - e), 2), pts=round(pts, 2), net=round(pts * PT - COMM, 2), exit=ex, t0=t0, t1hit=t1h, mfe=round(mfe, 2),
                     R_pat=r.r_pts, net_pat=r.net, t1hit_pat=int(r.exit == "T1")))
S = pd.DataFrame(rows)
def summ(g):
    return pd.Series({"n": len(g), "R_struct": g.R_struct.median(), "R_pat": g.R_pat.median(), "T1%_struct": 100 * g.t1hit.mean(), "T1%_pat": 100 * g.t1hit_pat.mean(),
                      "E$_struct": g.net.mean(), "E$_pat": g.net_pat.mean(), "T0(3)%": 100 * g.t0.mean(), "t1_dist": g.t1_dist.median()})
print(f"{len(S)} live-eligible candidates re-simulated with structural geometry (buffer {BUF}, min R {MINR}) — pattern geometry on the same candidates alongside")
print("\nALL:"); print(summ(S).round(1).to_string())
print("\nby kind:"); print(S.groupby("kind").apply(summ).round(1).to_string())
print("\nby kind x phase:"); print(S.groupby(["kind", "phase"]).apply(summ).round(1).to_string())
print("\nstop references used:"); print(S.stop_ref.value_counts().head(8).to_string()); print("\nT1 references used:"); print(S.t1_ref.value_counts().head(8).to_string())
by = S.groupby("cell").apply(summ); by = by[by.n >= NMIN]
print(f"\ntop cells by T1%_struct (n>={NMIN}):"); print(by.sort_values("T1%_struct", ascending=False).head(15).round(1).to_string())
ok = by[(by["T1%_struct"] >= 80) & (by["E$_struct"] > 0)]; print(f"\ncells with T1 >= 80% and E > 0 under structural geometry: {len(ok)}"); print(ok.round(1).to_string() if len(ok) else "")
if opt.get("out"): S.to_csv(opt["out"], index=False); print("→", opt["out"])
