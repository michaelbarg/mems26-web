#!/usr/bin/env python3
"""TREND_STEP_ENTRY_V1 — research replay (2026-08-11, step-entry-agent).

Catch a stair-step trend from the FIRST step: enter INSIDE the pause that
follows an impulse leg, at a leg-relative price, with a leg-relative stop and
a target ladder sized to the measured step distribution.

STRICTLY READ-ONLY: reads `v9_bars_5min_woodies` only. Never writes to the DB,
never touches ~/SierraChart_Data, never changes a flag or restarts anything.

Usage
-----
  # design window (the 15 sessions the parameters were chosen on)
  python3 scripts/replay_trend_step_entry.py --trades --validate --compare

  # TRUE out-of-sample: these bars were found after the design was frozen
  python3 scripts/replay_trend_step_entry.py --since 2026-06-01 --until 2026-07-15 \
      --validate --sweep

  # everything (48 RTH sessions = the entire usable woodies history)
  python3 scripts/replay_trend_step_entry.py --since 2026-06-01 --until 2026-08-12 \
      --validate --compare --anatomy

Findings: docs/research/TREND_STEP_ENTRY_2026-08-11.md
Note: --compare sets HIGHER_LOW_SECOND_TEST_V1=1 in THIS PROCESS ONLY (os.environ), so the
flag-gated HLST detector can be replayed head-to-head. It never touches .env, the running
backend, or any flag file.
"""
from __future__ import annotations

import argparse
import os
import statistics as st
import sys
from collections import OrderedDict
from datetime import time as dtime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── .env must be loaded (same contract as the other replay harnesses) ──
try:
    from scripts.flag_guard import parse_env
    for _k, _v in parse_env(str(ROOT / ".env")).items():
        os.environ.setdefault(_k, _v)
except Exception as _e:  # pragma: no cover
    print(f"[warn] could not parse .env: {_e}")

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/mems26")
os.environ.setdefault("BRIDGE_TOKEN", "x")

from zoneinfo import ZoneInfo  # noqa: E402

ET = ZoneInfo("America/New_York")
RTH_OPEN, RTH_END = dtime(9, 30), dtime(16, 15)
TICK = 0.25
MES = 5.0                       # $ per point per contract
COMMISSION_RT = 1.50            # $/contract round-turn (same constant as
                                # scripts/leg_exemption_replay.py) — reported separately
CONTRACTS = 4
SINCE, UNTIL = "2026-07-15", "2026-08-12"

# ══════════════════════════════════════════════════════════════════
# TREND_STEP_ENTRY_V1 parameters (all env-tunable, defaults = shipped)
# ══════════════════════════════════════════════════════════════════
P = dict(
    ZZ_REV=5.0,           # pt — swing-reversal threshold that defines a "step"
    REQUIRE_STAIR=0,      # step must extend a staircase (lower low + lower high)
    STAIR_OR_SESSION=0,   # 1 = a VERIFIED staircase substitutes for the session extreme
    SESSION_EXT_TOL=0.0,  # pt; step extreme must be within this of the session
                          # extreme (0 = the step MADE the session extreme).
                          # <0 disables the filter. This is the anti-rotation gate.
    IMP_MIN=8.0,          # min impulse size (pt) — p25 of the measured population
    IMP_MAX=45.0,         # above this the "step" is a news spike, not a stair
    IMP_BARS_MAX=10,      # impulse must be an impulse, not a slow grind
    PAUSE_MIN=1,          # at least one bar of pause (never enter on the impulse bar)
    PAUSE_MAX=3,          # pause>3 bars => the step is dying (beat rate 38%->21%)
    RETR_MIN=0.20,        # below this we are at the tip => this IS the chase
    RETR_MAX=0.55,        # above this the "pause" is a reversal
    LSMA_SLOPE_MIN=0.15,  # pt/bar, LSMA must agree with the step direction
    REQUIRE_LSMA_SIDE=0,  # price must not have retraced through LSMA
    VOL_RATIO_MAX=1.10,   # pause volume must not exceed impulse volume
    REQUIRE_EXHAUST=0,    # entry bar must fail to extend the retrace
    STOP_BUF_FRAC=0.10,   # stop = pause extreme + 0.10*impulse
    STOP_MIN=2.5,         # pt — clamp so a 1-tick pause cannot make a 0.5pt stop
    STOP_MAX=9.0,         # pt — hard risk ceiling per contract
    T0_PT=3.0,            # C1 scratch target (fixed, matches live exec model)
    T1_FRAC=0.45,         # C2 — ~= back to the step low
    T2_FRAC=0.80,         # C3 — half a fresh step
    T3_FRAC=1.30,         # C4 — a full fresh step
    CUTOFF="15:00",       # no new entries after this ET time
    MAX_PER_DAY=4,
    BE_AFTER_T1=1,
    SLIP_TICKS=0.0,       # adverse fill vs the signal bar's close (live lag ~5 s)
)
for _k in list(P):
    _env = os.getenv(f"TSE_{_k}")
    if _env is not None:
        P[_k] = type(P[_k])(_env)


