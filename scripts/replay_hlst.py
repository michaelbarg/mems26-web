#!/usr/bin/env python3
"""Replay Higher-Low Second Test (HLST) detector on historical 5-min RTH bars.

Walks each trading day bar-by-bar, runs the LONG and SHORT detectors on the
bars seen so far, simulates trades (entry/stop/T1), and scores outcomes by
scanning subsequent bars.

Usage:
  DATABASE_URL=postgresql://localhost/mems26 python3 scripts/replay_hlst.py
  python3 scripts/replay_hlst.py --since 2026-07-15 --until 2026-08-07
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── .env preamble (same as other replay scripts) ──────────────────────
try:
    from scripts.flag_guard import parse_env
    for k, v in parse_env(str(ROOT / ".env")).items():
        os.environ.setdefault(k, v)
except Exception:
    pass

# Enable the HLST flag BEFORE importing the detector (module-level _flag_on)
os.environ["HIGHER_LOW_SECOND_TEST_V1"] = "1"

TICK_VALUE = 12.50  # MES: $12.50 per point
T1_DIST = 4.0       # baseline target distance in points
STOP_MARGIN = 1.0   # stop margin beyond L2


def main():
    import argparse

    parser = argparse.ArgumentParser(description="HLST replay backtest")
    parser.add_argument("--since", default="2026-07-15")
    parser.add_argument("--until", default="2026-08-07")
    args = parser.parse_args()

    from backend.v9.db.read import read_all
    from backend.v9.systems.five_min.patterns.higher_low_second_test import (
        detect_higher_low_second_test_long,
        detect_higher_low_second_test_short,
    )
    from zoneinfo import ZoneInfo

    ET = ZoneInfo("America/New_York")

    since_str = args.since
    until_str = args.until

    print(f"HLST Replay: {since_str} -> {until_str}")
    print(f"T1 distance: {T1_DIST} pts | Stop margin: {STOP_MARGIN} pts")
    print("=" * 90)

    # ── Fetch all RTH bars in the date range ──────────────────────────
    all_bars = read_all("""
        SELECT ts, open, high, low, close, volume
        FROM v9_bars_5min_woodies
        WHERE ts >= :since AND ts < :until_next
          AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
          AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'
        ORDER BY ts
    """, {
        "since": f"{since_str}T00:00:00+00:00",
        "until_next": f"{until_str}T23:59:59+00:00",
    })

    if not all_bars:
        print("ERROR: no bars returned from DB. Check DATABASE_URL and date range.")
        sys.exit(1)

    print(f"Loaded {len(all_bars)} RTH 5-min bars\n")

    # ── Group bars by trading day (ET date) ───────────────────────────
    days: dict[str, list[dict]] = defaultdict(list)
    for bar in all_bars:
        ts = bar["ts"]
        if hasattr(ts, "astimezone"):
            et_dt = ts.astimezone(ET)
        else:
            from datetime import datetime, timezone
            et_dt = datetime.fromisoformat(str(ts)).astimezone(ET)
        day_key = et_dt.strftime("%Y-%m-%d")
        days[day_key].append(bar)

    sorted_days = sorted(days.keys())

    # ── Simulate bar-by-bar per day ───────────────────────────────────
    all_trades = []
    day_summaries = []

    for day_key in sorted_days:
        day_bars = days[day_key]
        day_trades = []
        seen_bars: list[dict] = []
        active_entry_bars: set[int] = set()  # dedup: bar index that triggered

        for i, bar in enumerate(day_bars):
            seen_bars.append(bar)

            if len(seen_bars) < 6:
                continue

            # Run both detectors on bars seen so far
            for detect_fn, direction_label in [
                (detect_higher_low_second_test_long, "LONG"),
                (detect_higher_low_second_test_short, "SHORT"),
            ]:
                direction, confidence, info = detect_fn(seen_bars)
                if direction is None:
                    continue

                # Dedup: only one trade per triggering bar index per direction
                dedup_key = (i, direction_label)
                if dedup_key in active_entry_bars:
                    continue
                active_entry_bars.add(dedup_key)

                entry = info["entry_price"]
                L2 = info["L2"]

                if direction_label == "LONG":
                    stop = L2 - STOP_MARGIN
                    t1 = entry + T1_DIST
                else:
                    stop = L2 + STOP_MARGIN
                    t1 = entry - T1_DIST

                stop_dist = abs(entry - stop)
                t1_dist = T1_DIST

                # ── Scan subsequent bars for outcome ──────────────
                outcome = "OPEN"
                pnl = 0.0
                exit_bar_idx = None

                for j in range(i + 1, len(day_bars)):
                    fb = day_bars[j]
                    fh = float(fb.get("high", fb.get("h", 0)))
                    fl = float(fb.get("low", fb.get("l", 0)))

                    if direction_label == "LONG":
                        # Check stop first (conservative)
                        if fl <= stop:
                            outcome = "LOSS"
                            pnl = -stop_dist * TICK_VALUE
                            exit_bar_idx = j
                            break
                        if fh >= t1:
                            outcome = "WIN"
                            pnl = t1_dist * TICK_VALUE
                            exit_bar_idx = j
                            break
                    else:  # SHORT
                        if fh >= stop:
                            outcome = "LOSS"
                            pnl = -stop_dist * TICK_VALUE
                            exit_bar_idx = j
                            break
                        if fl <= t1:
                            outcome = "WIN"
                            pnl = t1_dist * TICK_VALUE
                            exit_bar_idx = j
                            break

                # If neither hit by EOD, mark as SCRATCH (flat at close)
                if outcome == "OPEN":
                    last_close = float(day_bars[-1].get("close", day_bars[-1].get("c", 0)))
                    if direction_label == "LONG":
                        pnl = (last_close - entry) * TICK_VALUE
                    else:
                        pnl = (entry - last_close) * TICK_VALUE
                    outcome = "EOD_FLAT"

                trade = {
                    "day": day_key,
                    "bar_idx": i,
                    "direction": direction_label,
                    "entry": entry,
                    "stop": round(stop, 2),
                    "t1": round(t1, 2),
                    "L1": info["L1"],
                    "L2": L2,
                    "push_pts": info["push_pts"],
                    "recovery_pct": info["recovery_pct"],
                    "outcome": outcome,
                    "pnl": round(pnl, 2),
                    "confidence": confidence,
                    "ts": bar.get("ts", ""),
                }
                day_trades.append(trade)

        # ── Day summary ───────────────────────────────────────────────
        wins = sum(1 for t in day_trades if t["outcome"] == "WIN")
        losses = sum(1 for t in day_trades if t["outcome"] == "LOSS")
        eod = sum(1 for t in day_trades if t["outcome"] == "EOD_FLAT")
        day_pnl = sum(t["pnl"] for t in day_trades)
        n = len(day_trades)

        summary = {
            "day": day_key,
            "trades": n,
            "wins": wins,
            "losses": losses,
            "eod_flat": eod,
            "pnl": round(day_pnl, 2),
        }
        day_summaries.append(summary)
        all_trades.extend(day_trades)

    # ── Print results ─────────────────────────────────────────────────
    _print_results(day_summaries, all_trades)

    # ── Write report ──────────────────────────────────────────────────
    report_path = ROOT / "docs" / "reports" / "HLST_REPLAY_2026-08-09.md"
    _write_report(report_path, day_summaries, all_trades, since_str, until_str)
    print(f"\nReport written to {report_path}")


def _print_results(day_summaries, all_trades):
    """Print day-by-day summary table and net total to stdout."""
    hdr = f"{'Day':<12} {'Trades':>6} {'W':>4} {'L':>4} {'EOD':>4} {'P&L ($)':>10}"
    print(hdr)
    print("-" * len(hdr))

    for s in day_summaries:
        print(
            f"{s['day']:<12} {s['trades']:>6} {s['wins']:>4} "
            f"{s['losses']:>4} {s['eod_flat']:>4} {s['pnl']:>10.2f}"
        )

    print("-" * len(hdr))
    total_trades = sum(s["trades"] for s in day_summaries)
    total_wins = sum(s["wins"] for s in day_summaries)
    total_losses = sum(s["losses"] for s in day_summaries)
    total_eod = sum(s["eod_flat"] for s in day_summaries)
    total_pnl = sum(s["pnl"] for s in day_summaries)
    print(
        f"{'TOTAL':<12} {total_trades:>6} {total_wins:>4} "
        f"{total_losses:>4} {total_eod:>4} {total_pnl:>10.2f}"
    )

    if total_trades > 0:
        win_rate = total_wins / total_trades * 100
        avg_pnl = total_pnl / total_trades
        print(f"\nWin rate: {win_rate:.1f}%  |  Avg P&L/trade: ${avg_pnl:.2f}")

    # Detail trades
    print(f"\n{'='*90}")
    print("TRADE DETAIL")
    print(f"{'='*90}")
    detail_hdr = (
        f"{'Day':<12} {'Dir':<6} {'Entry':>8} {'Stop':>8} "
        f"{'T1':>8} {'L2':>8} {'Push':>6} {'Rec%':>5} {'Result':<10} {'P&L':>8}"
    )
    print(detail_hdr)
    print("-" * len(detail_hdr))
    for t in all_trades:
        print(
            f"{t['day']:<12} {t['direction']:<6} {t['entry']:>8.2f} "
            f"{t['stop']:>8.2f} {t['t1']:>8.2f} {t['L2']:>8.2f} "
            f"{t['push_pts']:>6.1f} {t['recovery_pct']*100:>5.0f}% "
            f"{t['outcome']:<10} {t['pnl']:>8.2f}"
        )


def _write_report(path, day_summaries, all_trades, since_str, until_str):
    """Write markdown report to docs/reports/."""
    total_trades = sum(s["trades"] for s in day_summaries)
    total_wins = sum(s["wins"] for s in day_summaries)
    total_losses = sum(s["losses"] for s in day_summaries)
    total_eod = sum(s["eod_flat"] for s in day_summaries)
    total_pnl = sum(s["pnl"] for s in day_summaries)
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
    avg_pnl = (total_pnl / total_trades) if total_trades > 0 else 0.0

    lines = [
        f"# HLST Replay Report — {since_str} to {until_str}",
        f"",
        f"Generated: 2026-08-09",
        f"",
        f"## Parameters",
        f"",
        f"- Detector: `detect_higher_low_second_test_long` / `_short`",
        f"- T1 distance: {T1_DIST} pts (${ T1_DIST * TICK_VALUE:.2f})",
        f"- Stop: L2 +/- {STOP_MARGIN} pt",
        f"- Tick value: ${TICK_VALUE:.2f}/pt (MES)",
        f"- RTH: 09:30-16:00 ET",
        f"- Source table: `v9_bars_5min_woodies`",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total trades | {total_trades} |",
        f"| Wins | {total_wins} |",
        f"| Losses | {total_losses} |",
        f"| EOD flat | {total_eod} |",
        f"| Win rate | {win_rate:.1f}% |",
        f"| Net P&L | ${total_pnl:.2f} |",
        f"| Avg P&L/trade | ${avg_pnl:.2f} |",
        f"",
        f"## Daily Breakdown",
        f"",
        f"| Day | Trades | W | L | EOD | P&L |",
        f"|-----|--------|---|---|-----|-----|",
    ]

    for s in day_summaries:
        lines.append(
            f"| {s['day']} | {s['trades']} | {s['wins']} | "
            f"{s['losses']} | {s['eod_flat']} | ${s['pnl']:.2f} |"
        )

    lines.extend([
        f"",
        f"## Trade Detail",
        f"",
        f"| Day | Dir | Entry | Stop | T1 | L2 | Push | Rec% | Result | P&L |",
        f"|-----|-----|-------|------|----|----|------|------|--------|-----|",
    ])

    for t in all_trades:
        lines.append(
            f"| {t['day']} | {t['direction']} | {t['entry']:.2f} | "
            f"{t['stop']:.2f} | {t['t1']:.2f} | {t['L2']:.2f} | "
            f"{t['push_pts']:.1f} | {t['recovery_pct']*100:.0f}% | "
            f"{t['outcome']} | ${t['pnl']:.2f} |"
        )

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
