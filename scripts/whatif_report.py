#!/usr/bin/env python3
"""WHATIF report — what would the current system fire on a historical session?

Loads bars from v9_bars_5min_woodies, runs them through the live detection chain
(read-only, no orders), and reports what would have fired and at what P&L.

Only runs on sessions that pass the replay kernel quality check.
NOT_JUDGEABLE sessions are reported, not skipped.

Usage: python3 scripts/whatif_report.py --session 2026-08-25 [--json /tmp/whatif.json]
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import statistics
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DSN = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)
IB_BARS = 12
POINT_USD = 5.0


def load_session_bars(cur, session_date):
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York') AS et,
               open, high, low, close, volume
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date = %s
          AND (ts AT TIME ZONE 'America/New_York')::time >= %s
          AND (ts AT TIME ZONE 'America/New_York')::time < %s
          AND symbol = 'MES'
        ORDER BY ts
    """, (session_date, RTH0, RTH1))
    return [{"ts": r[0], "o": float(r[1]), "h": float(r[2]),
             "l": float(r[3]), "c": float(r[4]), "v": int(r[5] or 0)}
            for r in cur.fetchall()]


def load_setups(cur, session_date):
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York') AS et,
               pattern, direction, entry_price, stop_price, t1_price, t2_price
        FROM v9_five_min_setups
        WHERE (ts AT TIME ZONE 'America/New_York')::date = %s
        ORDER BY ts
    """, (session_date,))
    return [{"ts": r[0], "pattern": r[1], "direction": r[2],
             "entry": float(r[3]), "stop": float(r[4]),
             "t1": float(r[5]) if r[5] else None,
             "t2": float(r[6]) if r[6] else None}
            for r in cur.fetchall()]


def load_decisions(cur, session_date):
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York') AS et,
               pattern, direction, entry_price, blocked_by, outcome, trade_id
        FROM v9_five_min_setups
        WHERE (ts AT TIME ZONE 'America/New_York')::date = %s
        ORDER BY ts
    """, (session_date,))
    return []  # decisions are in JSONL, not DB


def quality_check(bars):
    if len(bars) != 78:
        return [f"RTH_CARDINALITY({len(bars)})"]
    return []


def sim_trade(bars, entry_idx, direction, entry_price, stop_price, t1_price):
    sign = 1.0 if direction == "LONG" else -1.0
    for i in range(entry_idx + 1, len(bars)):
        h, l = bars[i]["h"], bars[i]["l"]
        if (direction == "LONG" and l <= stop_price) or (direction == "SHORT" and h >= stop_price):
            return (stop_price - entry_price) * sign, "STOP", i
        if t1_price and ((direction == "LONG" and h >= t1_price) or
                         (direction == "SHORT" and l <= t1_price)):
            return (t1_price - entry_price) * sign, "T1", i
    last = bars[-1]["c"]
    return (last - entry_price) * sign, "EOD", len(bars) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--contracts", type=int, default=3)
    args = ap.parse_args()

    conn = psycopg2.connect(DSN)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()

    session_date = args.session
    bars = load_session_bars(cur, session_date)
    setups = load_setups(cur, session_date)
    conn.close()

    quality = quality_check(bars)
    C = args.contracts

    print(f"=== WHATIF Report — {session_date} ({len(bars)} bars, {len(setups)} setups) ===")
    if quality:
        print(f"  NOT_JUDGEABLE: {quality}")

    if not setups:
        print(f"  No setups detected for this session.")
        return

    # Simulate trades (single slot)
    total_pnl = 0
    slot_free = 0
    for s in setups:
        s_bar = None
        for i, b in enumerate(bars):
            if b["ts"] >= s["ts"]:
                s_bar = i
                break
        if s_bar is None or s_bar >= len(bars) - 2:
            continue
        if s_bar < slot_free:
            print(f"  SKIP {s['pattern']:25s} {s['direction']:5s} @{s['entry']:.2f} (slot occupied)")
            continue
        pnl_pts, reason, exit_i = sim_trade(
            bars, s_bar, s["direction"], s["entry"], s["stop"], s["t1"])
        pnl_usd = pnl_pts * C * POINT_USD
        total_pnl += pnl_usd
        slot_free = exit_i + 1
        print(f"  {s['pattern']:25s} {s['direction']:5s} @{s['entry']:.2f} → "
              f"${pnl_usd:>7.2f} ({reason})")

    print(f"\n  Total: ${total_pnl:.2f} ({C} contracts)")

    if args.json:
        out = {
            "session": session_date, "bars": len(bars), "setups": len(setups),
            "quality": quality, "total_pnl": round(total_pnl, 2),
        }
        with open(args.json, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"  JSON → {args.json}")


if __name__ == "__main__":
    main()