# ══════════════════════════════════════════════════════════════════
# Data
# ══════════════════════════════════════════════════════════════════
def load_days(since=SINCE, until=UNTIL) -> "OrderedDict[str, List[Dict]]":
    from backend.v9.db.read import read_all
    rows = read_all(
        "SELECT ts,open,high,low,close,volume,cci_14,cci_6_tcci,lsma_value,ema_34 "
        "FROM v9_bars_5min_woodies WHERE ts>=:a AND ts<:b ORDER BY ts",
        {"a": f"{since}T00:00:00+00:00", "b": f"{until}T23:59:59+00:00"})
    days: "OrderedDict[str, List[Dict]]" = OrderedDict()
    for r in rows or []:
        et = r["ts"].astimezone(ET)
        if not (RTH_OPEN <= et.time() < RTH_END):
            continue
        days.setdefault(et.strftime("%Y-%m-%d"), []).append({
            "et": et, "hhmm": et.strftime("%H:%M"),
            "o": float(r["open"]), "h": float(r["high"]),
            "l": float(r["low"]), "c": float(r["close"]),
            "v": int(r["volume"] or 0),
            "cci": None if r["cci_14"] is None else float(r["cci_14"]),
            "lsma": None if r["lsma_value"] is None else float(r["lsma_value"]),
        })
    return OrderedDict((d, b) for d, b in days.items() if len(b) >= 20)


def zigzag(bars: List[Dict], rev: float = 5.0):
    """Offline swing segmentation (anatomy only — the detector is causal)."""
    n = len(bars)
    if n < 3:
        return []
    hi_i, hi_p = 0, bars[0]["h"]
    lo_i, lo_p = 0, bars[0]["l"]
    piv, direction, start = [], 0, n
    for i in range(n):
        if bars[i]["h"] > hi_p:
            hi_i, hi_p = i, bars[i]["h"]
        if bars[i]["l"] < lo_p:
            lo_i, lo_p = i, bars[i]["l"]
        if hi_p - lo_p >= rev and hi_i != lo_i:
            if lo_i < hi_i:
                direction, piv = 1, [(lo_i, lo_p, "L")]
                hi_i, hi_p = lo_i, bars[lo_i]["h"]
                for j in range(lo_i, i + 1):
                    if bars[j]["h"] > hi_p:
                        hi_i, hi_p = j, bars[j]["h"]
            else:
                direction, piv = -1, [(hi_i, hi_p, "H")]
                lo_i, lo_p = hi_i, bars[hi_i]["l"]
                for j in range(hi_i, i + 1):
                    if bars[j]["l"] < lo_p:
                        lo_i, lo_p = j, bars[j]["l"]
            start = i + 1
            break
    if direction == 0:
        return []
    for i in range(start, n):
        b = bars[i]
        if direction == 1:
            if b["h"] > hi_p:
                hi_i, hi_p = i, b["h"]
            if i > hi_i and hi_p - b["l"] >= rev:
                piv.append((hi_i, hi_p, "H"))
                direction = -1
                lo_i, lo_p = i, b["l"]
                for j in range(hi_i + 1, i + 1):
                    if bars[j]["l"] < lo_p:
                        lo_i, lo_p = j, bars[j]["l"]
        else:
            if b["l"] < lo_p:
                lo_i, lo_p = i, b["l"]
            if i > lo_i and b["h"] - lo_p >= rev:
                piv.append((lo_i, lo_p, "L"))
                direction = 1
                hi_i, hi_p = i, b["h"]
                for j in range(lo_i + 1, i + 1):
                    if bars[j]["h"] > hi_p:
                        hi_i, hi_p = j, bars[j]["h"]
    piv.append((hi_i, hi_p, "H") if direction == 1 else (lo_i, lo_p, "L"))
    return piv


