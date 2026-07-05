#!/usr/bin/env python3
"""Research: WHEN does opposing volume win, and is exiting there worth it?

Michael 2026-07-05: "תחקור מתי הווליום הנגדי מנצח ואז כדאי לצאת." Sweeps the
counter-flow threshold on real closed trades using the live CVD series
(v9_bars_cumulative_delta), and measures points captured vs the actual exit.
Read-only. Uses the real detector (counter_flow_wins).
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras

from backend.v9.systems.system6_exit_signals import counter_flow_wins

DB = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
DOLLAR_PT = 5.0
THRESHOLDS = [1000, 1500, 2000, 2500, 3000]
WINDOW = 2


def _pts(direction, entry, px):
    return (entry - px) if direction.upper() == "SHORT" else (px - entry)


def main():
    conn = psycopg2.connect(DB)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    cur = conn.cursor()
    cur.execute("""
        SELECT id, direction, entry_price, entry_ts, exit_ts, exit_price
        FROM v9_trades WHERE entry_ts >= '2026-06-22' AND entry_price IS NOT NULL
              AND exit_price IS NOT NULL AND exit_ts IS NOT NULL ORDER BY entry_ts
    """)
    trades = cur.fetchall()
    cur.execute("SELECT ts, close FROM v9_bars_5min_woodies WHERE ts >= '2026-06-22' ORDER BY ts")
    bars = cur.fetchall()
    cur.execute("""SELECT DISTINCT ON (ts) ts::timestamptz AS ts, cumulative
                   FROM v9_bars_cumulative_delta WHERE ts::timestamptz >= '2026-06-22'
                   AND cumulative IS NOT NULL ORDER BY ts, id""")
    cvd = cur.fetchall()
    conn.close()

    def _round5(t):
        return t.replace(second=0, microsecond=0, minute=(t.minute // 5) * 5)

    close_by = {}
    for b in bars:
        close_by[_round5(b["ts"])] = float(b["close"])
    cvd_by = {}
    for r in cvd:
        cvd_by[_round5(r["ts"])] = float(r["cumulative"])

    results = {}
    for thr in THRESHOLDS:
        agg = dict(n=0, delta=0.0, saved=0, hurt=0)
        for t in trades:
            d, entry = t["direction"], float(t["entry_price"])
            ets, xts = t["entry_ts"], t["exit_ts"]
            actual_pts = _pts(d, entry, float(t["exit_price"]))
            # build aligned (cvd, close) sequence over the trade life
            keys = sorted(k for k in cvd_by
                          if _round5(ets) <= k <= _round5(xts) and k in close_by)
            if len(keys) < WINDOW + 2:
                continue
            series = [cvd_by[k] for k in keys]
            exit_px = None
            for i in range(WINDOW, len(keys)):
                s = counter_flow_wins(direction=d, cvd_series=series[:i + 1],
                                      window=WINDOW, threshold=thr)
                if s.fired:
                    exit_px = close_by[keys[i]]
                    break
            if exit_px is None:
                continue
            delta = _pts(d, entry, exit_px) - actual_pts
            agg["n"] += 1; agg["delta"] += delta
            agg["saved"] += int(delta > 0); agg["hurt"] += int(delta < 0)
        results[thr] = agg

    hdr = f"{'threshold':>10}{'n':>5}{'net_pts':>10}{'net_$/1c':>10}{'saved':>7}{'hurt':>6}{'avg_pts':>9}"
    print(hdr); print("-" * len(hdr))
    for thr in THRESHOLDS:
        a = results[thr]
        if not a["n"]:
            print(f"{thr:>10}{0:>5}{'—':>10}"); continue
        print(f"{thr:>10}{a['n']:>5}{a['delta']:>10.1f}{a['delta']*DOLLAR_PT:>10.0f}"
              f"{a['saved']:>7}{a['hurt']:>6}{a['delta']/a['n']:>9.2f}")
    print("-" * len(hdr))
    print("counter CVD Δ over 2 bars against the position; net_pts>0 = exiting when "
          "opposing volume won beat the actual exit.")


if __name__ == "__main__":
    main()
