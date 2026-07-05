#!/usr/bin/env python3
"""Combined System 6 manager backtest (2026-07-05).

Simulates the full exit logic on real trades: HOLD while the pattern is intact
and one-timeframing; EXIT the moment structure breaks, or (when not a strong
hold) a proven exit signal fires (stall / 2 opposite patterns). Compares the
manager's exit to the ACTUAL exit.

Scope (honest): exit-TIMING comparison with a hard-stop floor (uses the trade's
recorded stop as the invalidation/stop). Walks up to 24 bars past entry so the
manager may hold LONGER or exit EARLIER than the real trade. CVD deferred
(noisy). Read-only; real detectors.
"""
import os
import sys
from collections import defaultdict
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras

from backend.v9.systems.system6_exit_signals import (
    hold_confirmation, price_stall, opposite_patterns,
)

DB = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
DOLLAR_PT = 5.0
MAX_BARS = 24


def _pts(direction, entry, px):
    return (entry - px) if direction.upper() == "SHORT" else (px - entry)


def main():
    conn = psycopg2.connect(DB)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    cur = conn.cursor()
    cur.execute("""
        SELECT id, direction, entry_price, stop, entry_ts, exit_ts, exit_price
        FROM v9_trades WHERE entry_ts >= '2026-06-22' AND entry_price IS NOT NULL
              AND stop IS NOT NULL AND exit_price IS NOT NULL AND exit_ts IS NOT NULL
        ORDER BY entry_ts
    """)
    trades = cur.fetchall()
    cur.execute("SELECT ts, high, low, close FROM v9_bars_5min_woodies "
                "WHERE ts >= '2026-06-22' ORDER BY ts")
    bars = cur.fetchall()
    conn.close()
    fires = [(t["entry_ts"], t["direction"]) for t in trades]

    agg = dict(n=0, delta=0.0, saved=0, hurt=0, held=0, exited_early=0)
    for t in trades:
        d, entry, stop = t["direction"], float(t["entry_price"]), float(t["stop"])
        ets = t["entry_ts"]
        window = [b for b in bars if ets <= b["ts"] <= ets + timedelta(minutes=5 * MAX_BARS)]
        if len(window) < 4:
            continue
        actual_pts = _pts(d, entry, float(t["exit_price"]))
        mgr_exit = None
        for i in range(3, len(window)):
            bar = window[i]
            hi, lo, cl = float(bar["high"]), float(bar["low"]), float(bar["close"])
            # hard stop floor
            if (d.upper() == "SHORT" and hi >= stop) or (d.upper() == "LONG" and lo <= stop):
                mgr_exit = stop; break
            seq = window[:i + 1]
            hold = hold_confirmation(direction=d, invalidation_level=stop, bars=seq)
            if hold.broke:
                mgr_exit = cl; break
            if not hold.continuing:
                stall = price_stall(direction=d, bars=seq, lookback=6, stall_bars=3)
                counters = [ts for (ts, fd) in fires
                            if ets < ts <= bar["ts"] and str(fd).upper() != d.upper()]
                opp = opposite_patterns(trade_direction=d,
                                        recent_fire_directions=["X"] * len(counters))
                if stall.fired or opp.fired:
                    mgr_exit = cl; break
        if mgr_exit is None:
            mgr_exit = float(window[-1]["close"])  # held to window end
        mgr_pts = _pts(d, entry, mgr_exit)
        delta = mgr_pts - actual_pts
        agg["n"] += 1; agg["delta"] += delta
        agg["saved"] += int(delta > 0.25); agg["hurt"] += int(delta < -0.25)

    print(f"{'trades':>8}{'net_pts':>10}{'net_$/1c':>10}{'net_$/3c':>10}{'better':>8}{'worse':>7}{'avg':>8}")
    print("-" * 61)
    n = agg["n"] or 1
    print(f"{agg['n']:>8}{agg['delta']:>10.1f}{agg['delta']*DOLLAR_PT:>10.0f}"
          f"{agg['delta']*DOLLAR_PT*3:>10.0f}{agg['saved']:>8}{agg['hurt']:>7}{agg['delta']/n:>8.2f}")
    print("-" * 61)
    print("net_pts>0 = the structure-based manager's exits beat the actual exits, "
          "summed over all trades. Exit-timing sim w/ hard-stop floor; CVD deferred.")


if __name__ == "__main__":
    main()