# ══════════════════════════════════════════════════════════════════
# The detector — causal: only bars[0..i] are ever read
# ══════════════════════════════════════════════════════════════════
def detect_trend_step(bars: List[Dict], i: int, p: Dict[str, Any]) -> Optional[Dict]:
    """Return a setup dict if bar `i` (already closed) is a TREND_STEP entry."""
    if i < 4:
        return None
    if bars[i]["hhmm"] > p["CUTOFF"]:
        return None
    # Causal swing state: zigzag over bars[0..i] only. The last element is the
    # running (unconfirmed) extreme, everything before it is confirmed.
    piv = zigzag(bars[:i + 1], float(p["ZZ_REV"]))
    if len(piv) < 2:
        return None

    for direction in ("SHORT", "LONG"):
        want = "L" if direction == "SHORT" else "H"
        # ── 1. the step extreme = most recent swing pivot of the right kind
        k = None
        for j in range(len(piv) - 1, -1, -1):
            if piv[j][2] == want:
                k = j
                break
        if k is None or k == 0:
            continue
        ext_i, ext_p, _ = piv[k]
        org_i, org_p, org_k = piv[k - 1]
        if org_k == want:
            continue
        imp = (org_p - ext_p) if direction == "SHORT" else (ext_p - org_p)
        if not (p["IMP_MIN"] <= imp <= p["IMP_MAX"]):
            continue
        if ext_i - org_i > p["IMP_BARS_MAX"] or ext_i <= org_i:
            continue

        # ── 1b. stair structure: the step must extend an existing staircase
        #        (SHORT: lower low AND lower high vs the previous swing pair)
        stair = None
        if k >= 3:
            prev_ext_p = piv[k - 2][1]
            prev_org_p = piv[k - 3][1]
            stair = ((ext_p < prev_ext_p and org_p < prev_org_p) if direction == "SHORT"
                     else (ext_p > prev_ext_p and org_p > prev_org_p))
        if p["REQUIRE_STAIR"] and not stair:
            continue

        # ── 1c. the step must be pushing the SESSION extreme, not rotating
        #        inside the range. This is the inverse of `extreme_chase_guard`:
        #        on a stair-step day, proximity to the session extreme IS the setup.
        if p["SESSION_EXT_TOL"] >= 0 and not (p.get("STAIR_OR_SESSION") and stair):
            if direction == "SHORT":
                sess = min(bars[j]["l"] for j in range(0, i + 1))
                if ext_p > sess + p["SESSION_EXT_TOL"]:
                    continue
            else:
                sess = max(bars[j]["h"] for j in range(0, i + 1))
                if ext_p < sess - p["SESSION_EXT_TOL"]:
                    continue

        # ── 3. pause geometry
        pause_bars = i - ext_i
        if not (p["PAUSE_MIN"] <= pause_bars <= p["PAUSE_MAX"]):
            continue
        if direction == "SHORT":
            pause_ext = max(bars[j]["h"] for j in range(ext_i, i + 1))
            retr = (pause_ext - ext_p) / imp
        else:
            pause_ext = min(bars[j]["l"] for j in range(ext_i, i + 1))
            retr = (ext_p - pause_ext) / imp
        if not (p["RETR_MIN"] <= retr <= p["RETR_MAX"]):
            continue

        # ── 4. trend agreement: LSMA slope + price still on the trend side of LSMA
        l_now, l_prev = bars[i]["lsma"], bars[max(0, i - 3)]["lsma"]
        if l_now is None or l_prev is None:
            continue
        slope = (l_now - l_prev) / 3.0
        if direction == "SHORT" and slope > -p["LSMA_SLOPE_MIN"]:
            continue
        if direction == "LONG" and slope < p["LSMA_SLOPE_MIN"]:
            continue
        if p["REQUIRE_LSMA_SIDE"]:
            if direction == "SHORT" and bars[i]["c"] > l_now:
                continue
            if direction == "LONG" and bars[i]["c"] < l_now:
                continue

        # ── 5. pause volume must not exceed impulse volume
        iv = [bars[j]["v"] for j in range(org_i + 1, ext_i + 1)]
        pv = [bars[j]["v"] for j in range(ext_i + 1, i + 1)]
        vol_ratio = (st.mean(pv) / st.mean(iv)) if (iv and pv and st.mean(iv)) else 1.0
        if vol_ratio > p["VOL_RATIO_MAX"]:
            continue

        # ── 6. exhaustion: this bar failed to extend the retrace
        if p["REQUIRE_EXHAUST"]:
            prev = bars[i - 1]
            if direction == "SHORT":
                if not (bars[i]["h"] <= prev["h"] and bars[i]["c"] <= prev["c"]):
                    continue
            else:
                if not (bars[i]["l"] >= prev["l"] and bars[i]["c"] >= prev["c"]):
                    continue

        # ── 7. prices.  Entry = the signal bar's close, optionally degraded by
        #      SLIP_TICKS in the ADVERSE direction to model the ~5 s live lag.
        entry = bars[i]["c"] + (-1 if direction == "SHORT" else 1) * p["SLIP_TICKS"] * TICK
        buf = max(2 * TICK, p["STOP_BUF_FRAC"] * imp)
        if direction == "SHORT":
            stop = pause_ext + buf
            risk = stop - entry
        else:
            stop = pause_ext - buf
            risk = entry - stop
        if risk <= 0:
            continue
        risk = min(max(risk, p["STOP_MIN"]), p["STOP_MAX"])
        sign = -1.0 if direction == "SHORT" else 1.0
        stop = round((entry - sign * risk) * 4) / 4
        tgts = [round((entry + sign * x) * 4) / 4 for x in (
            p["T0_PT"], p["T1_FRAC"] * imp, p["T2_FRAC"] * imp, p["T3_FRAC"] * imp)]
        # enforce a strictly increasing ladder
        for k in range(1, 4):
            if sign * (tgts[k] - tgts[k - 1]) < 0.5:
                tgts[k] = tgts[k - 1] + sign * 0.5
        return {
            "dir": direction, "i": i, "hhmm": bars[i]["hhmm"],
            "entry": entry, "stop": stop, "risk": round(risk, 2),
            "t0": tgts[0], "t1": tgts[1], "t2": tgts[2], "t3": tgts[3],
            "imp": round(imp, 2), "retr": round(retr, 3),
            "pause_bars": pause_bars, "imp_bars": ext_i - org_i,
            "step_id": ext_i, "slope": round(slope, 2),
            "vol_ratio": round(vol_ratio, 2),
            "org_i": org_i, "ext_p": ext_p, "pause_ext": pause_ext,
        }
    return None


