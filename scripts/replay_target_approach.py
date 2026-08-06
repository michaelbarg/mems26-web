#!/usr/bin/env python3
"""Replay S6_TARGET_APPROACH_REALIZE_V1 on historical trades.

For each trade that hit (or nearly hit) a target but ultimately didn't fill,
simulate whether the approach-realize rule would have captured profit that
was subsequently lost.

Usage:
  DATABASE_URL=postgresql://localhost/mems26 python3 scripts/replay_target_approach.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone
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

    # Force flag ON for replay
    os.environ["S6_TARGET_APPROACH_REALIZE_V1"] = "1"

    print(f"Target Approach Realize Replay: {args.since} → {args.until}")

    # Get all closed trades in window
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

    total_saved = 0.0
    total_cost = 0.0
    n_triggered = 0
    n_beneficial = 0
    n_premature = 0
    details = []

    for t in trades:
        tid = t["id"]
        entry_ts = t["entry_ts"]
        exit_ts = t["exit_ts"]
        if not entry_ts or not exit_ts:
            continue

        # Get bars between entry and exit
        bars = read_all("""
            SELECT ts, high, low, close, open, cci_14
            FROM v9_bars_5min_woodies
            WHERE ts >= :start AND ts <= :end
            ORDER BY ts
        """, {"start": str(entry_ts), "end": str(exit_ts)})

        if not bars or len(bars) < 3:
            continue

        # Get delta data for the same window
        deltas = read_all("""
            SELECT ts, direction FROM v9_bars_cumulative_delta
            WHERE ts >= :start AND ts <= :end
            ORDER BY ts
        """, {"start": str(entry_ts), "end": str(exit_ts)})
        delta_map = {}
        if deltas:
            for d in deltas:
                delta_map[str(d["ts"])[:16]] = d.get("direction")

        # Simulate bar-by-bar
        state = None
        realized = False
        realize_bar_idx = None
        realize_price = None
        realize_reason = None

        trade_dict = dict(t)
        trade_dict["t1_hit"] = t.get("t1_hit_ts") is not None

        for i, bar in enumerate(bars):
            ts_key = str(bar["ts"])[:16]
            delta_dir = delta_map.get(ts_key)
            prev_delta = delta_map.get(str(bars[i-1]["ts"])[:16]) if i > 0 else None

            should, reason, state = should_realize(
                trade=trade_dict,
                bar_high=float(bar["high"]),
                bar_low=float(bar["low"]),
                bar_close=float(bar["close"]),
                approach_state=state,
                cci_current=float(bar["cci_14"]) if bar.get("cci_14") is not None else None,
                cci_previous=float(bars[i-1]["cci_14"]) if i > 0 and bars[i-1].get("cci_14") is not None else None,
                delta_direction=delta_dir,
                delta_direction_prev=prev_delta,
            )
            if should:
                realized = True
                realize_bar_idx = i
                realize_price = float(bar["close"])
                realize_reason = reason
                break

        if not realized:
            continue

        # Compute P&L comparison
        actual_pnl = float(t["pnl_usd"] or 0)
        entry = float(t["entry_price"])
        direction = t["direction"]
        if direction == "LONG":
            realize_pnl = (realize_price - entry) * 5.0
        else:
            realize_pnl = (entry - realize_price) * 5.0

        delta = round(realize_pnl - actual_pnl, 2)
        n_triggered += 1

        if delta > 0:
            n_beneficial += 1
            total_saved += delta
        else:
            n_premature += 1
            total_cost += abs(delta)

        details.append({
            "id": tid, "mode": t["mode"], "direction": direction,
            "entry": entry, "actual_pnl": actual_pnl,
            "realize_pnl": round(realize_pnl, 2),
            "delta": delta, "reason": realize_reason,
            "outcome": t["outcome"],
        })

    # Summary
    net = total_saved - total_cost
    print(f"\n{'='*90}")
    print("S6 TARGET APPROACH REALIZE REPLAY")
    print(f"{'='*90}")
    print(f"Trades analyzed: {len(trades)}")
    print(f"Triggered: {n_triggered}")
    print(f"  Beneficial (saved profit): {n_beneficial} → +${total_saved:.2f}")
    print(f"  Premature (cost):          {n_premature} → -${total_cost:.2f}")
    print(f"  NET:                       ${net:+.2f}")
    print(f"\nVERDICT: {'GO' if net > 0 and n_triggered > 0 else 'NO-GO'}")

    print(f"\n{'ID':>5} {'Mode':>6} {'Dir':>5} {'Entry':>8} {'Actual':>8} {'Realize':>8} {'Delta':>8} {'Outcome':>7} Reason")
    print("-" * 90)
    for d in details:
        print(f"{d['id']:>5} {d['mode']:>6} {d['direction']:>5} {d['entry']:>8.2f} "
              f"${d['actual_pnl']:>7.2f} ${d['realize_pnl']:>7.2f} ${d['delta']:>+7.2f} "
              f"{d['outcome']:>7} {(d['reason'] or '')[:40]}")

    # Write report
    out = ROOT / "docs/reports/TARGET_APPROACH_REALIZE_REPLAY.md"
    with open(out, "w") as f:
        f.write("# S6 Target Approach Realize Replay\n\n")
        f.write(f"Period: {args.since} → {args.until}\n")
        f.write(f"Trades: {len(trades)} | Triggered: {n_triggered}\n")
        f.write(f"Beneficial: {n_beneficial} (+${total_saved:.2f}) | Premature: {n_premature} (-${total_cost:.2f})\n")
        f.write(f"**NET: ${net:+.2f}**\n")
        f.write(f"**VERDICT: {'GO' if net > 0 and n_triggered > 0 else 'NO-GO'}**\n\n")
        f.write("| ID | Mode | Dir | Entry | Actual | Realize | Delta | Outcome | Reason |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for d in details:
            f.write(f"| {d['id']} | {d['mode']} | {d['direction']} | {d['entry']:.2f} | "
                    f"${d['actual_pnl']:.2f} | ${d['realize_pnl']:.2f} | ${d['delta']:+.2f} | "
                    f"{d['outcome']} | {(d['reason'] or '')[:60]} |\n")
    print(f"\nReport: {out}")


if __name__ == "__main__":
    main()
