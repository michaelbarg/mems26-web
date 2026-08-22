#!/usr/bin/env python3
"""cvd_effort_result.py — Michael's "price talking to CVD" (effort vs result) study.

READ-ONLY.  Not imported by any runtime path.

WHAT IT DOES
  1. Builds REAL per-5min-bar aggressor delta from the Sierra tick file
     (~/SierraChart/Data/MESU26_FUT_CME.scid, BidVolume/AskVolume per tick),
     because v9_bars_cumulative_delta covers only 29/34 sessions and is
     duplicated/partial on several of them.  Validates the tick aggregation
     against v9_bars_5min_woodies.volume (Rule 2) before using it.
  2. Reconstructs Michael's four annotated moments of 2026-08-21 numerically.
  3. Defines 6 effort-vs-result primitives and measures each across all
     live-era sessions, BY DAY TYPE (causal 7-type label).
  4. Joint replay: one live slot, CVD-aware variants vs the live-S2 baseline.

ENGINES REUSED (not rebuilt)
  scripts/oracle_study.py       bars, ATR, zigzag threshold, sim_ladder, cost model
  scripts/entry_side_replay.py  session loader, Scid reader, causal 7-type labels
  scripts/good_pattern_fix.py   S2Shim + LIVE _detect_reactive/_detect_initiative,
                                sim_stream (one-slot sequential), agg
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import importlib.util as _ilu
import json
import os
import statistics
import struct
import sys

import numpy as np
import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load(name, rel):
    spec = _ilu.spec_from_file_location(name, os.path.join(ROOT, rel))
    m = _ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


GPF = _load("good_pattern_fix", "scripts/good_pattern_fix.py")
ESR = GPF.ESR
ORA = GPF.ORA

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
D0, D1 = ESR.D0, ESR.D1                     # 2026-07-07 .. 2026-08-21
SCID = ESR.SCID
ET_UTC = dt.timedelta(hours=4)              # EDT for the whole live era
SLIP = 1
CONTRACTS = 6
BAR_US = 5 * 60 * 1_000_000
SCID_DT = np.dtype([("t", "<i8"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"),
                    ("c", "<f4"), ("nt", "<u4"), ("tv", "<u4"),
                    ("bv", "<u4"), ("av", "<u4")])
EPOCH = dt.datetime(1899, 12, 30)


def med(xs):
    return round(statistics.median(xs), 2) if xs else 0.0


def il(t):
    """ET-naive bar time -> Israel HH:MM (EDT+7)."""
    return (t + dt.timedelta(hours=7)).strftime("%H:%M")


# ===================================================== tick-derived delta
class ScidNP(ESR.Scid):
    def block(self, t0, t1):
        a, b = self.find(t0), self.find(t1)
        if b <= a:
            return np.zeros(0, dtype=SCID_DT)
        self.f.seek(self.HDR + a * self.rec)
        raw = self.f.read((b - a) * self.rec)
        return np.frombuffer(raw, dtype=SCID_DT, count=(b - a))


def session_flow(sc, bars):
    """Per-bar {bid, ask, delta, tvol, ticks} from the tick file, + session CVD."""
    t0 = bars[0]["t"] + ET_UTC
    t1 = bars[-1]["t"] + ET_UTC + dt.timedelta(minutes=5)
    arr = sc.block(t0, t1)
    base = int((t0 - EPOCH).total_seconds() * 1_000_000)
    out = [dict(bid=0, ask=0, delta=0, tvol=0, ticks=0) for _ in bars]
    if len(arr) == 0:
        return out, [0.0] * len(bars)
    idx = ((arr["t"] - base) // BAR_US).astype(np.int64)
    n = len(bars)
    ok = (idx >= 0) & (idx < n)
    idx, sub = idx[ok], arr[ok]
    bid = np.bincount(idx, weights=sub["bv"].astype(np.float64), minlength=n)
    ask = np.bincount(idx, weights=sub["av"].astype(np.float64), minlength=n)
    tv = np.bincount(idx, weights=sub["tv"].astype(np.float64), minlength=n)
    cnt = np.bincount(idx, minlength=n)
    for i in range(n):
        out[i] = dict(bid=float(bid[i]), ask=float(ask[i]),
                      delta=float(ask[i] - bid[i]), tvol=float(tv[i]),
                      ticks=int(cnt[i]))
    cvd = list(np.cumsum([o["delta"] for o in out]))
    return out, [float(x) for x in cvd]


# ===================================================== helpers on a session
def prep(bars, flow, cvd):
    """Attach causal derived series to each bar index."""
    n = len(bars)
    vol = [b["v"] for b in bars]
    avg20 = [0.0] * n
    absd20 = [0.0] * n
    for i in range(n):
        w = vol[max(0, i - 20):i]
        avg20[i] = sum(w) / len(w) if w else (vol[i] or 1.0)
        wd = [abs(flow[j]["delta"]) for j in range(max(0, i - 20), i)]
        absd20[i] = sum(wd) / len(wd) if wd else (abs(flow[i]["delta"]) or 1.0)
    atr = [ESR.atr5(bars, i) or 2.0 for i in range(n)]
    return dict(vol=vol, avg20=avg20, absd20=absd20, atr=atr, cvd=cvd,
                d=[f["delta"] for f in flow])


def leg_dir(bars, i, k=6, atr=2.0, mult=1.0):
    """Direction of the last k-bar leg ending at i-1, or 0 if none."""
    if i - k < 0:
        return 0
    mv = bars[i - 1]["c"] - bars[i - k]["c"]
    if abs(mv) < mult * atr:
        return 0
    return 1 if mv > 0 else -1


def swing_low(bars, j, w=2):
    return all(bars[j]["l"] <= bars[k]["l"]
               for k in range(max(0, j - w), min(len(bars), j + w + 1)))


# ===================================================== the 6 primitives
L_EXT = 12          # lookback for "new extreme"
DBT_MIN, DBT_MAX = 3, 15
CHOP_K = 6
LATE_ET = dt.time(14, 0)


def prim_events(bars, S):
    """Every primitive event in one session.  Causal: bar i uses only bars<=i."""
    n = len(bars)
    ev = []
    for i in range(max(L_EXT, 8) + 1, n):
        h, l, c, o = bars[i]["h"], bars[i]["l"], bars[i]["c"], bars[i]["o"]
        rng = max(h - l, 0.25)
        a, av, ad = S["atr"][i], S["avg20"][i], S["absd20"][i]
        v, d, cv = S["vol"][i], S["d"][i], S["cvd"][i]
        pl = [bars[j]["l"] for j in range(i - L_EXT, i)]
        ph = [bars[j]["h"] for j in range(i - L_EXT, i)]
        pc = [S["cvd"][j] for j in range(i - L_EXT, i)]

        # --- P1a ABSORPTION: CVD makes a new extreme, PRICE does not -------
        #     ("effort without result" — this is what 08-21 16:50->17:40 was)
        if (min(pl) <= l <= min(pl) + 0.75 * a and cv < min(pc)
                and c > l + 0.33 * rng):
            ev.append(dict(i=i, dir=1, kind="P1a_ABSORB",
                           note=f"cvd new low {cv - min(pc):.0f}, price +{l - min(pl):.2f}"))
        if (max(ph) - 0.75 * a <= h <= max(ph) and cv > max(pc)
                and c < h - 0.33 * rng):
            ev.append(dict(i=i, dir=-1, kind="P1a_ABSORB",
                           note=f"cvd new high +{cv - max(pc):.0f}, price {h - max(ph):.2f}"))

        # --- P1b DIVERGENCE: PRICE makes a new SESSION extreme, CVD does not
        sess_l = min(bars[k]["l"] for k in range(i))
        sess_h = max(bars[k]["h"] for k in range(i))
        if l < sess_l and cv > min(S["cvd"][:i]) and c > l + 0.33 * rng:
            ev.append(dict(i=i, dir=1, kind="P1b_CVD_DIV",
                           note=f"session low, cvd +{cv - min(S['cvd'][:i]):.0f} off its low"))
        if h > sess_h and cv < max(S["cvd"][:i]) and c < h - 0.33 * rng:
            ev.append(dict(i=i, dir=-1, kind="P1b_CVD_DIV",
                           note=f"session high, cvd {cv - max(S['cvd'][:i]):.0f} off its high"))

        # --- P2 double bottom / top; "volume comes in" = DELTA arrives (PINK)
        #     Fired on the first bar after T2 whose aggressor delta arrives in
        #     the recovery direction and which closes through the prior bar.
        for j in range(max(0, i - DBT_MAX), i - DBT_MIN + 1):
            if not swing_low(bars, j):
                continue
            t2 = min(range(j + DBT_MIN, i + 1), key=lambda k: bars[k]["l"])
            if abs(bars[t2]["l"] - bars[j]["l"]) > 0.75 * a or t2 == j:
                continue
            neck = max(bars[k]["h"] for k in range(j, t2 + 1))
            if neck - bars[j]["l"] < 0.8 * a:
                continue
            if i - t2 > 5:
                continue
            if d >= 1.0 * ad and c > bars[i - 1]["h"] and c > o:
                ev.append(dict(i=i, dir=1, kind="P2_DBL_VOL",
                               note=f"T1@{j} T2@{t2} d=+{d:.0f} ({d / max(ad, 1):.1f}x) "
                                    f"v/avg={v / max(av, 1):.2f}"))
            break
        for j in range(max(0, i - DBT_MAX), i - DBT_MIN + 1):
            if not all(bars[j]["h"] >= bars[k]["h"]
                       for k in range(max(0, j - 2), min(i, j + 3))):
                continue
            t2 = max(range(j + DBT_MIN, i + 1), key=lambda k: bars[k]["h"])
            if abs(bars[t2]["h"] - bars[j]["h"]) > 0.75 * a or t2 == j:
                continue
            neck = min(bars[k]["l"] for k in range(j, t2 + 1))
            if bars[j]["h"] - neck < 0.8 * a:
                continue
            if i - t2 > 5:
                continue
            if d <= -1.0 * ad and c < bars[i - 1]["l"] and c < o:
                ev.append(dict(i=i, dir=-1, kind="P2_DBL_VOL",
                               note=f"T1@{j} T2@{t2} d={d:.0f} ({abs(d) / max(ad, 1):.1f}x) "
                                    f"v/avg={v / max(av, 1):.2f}"))
            break

        # --- P3 pullback on drying volume = ADD -----------------------------
        dd = leg_dir(bars, i, 6, a, 1.0)
        if dd and dd * (c - o) < 0 and v < 0.8 * av and v < S["vol"][i - 1] \
                and abs(d) <= 0.6 * ad:
            ev.append(dict(i=i, dir=dd, kind="P3_PB_ADD",
                           note=f"v/avg={v / max(av, 1):.2f} |d|/avg={abs(d) / max(ad, 1):.2f}"))

        # --- P4 reversal WITH volume support = take profit / flip ------------
        dd4 = leg_dir(bars, i, 8, a, 1.2)
        if dd4:
            ext_recent = (max(bars[k]["h"] for k in range(i - 1, i + 1)) >=
                          max(bars[k]["h"] for k in range(i - 8, i + 1))) if dd4 > 0 else \
                         (min(bars[k]["l"] for k in range(i - 1, i + 1)) <=
                          min(bars[k]["l"] for k in range(i - 8, i + 1)))
            if ext_recent and v >= 1.5 * av and dd4 * d < 0 and dd4 * (c - o) < 0:
                ev.append(dict(i=i, dir=-dd4, kind="P4_REV_VOL",
                               note=f"v/avg={v / max(av, 1):.2f} d={d:.0f}"))

        # --- P5 chop, no CVD progress = CLOSE --------------------------------
        if i >= CHOP_K:
            seg_h = max(bars[k]["h"] for k in range(i - CHOP_K + 1, i + 1))
            seg_l = min(bars[k]["l"] for k in range(i - CHOP_K + 1, i + 1))
            if (seg_h - seg_l <= 1.2 * a and abs(c - bars[i - CHOP_K]["c"]) <= 0.4 * a
                    and abs(cv - S["cvd"][i - CHOP_K]) <= 0.35 * ad * CHOP_K):
                dpre = leg_dir(bars, i - CHOP_K + 1, 6, a, 1.0)
                if dpre:
                    ev.append(dict(i=i, dir=dpre, kind="P5_CHOP_EXIT",
                                   note=f"rng={seg_h - seg_l:.2f} dcvd={cv - S['cvd'][i - CHOP_K]:.0f}"))

        # --- P6 late-session move WITH CVD support (YELLOW) -------------------
        if bars[i]["t"].time() >= LATE_ET:
            cc = [bars[k]["c"] for k in range(i - 8, i)]
            cvw = [S["cvd"][k] for k in range(i - 8, i)]
            if c > max(cc) and cv > max(cvw) and v >= av:
                ev.append(dict(i=i, dir=1, kind="P6_LATE_CVD", note="close+cvd new 8-bar high"))
            if c < min(cc) and cv < min(cvw) and v >= av:
                ev.append(dict(i=i, dir=-1, kind="P6_LATE_CVD", note="close+cvd new 8-bar low"))
    return ev


# ===================================================== outcome measurement
def fwd(bars, i, dirn, k):
    """MFE/MAE in points over the next k bars, from close[i]."""
    e = bars[i]["c"]
    seg = bars[i + 1:i + 1 + k]
    if not seg:
        return 0.0, 0.0
    if dirn > 0:
        return round(max(b["h"] for b in seg) - e, 2), round(e - min(b["l"] for b in seg), 2)
    return round(e - min(b["l"] for b in seg), 2), round(max(b["h"] for b in seg) - e, 2)


def ladder_stop(bars, i, dirn, stop, thr, contracts=CONTRACTS, slip=SLIP):
    """ORA.sim_ladder's management with an EXPLICIT stop (1/4 at 1R/2R/3R,
    BE after T1, structural trail on the runner).  Same cost model as ORA."""
    entry = bars[i]["c"] + dirn * slip * ORA.TICK
    R = abs(entry - stop)
    if R < 1.0:
        return None
    tg = [entry + dirn * R * k for k in (1, 2, 3)]
    q = contracts / 4.0
    left, pts, hit, ext = contracts, 0.0, 0, entry
    exit_i = len(bars) - 1
    for k in range(i + 1, len(bars)):
        b = bars[k]
        if (dirn > 0 and b["l"] <= stop) or (dirn < 0 and b["h"] >= stop):
            pts += left * dirn * (stop - dirn * slip * ORA.TICK - entry)
            left, exit_i = 0, k
            break
        while hit < 3 and ((dirn > 0 and b["h"] >= tg[hit]) or (dirn < 0 and b["l"] <= tg[hit])):
            pts += q * dirn * (tg[hit] - entry)
            left -= q
            hit += 1
            if hit == 1:
                stop = entry
        ext = max(ext, b["h"]) if dirn > 0 else min(ext, b["l"])
        if left > 0 and ((dirn > 0 and b["c"] <= ext - thr) or (dirn < 0 and b["c"] >= ext + thr)):
            pts += left * dirn * (b["c"] - dirn * slip * ORA.TICK - entry)
            left, exit_i = 0, k
            break
    if left > 0:
        pts += left * dirn * (bars[-1]["c"] - dirn * slip * ORA.TICK - entry)
    return dict(usd=round(pts * ORA.POINT_USD - ORA.COMM_RT * contracts, 2),
                exit_i=exit_i, risk=round(R, 2))


def measure(bars, ev, thr, S, contracts=CONTRACTS):
    for e in ev:
        i, d = e["i"], e["dir"]
        for k in (3, 6, 12):
            e[f"mfe{k}"], e[f"mae{k}"] = fwd(bars, i, d, k)
        r = ORA.sim_ladder(bars, i, d, thr, contracts)     # live MEMS 3-bar structural stop
        e["usd"] = r["usd"] if r else None
        e["exit_i"] = r["exit_i"] if r else None
        a = S["atr"][i]                                     # alt: 1.0 x ATR stop
        ra = ladder_stop(bars, i, d, bars[i]["c"] - d * a, thr, contracts)
        e["usd_atr"] = ra["usd"] if ra else None
    return ev


def table(rows, label):
    """Aggregate a list of measured events."""
    tk = [r for r in rows if r["usd"] is not None]
    if not rows:
        return None
    return dict(
        group=label, n=len(rows), n_tradable=len(tk),
        mfe3=med([r["mfe3"] for r in rows]), mae3=med([r["mae3"] for r in rows]),
        mfe6=med([r["mfe6"] for r in rows]), mae6=med([r["mae6"] for r in rows]),
        mfe12=med([r["mfe12"] for r in rows]), mae12=med([r["mae12"] for r in rows]),
        edge12=round(med([r["mfe12"] for r in rows]) - med([r["mae12"] for r in rows]), 2),
        win=round(100.0 * sum(1 for r in tk if r["usd"] > 0) / len(tk), 1) if tk else 0.0,
        usd=round(sum(r["usd"] for r in tk), 2),
        avg=round(sum(r["usd"] for r in tk) / len(tk), 2) if tk else 0.0,
        usd_atr=round(sum(r["usd_atr"] for r in rows if r["usd_atr"] is not None), 2),
        win_atr=round(100.0 * sum(1 for r in rows if (r["usd_atr"] or 0) > 0)
                      / max(sum(1 for r in rows if r["usd_atr"] is not None), 1), 1),
    )


# ===================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/cvd_er.json")
    a = ap.parse_args()

    from backend.v9.systems.five_min import five_min_system as _FMS
    GPF.FMS = _FMS
    from backend.v9.config_loader import load_s2_reactive_calibration, load_s2_firing
    GPF.CAL = load_s2_reactive_calibration

    cn = psycopg2.connect(DSN)
    cn.set_session(readonly=True)
    cur = cn.cursor()
    days = ESR.load_bars(cur)
    ds = ESR.live_days(days)
    print(f"[env] S2_VSA_VOLUME={os.environ.get('S2_VSA_VOLUME')} variant={load_s2_firing()} "
          f"S2_CVD_DETECTION_V1={os.environ.get('S2_CVD_DETECTION_V1')} "
          f"DIRECTION_CONTEXT={os.environ.get('DIRECTION_CONTEXT')}")
    print(f"[data] sessions={len(ds)} {ds[0]}..{ds[-1]}  bars={sum(len(days[d]) for d in ds)}")

    sc = ScidNP(SCID)
    print(f"[scid] {SCID} ticks={sc.n:,} rec={sc.rec}")

    # ---------- build flow + validate against DB volume (Rule 2) ----------
    flows, cvds, S = {}, {}, {}
    vdiff = []
    for d in ds:
        bars = days[d]
        f, cv = session_flow(sc, bars)
        flows[d], cvds[d] = f, cv
        S[d] = prep(bars, f, cv)
        for i, b in enumerate(bars):
            if b["v"] > 0:
                vdiff.append(f[i]["tvol"] / b["v"])
    print(f"[validate] tick_totalvolume / db_volume  n={len(vdiff)} "
          f"median={statistics.median(vdiff):.4f} p10={np.percentile(vdiff, 10):.4f} "
          f"p90={np.percentile(vdiff, 90):.4f}")

    # cross-check tick CVD vs v9_bars_cumulative_delta where both exist
    cur.execute("select ts, cumulative from v9_bars_cumulative_delta "
                "where left(ts,10) between %s and %s order by ts", (D0, D1))
    dbcvd = collections.defaultdict(dict)
    for k, val in cur.fetchall():
        if val is None:
            continue
        day = k[:10]
        hhmm = k[11:16]
        dbcvd[day].setdefault(hhmm, float(val))
    corr = {}
    for d in ds:
        key = d.isoformat()
        if key not in dbcvd:
            continue
        xs, ys = [], []
        for i, b in enumerate(days[d]):
            hhmm = (b["t"] + ET_UTC).strftime("%H:%M")
            if hhmm in dbcvd[key]:
                xs.append(cvds[d][i]); ys.append(dbcvd[key][hhmm])
        if len(xs) >= 20:
            corr[key] = round(float(np.corrcoef(xs, ys)[0, 1]), 4)
    print(f"[validate] tick-CVD vs v9_bars_cumulative_delta: days={len(corr)} "
          f"median r={med(list(corr.values()))} min={min(corr.values()) if corr else None}")
    bad = sorted((v, k) for k, v in corr.items() if v < 0.95)
    print(f"[validate] days with r<0.95: {bad}")

    # DB-CVD coverage per RTH session (what the LIVE gate can actually see)
    cov = {}
    for d in ds:
        key = d.isoformat()
        hh = {(b["t"] + ET_UTC).strftime("%H:%M") for b in days[d]}
        cov[key] = round(len(hh & set(dbcvd.get(key, {}))) / max(len(hh), 1), 3)
    full = sum(1 for v in cov.values() if v >= 0.95)
    zero = sum(1 for v in cov.values() if v == 0.0)
    print(f"[cvd-cov] sessions={len(cov)} full(>=95%)={full} zero={zero} "
          f"median={med(list(cov.values()))} "
          f"worst={sorted(cov.items(), key=lambda kv: kv[1])[:8]}")

    # ---------- causal day-type labels ----------
    labels = {}
    for d in ds:
        labels[d] = [ESR.norm_dt(x) for x in ESR.causal_labels(days, d, days[d])]
    dtc = collections.Counter(labels[d][-1] for d in ds)
    print(f"[daytype] EOD labels: {dict(dtc)}")

    # ---------- 1 · Michael's four moments on 2026-08-21 ----------
    d21 = dt.date(2026, 8, 21)
    m21 = []
    if d21 in days:
        bars = days[d21]
        s = S[d21]
        print("\n[08-21] bar table (IL time)  "
              "px o/h/l/c | vol v/avg | delta | CVD | cvdslope3 | label")
        for i, b in enumerate(bars):
            sl3 = s["cvd"][i] - s["cvd"][max(0, i - 3)]
            m21.append(dict(i=i, il=il(b["t"]), o=b["o"], h=b["h"], l=b["l"], c=b["c"],
                            v=int(b["v"]), vavg=round(b["v"] / max(s["avg20"][i], 1), 2),
                            delta=int(s["d"][i]), cvd=int(s["cvd"][i]),
                            slope3=int(sl3), atr=round(s["atr"][i], 2),
                            label=labels[d21][i]))
            print(f"  {il(b['t'])} {b['o']:8.2f}{b['h']:9.2f}{b['l']:9.2f}{b['c']:9.2f} "
                  f"{int(b['v']):7d} {b['v'] / max(s['avg20'][i], 1):5.2f}x "
                  f"{int(s['d'][i]):+7d} {int(s['cvd'][i]):+8d} {int(sl3):+7d}  "
                  f"{labels[d21][i] or '-'}")
        ev21 = measure(bars, prim_events(bars, s), ORA.thr_for(days, d21), s)
        print("\n[08-21] primitive events")
        for e in ev21:
            print(f"  {il(bars[e['i']]['t'])} {e['kind']:14s} "
                  f"{'LONG ' if e['dir'] > 0 else 'SHORT'} "
                  f"mfe12={e['mfe12']:6.2f} mae12={e['mae12']:6.2f} "
                  f"$struct={e['usd']} $atr={e['usd_atr']}  {e['note']}")

        # --- Michael's four annotated windows, numerically -----------------
        WINDOWS = [("BLUE  open / CVD reversal", "16:30", "17:10"),
                   ("PINK  double bottom", "17:35", "18:55"),
                   ("GREEN fall, try up, long chop", "18:55", "21:30"),
                   ("YELLOW late move w/ volume", "21:30", "22:55")]
        print("\n[08-21] Michael's four windows")
        idx = {il(b["t"]): k for k, b in enumerate(bars)}
        for name, t0, t1 in WINDOWS:
            i0, i1 = idx[t0], idx[t1]
            seg = bars[i0:i1 + 1]
            hi = max(b["h"] for b in seg); lo = min(b["l"] for b in seg)
            dpx = seg[-1]["c"] - seg[0]["o"]
            dcv = s["cvd"][i1] - s["cvd"][i0] + s["d"][i0]
            vsum = sum(b["v"] for b in seg)
            vavg = vsum / len(seg) / max(statistics.fmean(s["avg20"][i0:i1 + 1]), 1)
            print(f"  {name:32s} {t0}-{t1} bars={len(seg):3d} "
                  f"px {seg[0]['o']:.2f}->{seg[-1]['c']:.2f} ({dpx:+.2f}) "
                  f"H {hi:.2f} L {lo:.2f} | dCVD {dcv:+.0f} | vol {vavg:.2f}x avg")

    # ---------- 3 · primitives across all sessions, BY DAY TYPE ----------
    allev = []
    for d in ds:
        bars = days[d]
        thr = ORA.thr_for(days, d)
        ev = measure(bars, prim_events(bars, S[d]), thr, S[d])
        for e in ev:
            e["day"] = d.isoformat()
            e["dt"] = labels[d][e["i"]] or "UNKNOWN"
            e["hhmm_il"] = il(bars[e["i"]]["t"])
        allev += ev
    print(f"\n[prims] total events={len(allev)}")

    res = {"overall": {}, "by_daytype": {}}
    kinds = ["P1a_ABSORB", "P1b_CVD_DIV", "P2_DBL_VOL", "P3_PB_ADD", "P4_REV_VOL",
             "P5_CHOP_EXIT", "P6_LATE_CVD"]
    hdr = (f"{'primitive':13s}{'grp':17s}{'n':>5s}{'mfe3':>7s}{'mae3':>7s}"
           f"{'mfe6':>7s}{'mae6':>7s}{'mfe12':>7s}{'mae12':>7s}{'edge':>7s}"
           f"{'win%':>7s}{'$struct':>10s}{'avg$':>8s}{'$atr':>10s}{'winA%':>7s}")
    print("\n" + hdr)
    for k in kinds:
        rows = [e for e in allev if e["kind"] == k]
        t = table(rows, "ALL")
        if t:
            res["overall"][k] = t
            print(f"{k:13s}{'ALL':17s}{t['n']:5d}{t['mfe3']:7.2f}{t['mae3']:7.2f}"
                  f"{t['mfe6']:7.2f}{t['mae6']:7.2f}{t['mfe12']:7.2f}{t['mae12']:7.2f}"
                  f"{t['edge12']:7.2f}{t['win']:7.1f}{t['usd']:10.2f}{t['avg']:8.2f}"
                  f"{t['usd_atr']:10.2f}{t['win_atr']:7.1f}")
        for g in sorted({e["dt"] for e in rows}):
            sub = [e for e in rows if e["dt"] == g]
            t = table(sub, g)
            if t and t["n"] >= 3:
                res["by_daytype"].setdefault(k, {})[g] = t
                print(f"{'':13s}{g:17s}{t['n']:5d}{t['mfe3']:7.2f}{t['mae3']:7.2f}"
                      f"{t['mfe6']:7.2f}{t['mae6']:7.2f}{t['mfe12']:7.2f}{t['mae12']:7.2f}"
                      f"{t['edge12']:7.2f}{t['win']:7.1f}{t['usd']:10.2f}{t['avg']:8.2f}"
                      f"{t['usd_atr']:10.2f}{t['win_atr']:7.1f}")

    # per-direction split for the entry primitives
    print("\n[dir-split]")
    for k in kinds:
        for dn, lab in ((1, "LONG"), (-1, "SHORT")):
            sub = [e for e in allev if e["kind"] == k and e["dir"] == dn]
            t = table(sub, lab)
            if t:
                print(f"  {k:13s}{lab:6s} n={t['n']:4d} edge12={t['edge12']:6.2f} "
                      f"win={t['win']:5.1f}% $struct={t['usd']:9.2f} $atr={t['usd_atr']:9.2f}")

    # ---------- 5 · joint replay, one slot ----------
    shim = GPF.S2Shim()
    import backend.v9.services.trade_context as TC
    TC.get_live_day_type = lambda: shim.current_day_type

    IS0, IS1 = dt.date(2026, 7, 15), dt.date(2026, 8, 12)

    # PRODUCTION-FAITHFUL S2: _compute_setup_cvd reads v9_bars_cumulative_delta.
    # Also run the same scan with the TICK CVD (full 34/34 coverage) to price
    # what the missing/partial CVD rows cost.
    s2_db, s2_tick, s2_off, ev_by_day = {}, {}, {}, {}
    for d in ds:
        bars = days[d]
        key = d.isoformat()
        ev_by_day[d] = [e for e in allev if e["day"] == key]
        # (a) production: DB CVD rows, keyed by the same ISO ts the live code uses
        shim._cvd_sorted = sorted(
            ((f"{key}T{hhmm}:00+00:00", val) for hhmm, val in dbcvd.get(key, {}).items()))
        s2_db[d] = [dict(c, day=key) for c in GPF.scan_s2(bars, labels[d], shim, arm="LIVE")]
        # (b) tick CVD: complete coverage
        shim._cvd_sorted = [((b["t"] + ET_UTC).isoformat() + "+00:00", cvds[d][i])
                            for i, b in enumerate(bars)]
        s2_tick[d] = [dict(c, day=key) for c in GPF.scan_s2(bars, labels[d], shim, arm="LIVE")]
        # (c) CVD gate fully blind (fail-open everywhere)
        shim._cvd_sorted = []
        s2_off[d] = [dict(c, day=key) for c in GPF.scan_s2(bars, labels[d], shim, arm="LIVE")]
    print(f"\n[joint] S2 fires: DB-CVD={sum(len(v) for v in s2_db.values())} "
          f"tick-CVD={sum(len(v) for v in s2_tick.values())} "
          f"CVD-blind={sum(len(v) for v in s2_off.values())} | primitives={len(allev)}")

    ENTRY_PRIMS = ("P1a_ABSORB", "P1b_CVD_DIV", "P2_DBL_VOL", "P4_REV_VOL", "P6_LATE_CVD")
    variants = collections.OrderedDict()
    variants["S2 live (DB CVD)"] = lambda d, ev, s2: list(s2_db[d])
    variants["S2 CVD-blind"] = lambda d, ev, s2: list(s2_off[d])
    variants["S2 tick-CVD"] = lambda d, ev, s2: list(s2_tick[d])
    for p in ENTRY_PRIMS:
        variants[f"{p} alone"] = (lambda pp: lambda d, ev, s2:
                                  [e for e in ev if e["kind"] == pp])(p)
    variants["P1a+P2 alone"] = lambda d, ev, s2: [e for e in ev
                                                  if e["kind"] in ("P1a_ABSORB", "P2_DBL_VOL")]
    variants["ALL prims alone"] = lambda d, ev, s2: [e for e in ev if e["kind"] in ENTRY_PRIMS]
    variants["S2tick + P1a"] = lambda d, ev, s2: list(s2_tick[d]) + [
        e for e in ev if e["kind"] == "P1a_ABSORB"]
    variants["S2tick + P1a+P2"] = lambda d, ev, s2: list(s2_tick[d]) + [
        e for e in ev if e["kind"] in ("P1a_ABSORB", "P2_DBL_VOL")]
    variants["S2tick + P2"] = lambda d, ev, s2: list(s2_tick[d]) + [
        e for e in ev if e["kind"] == "P2_DBL_VOL"]
    variants["S2tick +flowfilter"] = None
    variants["S2tick +ff +P2"] = None
    # --- day-type-conditioned arms (the conditioning S2 does not have) ------
    TN = ("Trend_Normal", "Trend_DD", "Normal")
    NE = ("Neutral_Extreme", "Neutral_Center")
    variants["P2 @Trend/Normal"] = lambda d, ev, s2: [
        e for e in ev if e["kind"] == "P2_DBL_VOL" and e["dt"] in TN]
    variants["P6 @Neutral"] = lambda d, ev, s2: [
        e for e in ev if e["kind"] == "P6_LATE_CVD" and e["dt"] in NE]
    variants["S2 + P2@TN"] = lambda d, ev, s2: list(s2_db[d]) + [
        e for e in ev if e["kind"] == "P2_DBL_VOL" and e["dt"] in TN]
    variants["S2 + P2@TN + P6@N"] = lambda d, ev, s2: list(s2_db[d]) + [
        e for e in ev if (e["kind"] == "P2_DBL_VOL" and e["dt"] in TN)
        or (e["kind"] == "P6_LATE_CVD" and e["dt"] in NE)]
    variants["S2tick+ff+P2@TN"] = None
    variants["S2tick+ff+P2TN+P6N"] = None

    def cvd_ok(d, c):
        """The CVD filter Michael's read implies: with-flow for INITIATIVE,
        divergence-or-neutral for REACTIVE.  Uses tick CVD (always available)."""
        s, i, dirn = S[d], c["i"], c["dir"]
        net = s["cvd"][i] - s["cvd"][max(0, i - 3)]
        if c["kind"] == "INITIATIVE":
            return dirn * net > 0
        if c["kind"] == "REACTIVE":
            return not (dirn * net < -1.0 * s["absd20"][i])   # veto only hard opposite flow
        return True

    def run(sel, name, slip=SLIP, contracts=CONTRACTS):
        per, trades = {}, []
        for d in ds:
            bars = days[d]
            thr = ORA.thr_for(days, d)
            cands = sel(d, ev_by_day[d], s2_db[d])
            ts = GPF.sim_stream(bars, cands, thr, contracts, slip=slip)
            per[d] = round(sum(t["usd"] for t in ts), 2)
            for t in ts:
                t["day"] = d
            trades += ts
        g = GPF.agg(per, trades)
        g["name"] = name
        g["jul"] = round(sum(v for k, v in per.items() if k.month == 7), 2)
        g["aug"] = round(sum(v for k, v in per.items() if k.month == 8), 2)
        g["IS"] = round(sum(v for k, v in per.items() if IS0 <= k <= IS1), 2)
        g["OOS"] = round(sum(v for k, v in per.items() if not (IS0 <= k <= IS1)), 2)
        g["worst"] = min(per.items(), key=lambda kv: kv[1])
        g["worst"] = [g["worst"][0].isoformat(), g["worst"][1]]
        g["perday"] = {k.isoformat(): v for k, v in per.items()}
        return g

    out, sel_by_name = [], {}
    for name, sel in variants.items():
        if sel is None:
            if name == "S2tick +flowfilter":
                sel = lambda d, ev, s2: [c for c in s2_tick[d] if cvd_ok(d, c)]
            elif name == "S2tick +ff +P2":
                sel = lambda d, ev, s2: ([c for c in s2_tick[d] if cvd_ok(d, c)] +
                                         [e for e in ev if e["kind"] == "P2_DBL_VOL"])
            elif name == "S2tick+ff+P2@TN":
                sel = lambda d, ev, s2: ([c for c in s2_tick[d] if cvd_ok(d, c)] +
                                         [e for e in ev if e["kind"] == "P2_DBL_VOL"
                                          and e["dt"] in TN])
            else:
                sel = lambda d, ev, s2: ([c for c in s2_tick[d] if cvd_ok(d, c)] +
                                         [e for e in ev
                                          if (e["kind"] == "P2_DBL_VOL" and e["dt"] in TN)
                                          or (e["kind"] == "P6_LATE_CVD" and e["dt"] in NE)])
        sel_by_name[name] = sel
        out.append(run(sel, name))

    print(f"\n{'variant':21s}{'n':>5s}{'$total':>11s}{'$/day':>9s}{'medDay':>9s}"
          f"{'win%':>7s}{'+/-':>8s}{'Jul':>11s}{'Aug':>11s}{'IS':>11s}{'OOS':>11s}{'worst':>22s}")
    for g in out:
        pn = "%d/%d" % (g["pos"], g["neg"])
        print(f"{g['name']:21s}{g['n']:5d}{g['usd']:11.2f}{g['per_day']:9.2f}"
              f"{g['median_day']:9.2f}{g['win']:7.1f}{pn:>8s}"
              f"{g['jul']:11.2f}{g['aug']:11.2f}{g['IS']:11.2f}{g['OOS']:11.2f}"
              f"{str(g['worst']):>22s}")

    # robustness: slippage 0/1/2 and 4/6 contracts for the headline arms
    HEAD = ["S2 live (DB CVD)", "P2 @Trend/Normal", "S2 + P2@TN", "S2tick+ff+P2@TN"]
    print(f"\n[robust] {'variant':21s}{'s0@6c':>10s}{'s1@6c':>10s}{'s2@6c':>10s}"
          f"{'s1@4c':>10s}{'days+/-':>10s}")
    rob = {}
    for name in HEAD:
        sel = sel_by_name[name]
        row = [run(sel, name, slip=s)["usd"] for s in (0, 1, 2)]
        g4 = run(sel, name, slip=1, contracts=4)
        rob[name] = dict(s0=row[0], s1=row[1], s2=row[2], c4=g4["usd"])
        print(f"{'':9s}{name:21s}{row[0]:10.2f}{row[1]:10.2f}{row[2]:10.2f}"
              f"{g4['usd']:10.2f}{'%d/%d' % (g4['pos'], g4['neg']):>10s}")

    # who is in the P2@TN arm
    p2tn = [e for e in allev if e["kind"] == "P2_DBL_VOL"
            and e["dt"] in ("Trend_Normal", "Trend_DD", "Normal")]
    print(f"\n[P2@TN] events={len(p2tn)} days={len({e['day'] for e in p2tn})} "
          f"dt={dict(collections.Counter(e['dt'] for e in p2tn))} "
          f"dir={dict(collections.Counter(e['dir'] for e in p2tn))}")

    res["robust"] = rob
    res["joint"] = out
    res["m21"] = m21
    res["ev21"] = [{k: v for k, v in e.items() if k != "exit_i"} for e in ev21] if d21 in days else []
    res["validate"] = dict(vol_ratio_median=round(statistics.median(vdiff), 4),
                           cvd_corr=corr)
    res["sessions"] = [d.isoformat() for d in ds]
    res["events"] = allev
    with open(a.json, "w") as f:
        json.dump(res, f, default=str, indent=1)
    print(f"\n[json] {a.json}")


if __name__ == "__main__":
    main()