# ══════════════════════════════════════════════════════════════════
# Execution model — 4 contracts: C1->T0(3pt) C2->T1 C3->T2 C4->T3,
# BE after T1, stop wins ambiguous bars, MTM at the last RTH bar.
# ══════════════════════════════════════════════════════════════════
def simulate(setup: Dict, future: List[Dict], be_after_t1: bool = True) -> Dict:
    d = setup["dir"]
    sign = 1.0 if d == "LONG" else -1.0
    entry, stop = setup["entry"], setup["stop"]
    tg = [setup["t0"], setup["t1"], setup["t2"], setup["t3"]]
    open_c, cur_stop, nxt = 4, stop, 0
    pnl, legs, bars_held = 0.0, [], 0
    mfe, mae = 0.0, 0.0
    for k, b in enumerate(future):
        bars_held = k + 1
        mfe = max(mfe, sign * (b["h"] - entry) if d == "LONG" else sign * (b["l"] - entry))
        mae = min(mae, sign * (b["l"] - entry) if d == "LONG" else sign * (b["h"] - entry))
        hit_stop = (b["l"] <= cur_stop) if d == "LONG" else (b["h"] >= cur_stop)
        if hit_stop:
            pnl += open_c * (cur_stop - entry) * sign
            legs.append("BE" if abs(cur_stop - entry) < 0.26 else "STOP")
            open_c = 0
            break
        while nxt < 4 and open_c > 0:
            t = tg[nxt]
            if (b["h"] >= t) if d == "LONG" else (b["l"] <= t):
                pnl += 1 * (t - entry) * sign
                open_c -= 1
                legs.append(f"T{nxt}")
                nxt += 1
                if nxt == 2 and be_after_t1:      # T1 filled -> stop to BE
                    cur_stop = entry
            else:
                break
        if open_c == 0:
            break
    if open_c > 0:
        last = future[bars_held - 1]["c"] if bars_held else entry
        pnl += open_c * (last - entry) * sign
        legs.append(f"MTM{open_c}")
    return {"pnl_pts": round(pnl, 2), "pnl_usd": round(pnl * MES, 2),
            "outcome": "+".join(legs) or "NONE", "bars_held": bars_held,
            "mfe": round(mfe, 2), "mae": round(mae, 2)}


def run(days, p=P) -> List[Dict]:
    trades: List[Dict] = []
    for d, bars in days.items():
        used_steps, n_day = set(), 0
        busy_until = -1
        for i in range(4, len(bars) - 1):
            if n_day >= p["MAX_PER_DAY"] or i <= busy_until:
                continue
            s = detect_trend_step(bars, i, p)
            if s is None:
                continue
            key = (s["dir"], s["step_id"])
            if key in used_steps:            # one entry per step, no re-entry
                continue
            used_steps.add(key)
            sim = simulate(s, bars[i + 1:], bool(p["BE_AFTER_T1"]))
            trades.append({"date": d, **s, **sim})
            n_day += 1
            busy_until = i + sim["bars_held"]   # no overlapping positions
    return trades


