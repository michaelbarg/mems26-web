#!/usr/bin/env python3
"""Verify CVD / delta / ATR data availability for opening-type research.

READ-ONLY. Does NOT modify the DB. Safe to run against the live 10GB
mems26_local.db: uses index-based queries (MIN/MAX(ts), ORDER BY ts DESC
LIMIT) and AVOIDS full-table COUNT(*) which scans the whole 10GB file.

Purpose: confirm the building blocks for the RESEARCH 01 opening classifier
exist AND are populated in recent data:
  - net_CVD          ← v9_bars_5min.cumulative_delta
  - per-bar delta    ← v9_bars_footprint.delta  (and 5min cumulative_delta diff)
  - PE = net_CVD / Σ|delta_i|   (path / persistence efficiency)
  - ask/bid signing  ← v9_bars_tick_reversal.ask_vol/bid_vol
  - ATR              ← computed from bars (NOT stored)

Usage:
    python3 scripts/research/verify_cvd_atr_availability.py
    python3 scripts/research/verify_cvd_atr_availability.py --db data/mems26_local.db
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys


def connect_ro(path: str) -> sqlite3.Connection:
    uri = f"file:{path}?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=10)
    db.execute("PRAGMA query_only=1")
    return db


def cols(db, table) -> list[str]:
    try:
        return [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


def one(db, sql):
    try:
        return db.execute(sql).fetchone()
    except Exception as e:
        return ("ERR", str(e)[:150])


def recent(db, sql):
    try:
        return db.execute(sql).fetchall()
    except Exception as e:
        return [("ERR", str(e)[:150])]


def section(title):
    print("\n" + "=" * 4 + " " + title + " " + "=" * 4)


def check_table(db, table, ts_col="ts"):
    """Index-friendly: span via MIN/MAX(ts), populated via last-N sample."""
    c = cols(db, table)
    if not c:
        print(f"[{table}] MISSING (table not found)")
        return c
    print(f"[{table}] columns: {', '.join(c)}")
    span = one(db, f"SELECT MIN({ts_col}), MAX({ts_col}) FROM {table}")
    print(f"  ts span: {span[0]}  ->  {span[1]}")
    return c


def populated_in_last_n(db, table, col, n=200, ts_col="ts"):
    """Fraction of last-N rows (by ts index) where col IS NOT NULL.
    Avoids full scan: ORDER BY ts DESC LIMIT n uses the ts index."""
    rows = recent(
        db,
        f"SELECT {col} FROM {table} ORDER BY {ts_col} DESC LIMIT {n}",
    )
    if rows and rows[0] and rows[0][0] == "ERR":
        return f"ERR: {rows[0][1]}"
    nn = sum(1 for r in rows if r[0] is not None)
    return f"{nn}/{len(rows)} non-null (last {n})"


def sample_pe_from_5min(db, n=12):
    """Illustrative PE from the last n 5-min bars using cumulative_delta diffs.
    per-bar delta_i = CVD_i - CVD_{i-1}; net_CVD = CVD_last - CVD_first;
    Σ|delta_i| = sum of abs diffs. PE = net_CVD / Σ|delta_i|.
    NOT session-aligned — proves the math is computable from stored data."""
    rows = recent(
        db,
        f"SELECT ts, cumulative_delta FROM v9_bars_5min "
        f"WHERE cumulative_delta IS NOT NULL ORDER BY ts DESC LIMIT {n}",
    )
    if not rows or (rows[0] and rows[0][0] == "ERR"):
        return None, "no cumulative_delta rows"
    rows = list(reversed(rows))  # chronological
    cds = [r[1] for r in rows]
    if len(cds) < 3:
        return None, "insufficient rows"
    deltas = [cds[i] - cds[i - 1] for i in range(1, len(cds))]
    net = cds[-1] - cds[0]
    abs_sum = sum(abs(d) for d in deltas)
    pe = (net / abs_sum) if abs_sum else float("nan")
    return {
        "bars": len(cds),
        "first_ts": rows[0][0], "last_ts": rows[-1][0],
        "net_CVD": round(net, 1), "abs_delta_sum": round(abs_sum, 1),
        "PE": round(pe, 3) if abs_sum else None,
    }, None


def sample_atr_5min(db, period=14):
    """Compute a 5-min ATR(period) from the last (period+1) bars.
    NOTE: ATR is NOT stored in the DB — this shows it must be derived."""
    rows = recent(
        db,
        f"SELECT ts, high, low, close FROM v9_bars_5min "
        f"ORDER BY ts DESC LIMIT {period + 1}",
    )
    if not rows or (rows[0] and rows[0][0] == "ERR") or len(rows) < 2:
        return None
    rows = list(reversed(rows))
    trs = []
    for i in range(1, len(rows)):
        h, l, pc = rows[i][1], rows[i][2], rows[i - 1][3]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(trs) / len(trs) if trs else None
    return round(atr, 2) if atr is not None else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/mems26_local.db")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"DB not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    size_gb = os.path.getsize(args.db) / 1e9
    print(f"DB: {args.db}  ({size_gb:.1f} GB)  [read-only, no full COUNT]")

    db = connect_ro(args.db)

    section("v9_bars_5min (net_CVD source)")
    if check_table(db, "v9_bars_5min"):
        print("  cumulative_delta:", populated_in_last_n(db, "v9_bars_5min", "cumulative_delta"))
        for r in recent(db, "SELECT ts, close, cumulative_delta FROM v9_bars_5min ORDER BY ts DESC LIMIT 5"):
            print("   ", r)

    section("v9_bars_footprint (per-bar delta + per-level)")
    if check_table(db, "v9_bars_footprint"):
        print("  delta: ", populated_in_last_n(db, "v9_bars_footprint", "delta"))
        print("  levels:", populated_in_last_n(db, "v9_bars_footprint", "levels"))
        for r in recent(db, "SELECT ts, delta, stacked_buy, stacked_sell FROM v9_bars_footprint ORDER BY ts DESC LIMIT 5"):
            print("   ", r)

    section("v9_bars_tick_reversal (ask/bid signing)")
    if check_table(db, "v9_bars_tick_reversal"):
        print("  ask_vol:", populated_in_last_n(db, "v9_bars_tick_reversal", "ask_vol"))
        print("  bid_vol:", populated_in_last_n(db, "v9_bars_tick_reversal", "bid_vol"))

    section("Illustrative PE (last 12 5-min bars — proves computability)")
    pe, err = sample_pe_from_5min(db)
    print("  ", pe if pe else f"ERR: {err}")

    section("ATR (NOT stored — derived from bars)")
    atr = sample_atr_5min(db)
    print(f"   5-min ATR(14) from last 15 bars = {atr}  "
          f"(daily ATR would need a daily-bar table — confirm separately)")

    section("VERDICT")
    print("  If cumulative_delta + footprint.delta show high non-null ratios and")
    print("  PE computed a real number above, the opening/CVD research is")
    print("  data-feasible. ATR must be derived (no stored column).")

    db.close()


if __name__ == "__main__":
    main()
