#!/usr/bin/env python3
"""N1 — EDGE_FADE replay on truth bars from .scid (2026-08-02).

Runs the ARM→RELEASE edge-fade logic on scid-sourced truth bars for each
trading day. Reports armings, releases, entries, simulated P&L, MAE.

GO criterion: NET positive on truth bars + zero entries on Trend days.

Usage:
  python3 scripts/replay_edge_fade.py --scid ~/SierraChart/Data/MESU26_FUT_CME.scid
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta, datetime, timezone
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
from backend.v9.systems.edge_fade import (
    evaluate_edge_fade, build_edge_fade_setup, FADE_DAY_TYPES, ARM_WINDOW_BARS,
)

ET = ZoneInfo("America/New_York")
MES_POINT_VALUE = 5.0  # $/pt/contract


def classify_day_simple(bars):
    """Quick day-type classification from bars for replay purposes."""
    try:
        from backend.v9.systems.day_type.classifier_core import classify_session
        ib_bars = bars[:12] if len(bars) >= 12 else bars
        ib_h = max(b["h"] for b in ib_bars)
        ib_l = min(b["l"] for b in ib_bars)
        bar_dicts = [{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
                      "v": b.get("vol", 0)} for b in bars]
        result = classify_session(bars=bar_dicts, ib_high=ib_h, ib_low=ib_l,
                                  open_price=bars[0]["o"], is_eod=True)
        return result.get("day_type", "UNKNOWN")
    except Exception as e:
        return f"ERROR({e})"


def simulate_trade(entry, stop, t1, direction, future_bars):
    """Simulate a trade to T1 or stop, return (pnl_pts, mae_pts, outcome)."""
    sign = 1.0 if direction == "LONG" else -1.0
    mae = 0.0
    for b in future_bars:
        h, l = b["h"], b["l"]
        # MAE
        adverse = (entry - l) if direction == "LONG" else (h - entry)
        mae = max(mae, adverse)
        # Stop check
        if direction == "LONG" and l <= stop:
            return (stop - entry, mae, "STOP")
        if direction == "SHORT" and h >= stop:
            return (entry - stop, mae, "STOP")
        # T1 check
        if direction == "LONG" and h >= t1:
            return (t1 - entry, mae, "T1")
        if direction == "SHORT" and l <= t1:
            return (entry - t1, mae, "T1")
    return (0, mae, "OPEN")


def replay_day(bars_5min, day_date):
    """Replay one day through edge-fade. Returns list of trade results."""
    rth = rth_bars(bars_5min, day_date)
    if len(rth) < 12:
        return {"day": day_date.isoformat(), "bars": len(rth), "day_type": "INSUFFICIENT",
                "armings": 0, "entries": 0, "trades": [], "pnl_pts": 0}

    day_type = classify_day_simple(rth)
    results = {"day": day_date.isoformat(), "bars": len(rth), "day_type": day_type,
               "armings": 0, "entries": 0, "trades": [], "pnl_pts": 0}

    # D1-completion (03.08, cowork audit): the replay hard-gated on
    # FADE_DAY_TYPES and never passed `rib`, so EDGE_FADE_CONTAINED_NV_V1
    # was dead code here — the NV extension was UNPROVEN. Compute rib
    # (day range / IB width, IB = first 12 bars) and route contained-NV
    # days through when the flag is on, mirroring the live logic.
    import os as _os
    _ib = rth[:12]
    _ib_w = max(b["h"] for b in _ib) - min(b["l"] for b in _ib)
    _rng = max(b["h"] for b in rth) - min(b["l"] for b in rth)
    rib = round(_rng / _ib_w, 2) if _ib_w > 0 else 0.0
    results["rib"] = rib
    _nv_on = _os.getenv("EDGE_FADE_CONTAINED_NV_V1", "0").lower() in ("1", "true", "yes")
    _eligible = (day_type in FADE_DAY_TYPES
                 or (_nv_on and day_type == "Normal_Variation" and rib < 1.5))
    if not _eligible:
        return results

    fired = set()
    armed = {}  # direction → {bar_index, trigger}

    for i in range(6, len(rth)):
        window = rth[:i + 1]

        # Check for edge rejection → ARM
        trigger = evaluate_edge_fade(window, day_type, already_fired=fired, rib=rib)
        if trigger and trigger["direction"] not in armed:
            armed[trigger["direction"]] = {"bar_idx": i, "trigger": trigger}
            results["armings"] += 1

        # Check armed entries for release confirmation
        for d in list(armed):
            arm_info = armed[d]
            age = i - arm_info["bar_idx"]
            if age > ARM_WINDOW_BARS:
                del armed[d]
                continue

            # Release confirmation: price moves away from the edge
            # (simplified: close beyond the entry price in the trade direction)
            trig = arm_info["trigger"]
            cur = rth[i]
            cur_close = cur["c"]

            released = False
            if d == "LONG" and cur_close > trig["entry"] + 2.0:
                released = True
            elif d == "SHORT" and cur_close < trig["entry"] - 2.0:
                released = True

            if released:
                # Entry on this bar's close
                entry = cur_close
                setup = build_edge_fade_setup(trig)
                # Simulate the trade
                future = rth[i + 1:]
                pnl_pts, mae, outcome = simulate_trade(
                    entry, float(setup["stop"]), float(setup["t1"]),
                    d, future)
                results["entries"] += 1
                results["pnl_pts"] += pnl_pts
                trade = {
                    "bar": i, "ts": str(rth[i].get("ts", "")),
                    "direction": d, "entry": round(entry, 2),
                    "stop": setup["stop"], "t1": setup["t1"],
                    "pnl_pts": round(pnl_pts, 2),
                    "mae": round(mae, 2), "outcome": outcome,
                }
                results["trades"].append(trade)
                fired.add(trig["type"])
                del armed[d]

    return results


def main():
    parser = argparse.ArgumentParser(description="N1: EDGE_FADE truth replay")
    parser.add_argument("--scid", required=True)
    parser.add_argument("--since", default="2026-07-15")
    parser.add_argument("--until", default="2026-08-01")
    args = parser.parse_args()

    start = date.fromisoformat(args.since)
    end = date.fromisoformat(args.until)

    print(f"Reading {args.scid}...")
    raw = read_scid(os.path.expanduser(args.scid), start_date=start, end_date=end)
    all_bars = aggregate_5min(raw)
    print(f"Total: {len(raw)} raw, {len(all_bars)} 5-min bars")

    # Group by date
    from collections import defaultdict
    by_date = defaultdict(list)
    for b in all_bars:
        d = b["ts"].astimezone(ET).date()
        by_date[d].append(b)

    print(f"\n{'='*80}")
    print("EDGE_FADE TRUTH REPLAY")
    print(f"{'='*80}")
    print(f"{'Date':<12} {'DayType':<20} {'Bars':>4} {'Arms':>4} {'Entries':>4} {'P&L':>8} {'Trades'}")
    print("-" * 80)

    total_pnl = 0
    total_entries = 0
    trend_entries = 0
    all_results = []

    for d in sorted(by_date):
        if d < start or d > end:
            continue
        if d.weekday() >= 5:  # skip weekends
            continue

        result = replay_day(all_bars, d)
        all_results.append(result)
        total_pnl += result["pnl_pts"]
        total_entries += result["entries"]

        is_trend = "Trend" in result["day_type"]
        if is_trend and result["entries"] > 0:
            trend_entries += result["entries"]

        trades_str = " | ".join(
            f"{t['direction'][0]} @{t['entry']:.0f} →{t['outcome']}({t['pnl_pts']:+.1f}pt MAE={t['mae']:.1f})"
            for t in result["trades"]
        ) or "—"

        print(f"{result['day']:<12} {result['day_type']:<20} {result['bars']:>4} "
              f"{result['armings']:>4} {result['entries']:>4} {result['pnl_pts']:>+8.1f} {trades_str}")

    print(f"\n{'='*80}")
    print(f"NET P&L: {total_pnl:+.1f}pt (${total_pnl * MES_POINT_VALUE:+.0f} per contract)")
    print(f"Total entries: {total_entries}")
    print(f"Entries on Trend days: {trend_entries}")
    go = total_pnl > 0 and trend_entries == 0
    print(f"\nGO criterion: NET positive={total_pnl > 0} + zero-Trend-entries={trend_entries == 0}")
    print(f"VERDICT: {'GO' if go else 'NO-GO'}")

    # Write report
    out = ROOT / "docs/reports/EDGE_FADE_TRUTH_REPLAY_2026-08-02.md"
    with open(out, "w") as f:
        f.write("# EDGE_FADE Truth Replay (N1, 2026-08-02)\n\n")
        f.write(f"Source: {args.scid}\n")
        f.write(f"Period: {args.since} → {args.until}\n")
        f.write(f"NET P&L: {total_pnl:+.1f}pt (${total_pnl * MES_POINT_VALUE:+.0f}/contract)\n")
        f.write(f"Entries: {total_entries} | Trend entries: {trend_entries}\n")
        f.write(f"**VERDICT: {'GO' if go else 'NO-GO'}**\n\n")
        f.write("| Date | Day Type | Bars | Arms | Entries | P&L | Trades |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in all_results:
            trades = "; ".join(f"{t['direction'][0]}@{t['entry']:.0f}→{t['outcome']}({t['pnl_pts']:+.1f})" for t in r["trades"]) or "—"
            f.write(f"| {r['day']} | {r['day_type']} | {r['bars']} | {r['armings']} | {r['entries']} | {r['pnl_pts']:+.1f} | {trades} |\n")
    print(f"\nReport: {out}")


if __name__ == "__main__":
    main()