# ══════════════════════════════════════════════════════════════════
# Reporting
# ══════════════════════════════════════════════════════════════════
def money(x):
    return f"{'+' if x >= 0 else '-'}${abs(x):,.2f}"


def summarise(trades, label="", per_day=True):
    net = sum(t["pnl_usd"] for t in trades)
    n = len(trades)
    w = sum(1 for t in trades if t["pnl_usd"] > 0)
    comm = n * CONTRACTS * COMMISSION_RT
    print(f"\n### {label}   NET={money(net)}  n={n}  win={100*w/n if n else 0:.0f}%  "
          f"avg={money(net/n) if n else '$0'}")
    print(f"    after commission ({CONTRACTS}c x ${COMMISSION_RT:.2f} RT = "
          f"{money(-comm)}): {money(net - comm)}  "
          f"avg={money((net-comm)/n) if n else '$0'}")
    if not per_day or not trades:
        return net, n, w
    by = OrderedDict()
    for t in trades:
        by.setdefault(t["date"], []).append(t)
    print(f"{'date':12s} {'n':>2s} {'net':>10s}  outcomes")
    for d, ts in by.items():
        print(f"{d:12s} {len(ts):2d} {money(sum(x['pnl_usd'] for x in ts)):>10s}  "
              + ", ".join(f"{x['hhmm']}{x['dir'][0]}:{x['outcome']}" for x in ts))
    return net, n, w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anatomy", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--trades", action="store_true")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--since", default=SINCE)
    ap.add_argument("--until", default=UNTIL)
    a = ap.parse_args()

    days = load_days(a.since, a.until)
    print(f"sessions loaded: {len(days)}  ({list(days)[0]} .. {list(days)[-1]})")

    if a.anatomy:
        anatomy(days)
        return

    trades = run(days)
    summarise(trades, "TREND_STEP_ENTRY_V1 — baseline (4 contracts, $5/pt)")

    focus = {"2026-08-11": "stair-step DOWN", "2026-08-03": "trend UP",
             "2026-08-04": "trend UP (data ends 12:50)",
             "2026-08-06": "rotation/Neutral_Center", "2026-08-07": "rotation",
             "2026-08-10": "rotation/Neutral_Center"}
    print("\n### Focus days")
    for d, note in focus.items():
        ts = [t for t in trades if t["date"] == d]
        print(f"  {d} ({note:28s}) n={len(ts)}  {money(sum(t['pnl_usd'] for t in ts))}")

    if a.trades:
        print("\n### Blotter")
        hdr = (f"{'date':11s} {'time':5s} {'dir':5s} {'entry':>8s} {'stop':>8s} {'R':>5s} "
               f"{'imp':>6s} {'retr':>5s} {'pb':>2s} {'outcome':16s} {'pnl':>9s} "
               f"{'mfe':>6s} {'mae':>6s}")
        print(hdr)
        for t in trades:
            print(f"{t['date']:11s} {t['hhmm']:5s} {t['dir']:5s} {t['entry']:8.2f} "
                  f"{t['stop']:8.2f} {t['risk']:5.2f} {t['imp']:6.2f} {t['retr']:5.2f} "
                  f"{t['pause_bars']:2d} {t['outcome']:16s} {money(t['pnl_usd']):>9s} "
                  f"{t['mfe']:6.2f} {t['mae']:6.2f}")

    if a.validate:
        validate(days, trades)
    if a.sweep:
        sweep(days)
    if a.compare:
        compare(days)


