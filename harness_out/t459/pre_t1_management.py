#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-459 — stop management BEFORE T1, replayed on the engine's own live trades (58 clean sessions,
baseline = today's live set: drive branch ON @1.5R). For every live trade in the harness outputs
(entry at the fired bar's close, stop_initial, t1_target) the exit is re-simulated on the 5-min bars
with a management variant. One contract, $5/pt, $2.60 RT, stop-first inside a bar (conservative).

Variants
  V0 none      : the current system — stop_initial until T1 or stop.
  VA be_1r     : once MFE ≥ 1R (bar extreme), stop → entry (break-even) from the next bar.
  VB lock75    : once MFE ≥ 0.75×T1dist, stop → entry ± 1 tick (locks +0.25).
  VC lock50    : once MFE ≥ 0.50×T1dist, stop → entry (BE).
  VD trail_1r  : once MFE ≥ 1R, stop → extreme of the last 3 bars ± 1 tick, tighten-only, every bar.
  VE t1_near   : T1 filled when price comes within 1 tick of the target (limit-order tolerance).
"""
import glob, json, os, sys, collections
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
from backend.v9.db.read import read_all
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem"); TICK = 0.25; COMM = 2.60
B = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "t458"))

def bars_of(d):
    rows = read_all("""select ts, high h, low l, close c from v9_bars_5min_woodies where symbol='MES'
      and (ts at time zone 'Asia/Jerusalem')::date = :d and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by ts""", {"d": d})
    return [dict(ts=r["ts"], h=float(r["h"]), l=float(r["l"]), c=float(r["c"])) for r in rows]

def simulate(after, short, ep, st0, t1, variant):
    R = abs(ep - st0); tdist = abs(t1 - ep); stop = st0; mfe = 0.0
    sign = -1.0 if short else 1.0
    for k, b in enumerate(after):
        fav = (ep - b["l"]) if short else (b["h"] - ep)
        hit_stop = (b["h"] >= stop) if short else (b["l"] <= stop)
        if hit_stop:                                   # stop first inside a bar (conservative)
            return ((ep - stop) if short else (stop - ep)), k, "STOP"
        tol = TICK if variant == "VE" else 0.0
        if fav >= tdist - tol:
            return tdist - tol, k, "T1"
        mfe = max(mfe, fav)
        # management for the NEXT bar
        if variant == "VA" and mfe >= R:
            stop = ep
        elif variant == "VB" and mfe >= 0.75 * tdist:
            stop = (ep - TICK) if short else (ep + TICK)
        elif variant == "VC" and mfe >= 0.5 * tdist:
            stop = ep
        elif variant == "VD" and mfe >= R:
            seq = after[max(0, k - 2):k + 1]
            cand = (max(x["h"] for x in seq) + TICK) if short else (min(x["l"] for x in seq) - TICK)
            stop = min(stop, cand) if short else max(stop, cand)
    last = after[-1]["c"]
    return ((ep - last) if short else (last - ep)), len(after) - 1, "EOD"

def main():
    files = sorted(glob.glob(os.path.join(B, "branch1_*.json")))
    trades = []
    for p in files:
        d = os.path.basename(p)[8:18]
        q = os.path.join(B, f"r15_{d}.json")
        j = json.load(open(q if os.path.exists(q) else p))
        for t in j.get("trades") or []:
            if not t.get("filled") or not t.get("stop_initial") or not t.get("t1_target"):
                continue
            trades.append(dict(d=d, cls=t["classification"], dir=t["direction"], ep=float(t["entry"]), st0=float(t["stop_initial"]),
                               t1=float(t["t1_target"]), fired=t["fired_il"], harness_pnl=t.get("pnl_usd"), harness_out=t.get("outcome")))
    bars = {d: bars_of(d) for d in sorted({t["d"] for t in trades})}
    variants = ["V0", "VA", "VB", "VC", "VD", "VE"]
    res = {v: [] for v in variants}
    near_miss = 0
    for t in trades:
        bs = bars[t["d"]]
        fired = datetime.strptime(t["d"] + " " + t["fired"][:8], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IL)
        bar_close = fired - timedelta(seconds=fired.second, minutes=fired.minute % 5)   # the closed bar's ts
        after = [b for b in bs if b["ts"] > bar_close.astimezone(bs[0]["ts"].tzinfo)] if bs else []
        if not after:
            continue
        short = t["dir"] == "SHORT"
        mfe_all = max(((t["ep"] - b["l"]) if short else (b["h"] - t["ep"])) for b in after[:60])
        if abs(t["t1"] - t["ep"]) - TICK <= mfe_all < abs(t["t1"] - t["ep"]):
            near_miss += 1
        for v in variants:
            pts, k, how = simulate(after, short, t["ep"], t["st0"], t["t1"], v)
            res[v].append(dict(**t, pts=pts, usd=pts * 5 - COMM, how=how))
    n = len(res["V0"])
    print(f"live trades replayed: {n} over {len(bars)} sessions · T1 missed by ≤1 tick (MFE within a tick of T1): {near_miss}")
    print(f"{'variant':10} {'Σ$':>9} {'win%':>5} {'STOP':>5} {'T1':>5} {'EOD':>5}  Δ vs V0")
    base = sum(r["usd"] for r in res["V0"])
    for v in variants:
        rows = res[v]; s = sum(r["usd"] for r in rows); w = sum(1 for r in rows if r["pts"] > 0)
        hows = collections.Counter(r["how"] for r in rows)
        print(f"{v:10} {s:+9.1f} {100*w/max(n,1):5.0f} {hows.get('STOP',0):5d} {hows.get('T1',0):5d} {hows.get('EOD',0):5d}  {s-base:+8.1f}")
    print("\nby producer (V0 → best variant):")
    bycls = collections.defaultdict(lambda: collections.defaultdict(float)); cnt = collections.Counter()
    for v in variants:
        for r in res[v]: bycls[r["cls"]][v] += r["usd"]
    for r in res["V0"]: cnt[r["cls"]] += 1
    for c, m in sorted(bycls.items(), key=lambda kv: -cnt[kv[0]]):
        best = max(m, key=lambda k: m[k])
        print(f"  {c:26s} n={cnt[c]:3d}  V0 {m['V0']:+8.1f}  " + "  ".join(f"{v} {m[v]:+7.1f}" for v in variants[1:]) + f"   best={best}")
    sanity = sum(1 for r in res["V0"] if (r["pts"] > 0) == (r["harness_out"] == "WIN"))
    print(f"\nsanity: V0 agrees with the harness outcome on {sanity}/{n} trades")
    json.dump({v: res[v] for v in variants}, open(os.path.join(os.path.dirname(__file__), "pre_t1_results.json"), "w"), default=str)

if __name__ == "__main__":
    main()
