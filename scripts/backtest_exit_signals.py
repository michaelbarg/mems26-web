#!/usr/bin/env python3
"""Backtest System 6 exit signals on real managed trades (2026-07-05).

For every closed trade since 2026-06-22, walk its bars from entry to exit and
ask: if we had EXITED the moment an exit-signal fired, how many points would we
have captured vs. what actually happened? Positive delta = the signal saved a
give-back; negative = it exited too early (cost on trend/continuation).

Read-only. Uses the REAL detectors (backend.v9.systems.system6_exit_signals).
Rigorously computable here: price_stall and opposite_patterns. failed_volume
needs the live CVD/level feed at each bar → deferred (noted), not faked.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras

from backend.v9.systems.system6_exit_signals import price_stall, opposite_patterns

DB = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
DOLLAR_PT = 5.0


def _pts(direction, entry, px):
    return (entry - px) if direction.upper() == "SHORT" else (px - entry)


def main():
    conn = psycopg2.connect(DB)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    cur = conn.cursor()
    cur.execute("""
        SELECT id, direction, entry_price, entry_ts, exit_ts, exit_price,
               pattern_id_at_entry
        FROM v9_trades
        WHERE entry_ts >= '2026-06-22' AND entry_price IS NOT NULL
              AND exit_price IS NOT NULL AND exit_ts IS NOT NULL
        ORDER BY entry_ts
    """)
    trades = cur.fetchall()
    cur.execute("SELECT ts, open, high, low, close FROM v9_bars_5min_woodies "
                "WHERE ts >= '2026-06-22' ORDER BY ts")
    bars = cur.fetchall()
    conn.close()

    # index all fires (trades) for the opposite-patterns signal
    fires = [(t["entry_ts"], t["direction"]) for t in trades]

    agg = defaultdict(lambda: dict(n=0, delta_pts=0.0, saved=0, hurt=0))

    for t in trades:
        d, entry = t["direction"], float(t["entry_price"])
        ets, xts = t["entry_ts"], t["exit_ts"]
        actual_exit = float(t["exit_price"])
        life = [b for b in bars if ets <= b["ts"] <= xts]
        if len(life) < 3:
            continue
        actual_pts = _pts(d, entry, actual_exit)

        # --- price_stall: first bar (walking forward) where it fires ---
        stall_px = None
        for i in range(3, len(life)):
            s = price_stall(direction=d, bars=life[:i + 1], lookback=6, stall_bars=3)
            if s.fired:
                stall_px = float(life[i]["close"])
                break
        if stall_px is not None:
            delta = _pts(d, entry, stall_px) - actual_pts
            a = agg["stall"]; a["n"] += 1; a["delta_pts"] += delta
            a["saved"] += int(delta > 0); a["hurt"] += int(delta < 0)

        # --- opposite_patterns: 2nd counter fire inside the trade's life ---
        counters = [ts for (ts, fdir) in fires
                    if ets < ts <= xts and str(fdir).upper() != d.upper()]
        if len(counters) >= 2:
            trig_ts = sorted(counters)[1]
            after = [b for b in life if b["ts"] >= trig_ts]
            if after:
                opp_px = float(after[0]["close"])
                delta = _pts(d, entry, opp_px) - actual_pts
                a = agg["opposite_patterns"]; a["n"] += 1; a["delta_pts"] += delta
                a["saved"] += int(delta > 0); a["hurt"] += int(delta < 0)

    hdr = f"{'signal':<20}{'n':>4}{'net_pts':>10}{'net_$/1c':>10}{'saved':>7}{'hurt':>6}{'avg_pts':>9}"
    print(hdr); print("-" * len(hdr))
    for k in ("stall", "opposite_patterns"):
        a = agg[k]
        if not a["n"]:
            print(f"{k:<20}{0:>4}{'—':>10}"); continue
        avg = a["delta_pts"] / a["n"]
        print(f"{k:<20}{a['n']:>4}{a['delta_pts']:>10.1f}{a['delta_pts']*DOLLAR_PT:>10.0f}"
              f"{a['saved']:>7}{a['hurt']:>6}{avg:>9.2f}")
    print("-" * len(hdr))
    print("net_pts>0 = exiting on the signal captured MORE than the actual exit "
          "(saved a give-back); <0 = exited too early.")
    print("failed_volume: deferred — needs live CVD/level at each bar (not faked).")


if __name__ == "__main__":
    main()