def validate(days, trades):
    """Robustness checks — is the NET a real edge or two lucky trades?"""
    print("\n=== VALIDATION ===")
    ds = list(days)
    half = len(ds) // 2
    for name, sub in (("first half " + ds[0] + ".." + ds[half - 1], ds[:half]),
                      ("second half " + ds[half] + ".." + ds[-1], ds[half:])):
        ts = [t for t in trades if t["date"] in sub]
        net = sum(t["pnl_usd"] for t in ts)
        w = sum(1 for t in ts if t["pnl_usd"] > 0)
        print(f"  {name:34s} NET={money(net):>11s} n={len(ts):3d} "
              f"win={100*w/len(ts) if ts else 0:3.0f}%")

    pnl = sorted((t["pnl_usd"] for t in trades), reverse=True)
    net = sum(pnl)
    print(f"\n  NET={money(net)}  n={len(pnl)}")
    for k in (1, 2, 3, 5):
        print(f"  drop the {k} best trade(s): {money(net - sum(pnl[:k])):>11s}   "
              f"drop the {k} worst: {money(net - sum(pnl[-k:])):>11s}")
    print(f"  best={money(pnl[0])}  worst={money(pnl[-1])}  "
          f"median={money(pnl[len(pnl)//2])}")

    by = OrderedDict()
    for t in trades:
        by.setdefault(t["date"], 0.0)
        by[t["date"]] += t["pnl_usd"]
    dn = list(by.values())
    print(f"  profitable sessions: {sum(1 for x in dn if x > 0)}/{len(dn)}  "
          f"(sessions with >=1 trade)")
    eq, peak, mdd = 0.0, 0.0, 0.0
    for t in trades:
        eq += t["pnl_usd"]
        peak = max(peak, eq)
        mdd = min(mdd, eq - peak)
    print(f"  max drawdown (trade sequence): {money(mdd)}")

    print("\n  -- by realized day character (net displacement / RTH range) --")
    char = {}
    for d, bars in days.items():
        rng = max(b["h"] for b in bars) - min(b["l"] for b in bars)
        net_d = abs(bars[-1]["c"] - bars[0]["o"])
        char[d] = ("TREND" if (rng and net_d / rng >= 0.55) else
                   "SEMI" if (rng and net_d / rng >= 0.30) else "ROTATION")
    for lab in ("TREND", "SEMI", "ROTATION"):
        ds = [d for d in days if char[d] == lab]
        ts = [t for t in trades if char[t["date"]] == lab]
        net_l = sum(t["pnl_usd"] for t in ts)
        w = sum(1 for t in ts if t["pnl_usd"] > 0)
        print(f"    {lab:9s} sessions={len(ds):2d}  n={len(ts):3d}  NET={money(net_l):>11s}  "
              f"win={100*w/len(ts) if ts else 0:3.0f}%  "
              f"per-session={money(net_l/len(ds)) if ds else '$0'}")
    print("    " + "  ".join(f"{d[5:]}:{char[d][:4]}" for d in days))

    print("\n  -- by direction --")
    for d in ("LONG", "SHORT"):
        ts = [t for t in trades if t["dir"] == d]
        if ts:
            print(f"    {d:6s} n={len(ts):3d} NET={money(sum(t['pnl_usd'] for t in ts)):>11s} "
                  f"win={100*sum(1 for t in ts if t['pnl_usd']>0)/len(ts):3.0f}%")

    print("\n  -- outcome census --")
    cens = OrderedDict()
    for t in trades:
        cens[t["outcome"]] = cens.get(t["outcome"], 0) + 1
    for k, v in sorted(cens.items(), key=lambda x: -x[1]):
        sub = [t["pnl_usd"] for t in trades if t["outcome"] == k]
        print(f"    {k:20s} n={v:3d}  net={money(sum(sub)):>11s}")

    print("\n  -- flat-$ risk check: what if EVERY trade were a full stop? --")
    worst = sum(-4 * t["risk"] * MES for t in trades)
    print(f"    theoretical max loss if all {len(trades)} stopped: {money(worst)}  "
          f"(mean R = {st.mean([t['risk'] for t in trades]):.2f} pt "
          f"= {money(-4*st.mean([t['risk'] for t in trades])*MES)}/trade)")


