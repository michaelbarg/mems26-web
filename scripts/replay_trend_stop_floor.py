#!/usr/bin/env python3
"""Replay TREND_STOP_FLOOR_V1 on truth bars — GO/NO-GO for enable.

For each day: classify, find trades in v9_trades, check if the floor
would have changed the stop, and simulate the impact.

Usage:
  python3 scripts/replay_trend_stop_floor.py --scid ~/SierraChart/Data/MESU26_FUT_CME.scid
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from scripts.flag_guard import parse_env
    for k, v in parse_env(str(ROOT / ".env")).items():
        os.environ.setdefault(k, v)
except Exception:
    pass

from scripts.rebuild_bar_truth import read_scid, aggregate_5min, rth_bars

ET = ZoneInfo("America/New_York")


def classify_day(bars):
    try:
        from backend.v9.systems.day_type.classifier_core import classify_session
        ib_bars = bars[:12]
        ib_h = max(b["h"] for b in ib_bars)
        ib_l = min(b["l"] for b in ib_bars)
        bar_dicts = [{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
                      "v": b.get("vol", 0)} for b in bars]
        result = classify_session(bars=bar_dicts, ib_high=ib_h, ib_low=ib_l,
                                  open_price=bars[0]["o"], is_eod=True)
        return result.get("day_type", "UNKNOWN"), result
    except Exception as e:
        return f"ERROR({e})", {}


def compute_floor(ib_width):
    return max(6.0, 0.15 * ib_width)


def simulate_with_floor(entry, orig_stop, floor_stop, t1, direction, future_bars):
    """Compare original vs floor stop outcomes."""
    results = {}
    for label, stop in [("original", orig_stop), ("floor", floor_stop)]:
        mae = 0.0
        outcome = "OPEN"
        pnl = 0.0
        for b in future_bars:
            h, l = b["h"], b["l"]
            adverse = (entry - l) if direction == "LONG" else (h - entry)
            mae = max(mae, adverse)
            if direction == "LONG" and l <= stop:
                pnl = stop - entry
                outcome = "STOP"
                break
            if direction == "SHORT" and h >= stop:
                pnl = entry - stop
                outcome = "STOP"
                break
            if direction == "LONG" and h >= t1:
                pnl = t1 - entry
                outcome = "T1"
                break
            if direction == "SHORT" and l <= t1:
                pnl = entry - t1
                outcome = "T1"
                break
        results[label] = {"pnl": round(pnl, 2), "mae": round(mae, 2), "outcome": outcome}
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scid", required=True)
    parser.add_argument("--since", default="2026-07-15")
    parser.add_argument("--until", default="2026-08-03")
    args = parser.parse_args()

    start = date.fromisoformat(args.since)
    end = date.fromisoformat(args.until)

    print(f"Reading {args.scid}...")
    raw = read_scid(os.path.expanduser(args.scid), start_date=start, end_date=end)
    all_bars = aggregate_5min(raw)

    from collections import defaultdict
    by_date = defaultdict(list)
    for b in all_bars:
        d = b["ts"].astimezone(ET).date()
        by_date[d].append(b)

    # Load trades from DB
    trades_by_date = defaultdict(list)
    try:
        from backend.v9.db.read import read_all
        trades = read_all(
            "SELECT id, direction, entry_price, stop, t1, mode, state, "
            "pnl_usd, outcome, quality, entry_ts "
            "FROM v9_trades WHERE mode IN ('demo', 'live') "
            "AND state = 'CLOSED' ORDER BY entry_ts", {})
        for t in trades:
            d = t["entry_ts"].date() if hasattr(t["entry_ts"], "date") else str(t["entry_ts"])[:10]
            trades_by_date[str(d)].append(t)
    except Exception as e:
        print(f"DB trade load failed: {e}")

    print(f"\n{'='*90}")
    print("TREND STOP FLOOR REPLAY")
    print(f"{'='*90}")
    print(f"{'Date':<12} {'DayType':<18} {'IB':>5} {'Floor':>6} {'Trades':>6} {'Delta':>8} {'Detail'}")
    print("-" * 90)

    total_delta = 0.0
    trend_delta = 0.0
    balance_delta = 0.0
    all_results = []

    for d in sorted(by_date):
        if d < start or d > end or d.weekday() >= 5:
            continue
        rth = rth_bars(all_bars, d)
        if len(rth) < 12:
            continue

        day_type, cls_result = classify_day(rth)
        ib_bars = rth[:12]
        ib_w = max(b["h"] for b in ib_bars) - min(b["l"] for b in ib_bars)
        floor = compute_floor(ib_w)
        is_trend = day_type.startswith("Trend")

        day_trades = trades_by_date.get(d.isoformat(), [])
        day_delta = 0.0
        details = []

        for t in day_trades:
            entry = float(t["entry_price"]) if t.get("entry_price") else None
            orig_stop = float(t["stop"]) if t.get("stop") else None
            t1 = float(t["t1"]) if t.get("t1") else None
            direction = t.get("direction", "")

            if not all([entry, orig_stop, t1]):
                continue

            orig_risk = abs(entry - orig_stop)
            with_trend = is_trend and (
                (direction == "LONG" and cls_result.get("direction", "").find("UP") >= 0) or
                (direction == "SHORT" and cls_result.get("direction", "").find("DOWN") >= 0)
            )

            if is_trend and with_trend and orig_risk < floor:
                sign = 1.0 if direction == "LONG" else -1.0
                new_stop = entry - sign * floor

                # Find the bar index closest to entry_ts
                entry_bar = None
                for i, b in enumerate(rth):
                    if b["h"] >= entry >= b["l"]:
                        entry_bar = i
                        break
                if entry_bar is None:
                    entry_bar = 0

                future = rth[entry_bar + 1:]
                sim = simulate_with_floor(entry, orig_stop, new_stop, t1, direction, future)
                delta = sim["floor"]["pnl"] - sim["original"]["pnl"]
                day_delta += delta
                details.append(
                    f"#{t['id']} {direction[0]} @{entry:.0f} stop {orig_risk:.1f}→{floor:.1f} "
                    f"orig={sim['original']['outcome']}({sim['original']['pnl']:+.1f}) "
                    f"floor={sim['floor']['outcome']}({sim['floor']['pnl']:+.1f}) Δ={delta:+.1f}")

        total_delta += day_delta
        if is_trend:
            trend_delta += day_delta
        else:
            balance_delta += day_delta

        detail_str = " | ".join(details) if details else "—"
        print(f"{d.isoformat():<12} {day_type:<18} {ib_w:>5.1f} {floor:>6.1f} {len(day_trades):>6} "
              f"{day_delta:>+8.1f} {detail_str}")

        all_results.append({
            "date": d.isoformat(), "day_type": day_type, "ib_w": ib_w,
            "floor": floor, "trades": len(day_trades), "delta": day_delta,
            "is_trend": is_trend, "details": details,
        })

    print(f"\n{'='*90}")
    print(f"Total P&L delta:   {total_delta:+.1f}pt")
    print(f"  Trend days:      {trend_delta:+.1f}pt")
    print(f"  Balance days:    {balance_delta:+.1f}pt")
    go = trend_delta > 0 and abs(balance_delta) < 0.01
    print(f"\nGO: trend-NET-positive={trend_delta > 0} + balance-zero-change={abs(balance_delta) < 0.01}")
    print(f"VERDICT: {'GO' if go else 'NO-GO'}")

    # Write report
    out = ROOT / "docs/reports/TREND_STOP_FLOOR_REPLAY_2026-08-04.md"
    with open(out, "w") as f:
        f.write(f"# Trend Stop Floor Replay (2026-08-04)\n\n")
        f.write(f"Total P&L delta: {total_delta:+.1f}pt\n")
        f.write(f"Trend: {trend_delta:+.1f}pt | Balance: {balance_delta:+.1f}pt\n")
        f.write(f"**VERDICT: {'GO' if go else 'NO-GO'}**\n\n")
        f.write("| Date | Type | IB | Floor | Trades | Delta | Detail |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in all_results:
            detail = "; ".join(r["details"][:3]) or "—"
            f.write(f"| {r['date']} | {r['day_type']} | {r['ib_w']:.0f} | {r['floor']:.1f} | "
                    f"{r['trades']} | {r['delta']:+.1f} | {detail} |\n")
    print(f"\nReport: {out}")


if __name__ == "__main__":
    main()
