#!/usr/bin/env python3
"""Replay EXTREMES_AWARE_REALIZE_V1 on historical trades.

Compares extremes-aware target approach realize vs the base approach
realize: for each trade, computes session extremes from the bars up to
that point, and tests whether EXCESS/POOR would change the realize decision.

Usage:
  DATABASE_URL=postgresql://localhost/mems26 python3 scripts/replay_extremes_aware.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from scripts.flag_guard import parse_env
    for k, v in parse_env(str(ROOT / ".env")).items():
        os.environ.setdefault(k, v)
except Exception:
    pass


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2026-07-15")
    parser.add_argument("--until", default="2026-08-05")
    args = parser.parse_args()

    from backend.v9.db.read import read_all
    from backend.v9.systems.target_approach_realize import should_realize, ApproachState
    from backend.v9.systems.extremes_quality import classify_extremes_live
    from zoneinfo import ZoneInfo

    ET = ZoneInfo("America/New_York")

    print(f"Extremes-Aware Realize Replay: {args.since} → {args.until}")

    # Get all closed trades
    trades = read_all("""
        SELECT id, mode, direction, entry_price, stop, t1, t2, t3,
               t1_hit_ts, t2_hit_ts, t3_hit_ts,
               pnl_usd, outcome, exit_reason, entry_ts, exit_ts
        FROM v9_trades
        WHERE entry_ts >= :since AND entry_ts < :until_next
        AND state = 'CLOSED'
        ORDER BY entry_ts
    """, {
        "since": f"{args.since}T00:00:00+00:00",
        "until_next": f"{args.until}T23:59:59+00:00",
    })

    if not trades:
        print("No trades found")
        return

    print(f"Total trades: {len(trades)}")

    # Pre-fetch all session bars grouped by ET date
    all_bars = read_all("""
        SELECT ts, open, high, low, close, cci_14
        FROM v9_bars_5min_woodies
        WHERE ts >= :since AND ts < :until_next
        ORDER BY ts
    """, {
        "since": f"{args.since}T00:00:00+00:00",
        "until_next": f"{args.until}T23:59:59+00:00",
    })

    # Group bars by ET date
    bars_by_date = defaultdict(list)
    for b in (all_bars or []):
        try:
            ts = b["ts"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            et_date = ts.astimezone(ET).date()
            et_time = ts.astimezone(ET).time()
            # RTH only (09:30+)
            if et_time.hour >= 9 and (et_time.hour > 9 or et_time.minute >= 30):
                bars_by_date[et_date].append(b)
        except Exception:
            pass

    # Run both modes: base (no extremes) vs extremes-aware
    results_base = []
    results_aware = []

    for mode_label, flag_on in [("BASE", False), ("EXTREMES", True)]:
        os.environ["S6_TARGET_APPROACH_REALIZE_V1"] = "1"
        if flag_on:
            os.environ["EXTREMES_AWARE_REALIZE_V1"] = "1"
        else:
            os.environ.pop("EXTREMES_AWARE_REALIZE_V1", None)

        mode_results = []

        for t in trades:
            tid = t["id"]
            entry_ts = t["entry_ts"]
            exit_ts = t["exit_ts"]
            if not entry_ts or not exit_ts:
                continue

            # Determine ET date
            if isinstance(entry_ts, str):
                entry_ts_dt = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
            else:
                entry_ts_dt = entry_ts
            et_date = entry_ts_dt.astimezone(ET).date()
            session_bars = bars_by_date.get(et_date, [])

            # Get trade-window bars
            trade_bars = []
            for b in session_bars:
                ts = b["ts"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if ts >= entry_ts_dt and ts <= (exit_ts if not isinstance(exit_ts, str) else datetime.fromisoformat(exit_ts.replace("Z", "+00:00"))):
                    trade_bars.append(b)

            if len(trade_bars) < 2:
                continue

            # Compute extremes from all session bars up to each bar
            state = None
            realized = False
            realize_price = None
            realize_reason = None

            trade_dict = dict(t)
            trade_dict["t1_hit"] = t.get("t1_hit_ts") is not None

            for i, bar in enumerate(trade_bars):
                # Compute extremes from session bars up to this point
                bars_so_far = [b for b in session_bars
                               if (b["ts"] if not isinstance(b["ts"], str) else datetime.fromisoformat(b["ts"].replace("Z", "+00:00"))) <=
                               (bar["ts"] if not isinstance(bar["ts"], str) else datetime.fromisoformat(bar["ts"].replace("Z", "+00:00")))]

                extremes_dict = None
                if flag_on and len(bars_so_far) >= 3:
                    bar_dicts = [{"open": float(b["open"]), "high": float(b["high"]),
                                  "low": float(b["low"]), "close": float(b["close"])}
                                 for b in bars_so_far]
                    extremes_dict = classify_extremes_live(bar_dicts)

                should, reason, state = should_realize(
                    trade=trade_dict,
                    bar_high=float(bar["high"]),
                    bar_low=float(bar["low"]),
                    bar_close=float(bar["close"]),
                    approach_state=state,
                    cci_current=float(bar["cci_14"]) if bar.get("cci_14") is not None else None,
                    cci_previous=float(trade_bars[i-1]["cci_14"]) if i > 0 and trade_bars[i-1].get("cci_14") is not None else None,
                    extremes=extremes_dict,
                )
                if should:
                    realized = True
                    realize_price = float(bar["close"])
                    realize_reason = reason
                    break

            if not realized:
                continue

            actual_pnl = float(t["pnl_usd"] or 0)
            entry = float(t["entry_price"])
            direction = t["direction"]
            if direction == "LONG":
                realize_pnl = (realize_price - entry) * 5.0
            else:
                realize_pnl = (entry - realize_price) * 5.0

            delta = round(realize_pnl - actual_pnl, 2)
            mode_results.append({
                "id": tid, "mode": t["mode"], "direction": direction,
                "entry": entry, "actual_pnl": actual_pnl,
                "realize_pnl": round(realize_pnl, 2),
                "delta": delta, "reason": realize_reason,
            })

        if flag_on:
            results_aware = mode_results
        else:
            results_base = mode_results

    # Compare
    base_ids = {r["id"] for r in results_base}
    aware_ids = {r["id"] for r in results_aware}
    base_net = sum(r["delta"] for r in results_base)
    aware_net = sum(r["delta"] for r in results_aware)

    print(f"\n{'='*100}")
    print("EXTREMES-AWARE REALIZE REPLAY — COMPARISON")
    print(f"{'='*100}")
    print(f"Trades analyzed: {len(trades)}")
    print(f"\n--- BASE (S6_TARGET_APPROACH_REALIZE only) ---")
    print(f"Triggered: {len(results_base)} | NET delta: ${base_net:+.2f}")
    for r in results_base:
        print(f"  #{r['id']:4d} {r['mode']:6s} {r['direction']:5s} actual=${r['actual_pnl']:+.2f} → realize=${r['realize_pnl']:+.2f} delta=${r['delta']:+.2f}")

    print(f"\n--- EXTREMES-AWARE (+ EXCESS boost / POOR suppress) ---")
    print(f"Triggered: {len(results_aware)} | NET delta: ${aware_net:+.2f}")
    for r in results_aware:
        _marker = ""
        if r["id"] not in base_ids:
            _marker = " ← NEW (EXCESS boost)"
        print(f"  #{r['id']:4d} {r['mode']:6s} {r['direction']:5s} actual=${r['actual_pnl']:+.2f} → realize=${r['realize_pnl']:+.2f} delta=${r['delta']:+.2f}{_marker}")

    # Trades only in base (suppressed by POOR)
    suppressed = base_ids - aware_ids
    if suppressed:
        print(f"\n  Suppressed by POOR: {sorted(suppressed)}")

    # Trades only in aware (added by EXCESS)
    added = aware_ids - base_ids
    if added:
        print(f"  Added by EXCESS: {sorted(added)}")

    improvement = aware_net - base_net
    print(f"\n{'='*100}")
    print(f"BASE NET:    ${base_net:+.2f}")
    print(f"AWARE NET:   ${aware_net:+.2f}")
    print(f"IMPROVEMENT: ${improvement:+.2f}")
    go = aware_net > 0
    print(f"VERDICT: {'GO' if go else 'NO-GO'}")

    # Write report
    out = ROOT / "docs/reports/EXTREMES_AWARE_REALIZE_REPLAY.md"
    with open(out, "w") as f:
        f.write("# Extremes-Aware Realize Replay (Dalton Step 1)\n\n")
        f.write(f"Period: {args.since} → {args.until} ({len(trades)} trades)\n\n")
        f.write("## Comparison\n\n")
        f.write(f"| Mode | Triggered | NET delta |\n|---|---|---|\n")
        f.write(f"| BASE (approach-realize only) | {len(results_base)} | ${base_net:+.2f} |\n")
        f.write(f"| EXTREMES-AWARE (+EXCESS/POOR) | {len(results_aware)} | ${aware_net:+.2f} |\n")
        f.write(f"| **IMPROVEMENT** | | **${improvement:+.2f}** |\n\n")
        f.write(f"**VERDICT: {'GO' if go else 'NO-GO'}**\n\n")
        f.write("## Base Details\n\n")
        f.write("| ID | Mode | Dir | Actual | Realize | Delta | Reason |\n|---|---|---|---|---|---|---|\n")
        for r in results_base:
            f.write(f"| {r['id']} | {r['mode']} | {r['direction']} | ${r['actual_pnl']:.2f} | "
                    f"${r['realize_pnl']:.2f} | ${r['delta']:+.2f} | {(r['reason'] or '')[:50]} |\n")
        f.write("\n## Extremes-Aware Details\n\n")
        f.write("| ID | Mode | Dir | Actual | Realize | Delta | Reason |\n|---|---|---|---|---|---|---|\n")
        for r in results_aware:
            f.write(f"| {r['id']} | {r['mode']} | {r['direction']} | ${r['actual_pnl']:.2f} | "
                    f"${r['realize_pnl']:.2f} | ${r['delta']:+.2f} | {(r['reason'] or '')[:50]} |\n")
    print(f"\nReport: {out}")


if __name__ == "__main__":
    main()