def anatomy(days):
    """Step anatomy: impulse / pause / retrace / continuation, offline zigzag."""
    recs = []
    for d, bars in days.items():
        piv = zigzag(bars, 5.0)
        for k in range(len(piv) - 3):
            (a_i, a_p, a_k), (b_i, b_p, _), (c_i, c_p, _), (e_i, e_p, _) = piv[k:k + 4]
            direction = "SHORT" if a_k == "H" else "LONG"
            imp = abs(b_p - a_p)
            if imp <= 0:
                continue
            recs.append({
                "date": d, "dir": direction, "imp": imp, "imp_bars": b_i - a_i,
                "pause_bars": c_i - b_i, "retr": abs(c_p - b_p) / imp,
                "cont": abs(e_p - c_p),
                "beat": (e_p < b_p) if direction == "SHORT" else (e_p > b_p),
                "t0": bars[a_i]["hhmm"], "t1": bars[b_i]["hhmm"], "t2": bars[c_i]["hhmm"],
                "vol_r": (st.mean([bars[j]["v"] for j in range(b_i + 1, c_i + 1)] or [1]) /
                          max(1, st.mean([bars[j]["v"] for j in range(a_i + 1, b_i + 1)] or [1]))),
                "lsma_side": (None if bars[c_i]["lsma"] is None else
                              (bars[c_i]["c"] - bars[c_i]["lsma"])),
            })

    def qq(v, x):
        v = sorted(v)
        return v[min(len(v) - 1, int(x * len(v)))] if v else float("nan")

    print(f"\n=== STEP ANATOMY — {len(recs)} impulse->pause->continuation records ===")
    print(f"impulse pt    p25={qq([r['imp'] for r in recs],.25):5.2f} "
          f"med={qq([r['imp'] for r in recs],.5):5.2f} "
          f"p75={qq([r['imp'] for r in recs],.75):5.2f} "
          f"p90={qq([r['imp'] for r in recs],.9):5.2f}")
    print(f"pause bars    p25={qq([r['pause_bars'] for r in recs],.25)} "
          f"med={qq([r['pause_bars'] for r in recs],.5)} "
          f"p75={qq([r['pause_bars'] for r in recs],.75)} "
          f"p90={qq([r['pause_bars'] for r in recs],.9)}")
    print(f"retrace %     p25={100*qq([r['retr'] for r in recs],.25):3.0f} "
          f"med={100*qq([r['retr'] for r in recs],.5):3.0f} "
          f"p75={100*qq([r['retr'] for r in recs],.75):3.0f}")
    print(f"continuation  p25={qq([r['cont'] for r in recs],.25):5.2f} "
          f"med={qq([r['cont'] for r in recs],.5):5.2f} "
          f"p75={qq([r['cont'] for r in recs],.75):5.2f}")

    def bucket(name, key, edges):
        print(f"\n-- P(next leg beats the step extreme) by {name} --")
        for lo, hi in zip(edges, edges[1:]):
            sub = [r for r in recs if key(r) is not None and lo <= key(r) < hi]
            if not sub:
                continue
            print(f"   {lo:7.2f}..{hi:7.2f}  n={len(sub):3d}  "
                  f"beat={100*sum(r['beat'] for r in sub)/len(sub):3.0f}%  "
                  f"med_cont={qq([r['cont'] for r in sub],.5):5.2f}")

    bucket("impulse size", lambda r: r["imp"], [0, 8, 12, 18, 26, 200])
    bucket("pause bars", lambda r: r["pause_bars"], [0, 2, 3, 4, 6, 99])
    bucket("retrace frac", lambda r: r["retr"], [0, .2, .35, .5, .65, .8, 1.0, 99])
    bucket("pause/impulse volume", lambda r: r["vol_r"], [0, .6, .85, 1.1, 99])

    for d in ("2026-08-11", "2026-08-03", "2026-08-04", "2026-08-06", "2026-08-10"):
        sub = [r for r in recs if r["date"] == d]
        if not sub:
            continue
        print(f"\n-- {d} --")
        print(f"   {'dir':6s}{'imp0':7s}{'imp1':7s}{'pEnd':7s}{'imp':>7s}{'pb':>4s}"
              f"{'retr%':>7s}{'cont':>7s}{'beat':>6s}{'volR':>6s}")
        for r in sub:
            print(f"   {r['dir']:6s}{r['t0']:7s}{r['t1']:7s}{r['t2']:7s}{r['imp']:7.2f}"
                  f"{r['pause_bars']:4d}{100*r['retr']:7.1f}{r['cont']:7.2f}"
                  f"{str(r['beat']):>6s}{r['vol_r']:6.2f}")


def sweep(days):
    print("\n=== PARAMETER SENSITIVITY (one knob at a time) ===")
    base = dict(P)
    grid = {
        "ZZ_REV": [3.5, 4.0, 5.0, 6.0, 7.0],
        "REQUIRE_STAIR": [0, 1],
        "SESSION_EXT_TOL": [-1.0, 0.0, 1.0, 2.0, 4.0, 8.0],
        "MAX_PER_DAY": [2, 3, 4, 6],
        "RETR_MAX": [0.55, 0.65, 0.75, 0.85, 1.00],
        "RETR_MIN": [0.0, 0.10, 0.20, 0.30],
        "PAUSE_MAX": [2, 3, 4, 6],
        "IMP_MIN": [6.0, 8.0, 10.0, 12.0],
        "LSMA_SLOPE_MIN": [0.0, 0.10, 0.15, 0.25, 0.40],
        "REQUIRE_EXHAUST": [0, 1],
        "REQUIRE_LSMA_SIDE": [0, 1],
        "VOL_RATIO_MAX": [0.85, 1.10, 1.40, 9.0],
        "STOP_BUF_FRAC": [0.0, 0.10, 0.20, 0.35],
        "STOP_MAX": [6.0, 9.0, 12.0],
        "T1_FRAC": [0.30, 0.45, 0.60],
        "T2_FRAC": [0.60, 0.80, 1.00],
        "T3_FRAC": [1.00, 1.30, 1.80],
        "CUTOFF": ["14:00", "15:00", "15:30", "16:00"],
        "SLIP_TICKS": [0.0, 1.0, 2.0, 4.0],
        "BE_AFTER_T1": [0, 1],
    }
    for k, vals in grid.items():
        line = []
        for v in vals:
            p = dict(base); p[k] = v
            ts = run(days, p)
            net = sum(t["pnl_usd"] for t in ts)
            wr = 100 * sum(1 for t in ts if t["pnl_usd"] > 0) / len(ts) if ts else 0
            mark = "*" if v == base[k] else " "
            line.append(f"{mark}{v}: {money(net)} n={len(ts)} w={wr:.0f}%")
        print(f"  {k:18s} " + " | ".join(line))


