#!/usr/bin/env python3
"""Backtest cvd_divergence (literature-correct volume exit) on real trades.

Compares to the raw counter_flow result (which was net-negative). If the
literature is right, divergence should be net-positive. Read-only, real detector.
"""
import os
import sys
from collections import defaultdict
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras

from backend.v9.systems.system6_exit_signals import cvd_divergence

DB = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
DOLLAR_PT = 5.0


def _pts(direction, entry, px):
    return (entry - px) if direction.upper() == "SHORT" else (px - entry)


def _r5(t):
    return t.replace(second=0, microsecond=0, minute=(t.minute // 5) * 5)


def main():
    conn = psycopg2.connect(DB)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    cur = conn.cursor()
    cur.execute("SELECT id, direction, entry_price, entry_ts, exit_ts, exit_price "
                "FROM v9_trades WHERE entry_ts >= '2026-06-22' AND entry_price IS NOT NULL "
                "AND exit_price IS NOT NULL AND exit_ts IS NOT NULL ORDER BY entry_ts")
    trades = cur.fetchall()
    cur.execute("SELECT ts, high, low, close FROM v9_bars_5min_woodies WHERE ts >= '2026-06-22' ORDER BY ts")
    bars = cur.fetchall()
    cur.execute("SELECT DISTINCT ON (ts) ts::timestamptz AS ts, cumulative FROM v9_bars_cumulative_delta "
                "WHERE ts::timestamptz >= '2026-06-22' AND cumulative IS NOT NULL ORDER BY ts, id")
    cvd = cur.fetchall()
    conn.close()

    bar_by = {_r5(b["ts"]): {"high": float(b["high"]), "low": float(b["low"]),
                             "close": float(b["close"])} for b in bars}
    cvd_by = {_r5(r["ts"]): float(r["cumulative"]) for r in cvd}

    agg = dict(n=0, delta=0.0, saved=0, hurt=0)
    for t in trades:
        d, entry = t["direction"], float(t["entry_price"])
        ets, xts = t["entry_ts"], t["exit_ts"]
        actual = _pts(d, entry, float(t["exit_price"]))
        keys = sorted(k for k in cvd_by if _r5(ets) <= k <= _r5(xts) and k in bar_by)
        if len(keys) < 4:
            continue
        seq_bars = [bar_by[k] for k in keys]
        seq_cvd = [cvd_by[k] for k in keys]
        exit_px = None
        for i in range(3, len(keys)):
            s = cvd_divergence(direction=d, bars=seq_bars[:i + 1], cvd_series=seq_cvd[:i + 1])
            if s.fired:
                exit_px = seq_bars[i]["close"]
                break
        if exit_px is None:
            continue
        delta = _pts(d, entry, exit_px) - actual
        agg["n"] += 1
        agg["delta"] += delta
        agg["saved"] += int(delta > 0.25)
        agg["hurt"] += int(delta < -0.25)

    print(f"{'signal':<16}{'n':>5}{'net_pts':>10}{'net_$/1c':>10}{'saved':>7}{'hurt':>6}{'avg':>8}")
    print("-" * 62)
    n = agg["n"] or 1
    print(f"{'cvd_divergence':<16}{agg['n']:>5}{agg['delta']:>10.1f}{agg['delta']*DOLLAR_PT:>10.0f}"
          f"{agg['saved']:>7}{agg['hurt']:>6}{agg['delta']/n:>8.2f}")
    print("-" * 62)
    print("compare: raw counter_flow was net-negative. Divergence = price new "
          "extreme not confirmed by CVD (literature ~70% pre-pullback on ES).")


if __name__ == "__main__":
    main()