def compare(days):
    """Head-to-head with the two earlier failures, same window + same exec model."""
    print("\n=== HEAD-TO-HEAD vs the two failed attempts (same 4-contract model) ===")
    rows = []
    try:
        from backend.v9.systems.five_min.patterns.pullback_retest import (
            detect_pullback_retest)
        tr = []
        for d, bars in days.items():
            ibh = max(b["h"] for b in bars[:12]); ibl = min(b["l"] for b in bars[:12])
            last, nday = -99, 0
            for i in range(12, len(bars) - 1):
                if i - last < 6 or nday >= 2:
                    continue
                dr, conf, info = detect_pullback_retest(
                    bars[:i + 1], ib_high=ibh, ib_low=ibl, ib_locked=True, session_min=i * 5)
                if dr is None:
                    continue
                sign = 1.0 if dr == "LONG" else -1.0
                s = {"dir": dr, "entry": info["entry_price"], "stop": info["stop"],
                     "t0": round((info["entry_price"] + sign * 3.0) * 4) / 4,
                     "t1": info["t1"], "t2": info["t2"],
                     "t3": info["t2"] + sign * abs(info["t2"] - info["t1"])}
                sim = simulate(s, bars[i + 1:])
                tr.append({"date": d, "hhmm": bars[i]["hhmm"], **s, **sim})
                last, nday = i, nday + 1
        rows.append(("RE_PULLBACK_ENTRY_V1 (C2)", tr))
    except Exception as e:
        print(f"  [warn] pullback_retest replay failed: {e}")
    try:
        os.environ["HIGHER_LOW_SECOND_TEST_V1"] = "1"   # process-local only
        import importlib
        import backend.v9.systems.five_min.patterns.higher_low_second_test as H
        importlib.reload(H)
        tr = []
        for d, bars in days.items():
            last, nday = -99, 0
            for i in range(12, len(bars) - 1):
                if i - last < 6 or nday >= P["MAX_PER_DAY"]:
                    continue
                dr, info = None, None
                for fn, dd in ((H.detect_higher_low_second_test_long, "LONG"),
                               (H.detect_higher_low_second_test_short, "SHORT")):
                    r = fn(bars[:i + 1])
                    if r[0] is not None:
                        dr, info = dd, r[2]
                        break
                if dr is None:
                    continue
                sign = 1.0 if dr == "LONG" else -1.0
                entry = info["entry_price"]
                anchor = info["L2"]                    # the structural second-test extreme
                stop = anchor - sign * 1.0             # HLST's own STOP_MARGIN = 1.0
                push = info["push_pts"]
                s = {"dir": dr, "entry": entry, "stop": stop,
                     "t0": round((entry + sign * 3.0) * 4) / 4,
                     "t1": round((entry + sign * 0.45 * push) * 4) / 4,
                     "t2": round((entry + sign * 0.80 * push) * 4) / 4,
                     "t3": round((entry + sign * 1.30 * push) * 4) / 4}
                sim = simulate(s, bars[i + 1:])
                tr.append({"date": d, "hhmm": bars[i]["hhmm"], **s, **sim})
                last, nday = i, nday + 1
        rows.append(("HIGHER_LOW_SECOND_TEST_V1", tr))
    except Exception as e:
        print(f"  [warn] HLST replay failed: {e}")
    rows.append(("TREND_STEP_ENTRY_V1", run(days)))
    for name, tr in rows:
        net = sum(t["pnl_usd"] for t in tr)
        w = sum(1 for t in tr if t["pnl_usd"] > 0)
        print(f"  {name:32s} NET={money(net):>12s}  n={len(tr):3d}  "
              f"win={100*w/len(tr) if tr else 0:3.0f}%  "
              f"avg={money(net/len(tr)) if tr else '$0':>9s}")


if __name__ == "__main__":
    main()
