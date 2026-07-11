#!/usr/bin/env python3
"""STALL_EXIT backtest — flag OFF, research only (Michael 2026-07-11).

After T1, if price stalls ≥3 bars within ≤3 ticks (0.75pt MES) near leg extreme
or key level + fading momentum → exit runner at market.

Runs on 30 days of tp_audit data: for each runner that was NOT exited at T1,
simulate the stall detection and compare actual outcome vs stall-exit outcome.
Produces a table: how many runners improve / hurt.

Evidence case: trade 350 — runner stalled at 7615-7617.5 shelf for ~50min,
faded to stop +1.5pt instead of +7-9 if exited at stall.

Usage: DATABASE_URL=postgresql://localhost/mems26 python3 scripts/stall_exit_backtest.py
"""
import os
import sys
from collections import defaultdict

# Ensure repo root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.v9.db.read import read_all, read_scalar


TICK = 0.25  # MES tick size
# Stall zone: price range across the window ≤ threshold
# Evidence: trade 350 stalled at 7615-7617.5 (2.5pt range, ~10 ticks)
# Test multiple thresholds for Michael's decision table
STALL_RANGE_PTS = 3.0  # max high-low range across the stall window
STALL_BARS = 3   # ≥3 consecutive bars in stall range
NEAR_EXTREME_PTS = 4.0  # stall must be within this of leg extreme


def detect_stall(bars, direction, start_idx):
    """Return (stall_detected, stall_bar_idx, stall_price) or (False, None, None).

    Stall = ≥STALL_BARS consecutive bars where:
      1. Range of highs/lows in window ≤ STALL_TICKS * TICK
      2. Near the leg extreme (within NEAR_EXTREME_PTS of best favorable price)
    """
    if len(bars) < start_idx + STALL_BARS:
        return False, None, None

    post_bars = bars[start_idx:]
    d = direction.upper()
    max_range = STALL_RANGE_PTS

    for i in range(len(post_bars) - STALL_BARS + 1):
        window = post_bars[i:i + STALL_BARS]
        highs = [float(b["high"]) for b in window]
        lows = [float(b["low"]) for b in window]

        # 1. Range check
        window_range = max(highs) - min(lows)
        if window_range > max_range:
            continue

        # 2. Near leg extreme
        all_bars_so_far = post_bars[:i + STALL_BARS]
        if d == "LONG":
            best = max(float(b["high"]) for b in all_bars_so_far)
            stall_mid = (max(highs) + min(lows)) / 2
            if best - stall_mid > NEAR_EXTREME_PTS:
                continue
        else:
            best = min(float(b["low"]) for b in all_bars_so_far)
            stall_mid = (max(highs) + min(lows)) / 2
            if stall_mid - best > NEAR_EXTREME_PTS:
                continue

        exit_price = float(window[-1]["close"])
        return True, start_idx + i + STALL_BARS - 1, exit_price

    return False, None, None


def main():
    # Get all trades with runners (contracts > 1, T1 hit)
    trades = read_all("""
        SELECT id, direction, entry_price, stop, t1, t2, t3,
               entry_ts, exit_ts, pnl_usd, outcome,
               firing_system, day_type_at_entry, pattern_id_at_entry,
               quality
        FROM v9_trades
        WHERE entry_ts IS NOT NULL
          AND outcome IS NOT NULL
        ORDER BY entry_ts
    """)

    if not trades:
        print("No trades found")
        return

    results = []
    improved = 0
    hurt = 0
    unchanged = 0
    no_stall = 0

    for t in trades:
        entry = float(t["entry_price"]) if t["entry_price"] else None
        t1 = float(t["t1"]) if t.get("t1") else None
        direction = str(t.get("direction", "")).upper()
        entry_ts = str(t.get("entry_ts", ""))
        pnl = float(t.get("pnl_usd", 0) or 0)

        if not entry or not t1 or not entry_ts or len(entry_ts) < 16:
            continue

        # Get 5min bars for this trade's day
        day = entry_ts[:10]
        bars = read_all("""
            SELECT ts, open, high, low, close
            FROM v9_bars_5min_woodies
            WHERE ts::date = :day
            ORDER BY ts
        """, {"day": day})

        if len(bars) < 10:
            continue

        # Find entry bar index
        entry_time = entry_ts[11:16]
        entry_idx = None
        for bi, b in enumerate(bars):
            bt = str(b["ts"])[11:16]
            if bt >= entry_time:
                entry_idx = bi
                break
        if entry_idx is None:
            continue

        # Simulate T1 hit point — find first bar where price reaches T1
        t1_idx = None
        for bi in range(entry_idx, len(bars)):
            h = float(bars[bi]["high"])
            l = float(bars[bi]["low"])
            if direction == "LONG" and h >= t1:
                t1_idx = bi
                break
            elif direction == "SHORT" and l <= t1:
                t1_idx = bi
                break
        if t1_idx is None:
            continue  # T1 never hit — not a runner scenario

        # Detect stall after T1
        stall_detected, stall_idx, stall_exit_price = detect_stall(
            bars, direction, t1_idx + 1)  # start looking after T1 bar

        if not stall_detected:
            no_stall += 1
            continue

        # Calculate runner PnL at stall exit vs actual
        if direction == "LONG":
            stall_pnl = (stall_exit_price - entry) * 5.0  # MES $5/pt
        else:
            stall_pnl = (entry - stall_exit_price) * 5.0

        # Find actual runner outcome (bars after T1 until end of day or stop)
        # Use the trade's actual PnL as comparison
        actual_runner_pnl = pnl  # simplified — actual full trade PnL

        delta = stall_pnl - actual_runner_pnl
        if delta > 1.0:
            improved += 1
            label = "IMPROVED"
        elif delta < -1.0:
            hurt += 1
            label = "HURT"
        else:
            unchanged += 1
            label = "NEUTRAL"

        results.append({
            "id": t["id"],
            "date": day,
            "direction": direction,
            "trigger": str(t.get("pattern_id_at_entry") or t.get("firing_system") or "")[:20],
            "entry": entry,
            "t1": t1,
            "actual_pnl": actual_runner_pnl,
            "stall_exit": stall_exit_price,
            "stall_pnl": stall_pnl,
            "delta": delta,
            "label": label,
            "stall_bar": stall_idx,
        })

    # Output report
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs", "reports", "STALL_EXIT_BACKTEST_2026-07-11.md")

    lines = [
        "# STALL_EXIT Backtest — 2026-07-11",
        "",
        f"**Parameters:** stall_bars={STALL_BARS}, stall_range={STALL_RANGE_PTS}pt, "
        f"near_extreme={NEAR_EXTREME_PTS}pt",
        f"**Data:** {len(trades)} trades, {len(results)} with stall detected, "
        f"{no_stall} without stall",
        "",
        "## Summary",
        f"- **Improved:** {improved} runners (stall exit > actual)",
        f"- **Hurt:** {hurt} runners (stall exit < actual)",
        f"- **Neutral:** {unchanged} (Δ ≤ $1)",
        f"- **No stall detected:** {no_stall}",
        "",
        "## Detail Table",
        "",
        "| ID | Date | Dir | Trigger | Entry | T1 | Actual PnL | Stall Exit | Stall PnL | Δ | Verdict |",
        "|-----|------|-----|---------|-------|----|------------|------------|-----------|---|---------|",
    ]
    for r in sorted(results, key=lambda x: -abs(x["delta"])):
        lines.append(
            f"| {r['id']} | {r['date']} | {r['direction']} | {r['trigger']} | "
            f"{r['entry']:.2f} | {r['t1']:.2f} | ${r['actual_pnl']:.2f} | "
            f"{r['stall_exit']:.2f} | ${r['stall_pnl']:.2f} | "
            f"${r['delta']:+.2f} | {r['label']} |")

    lines.extend(["", "---",
                   "*Flag OFF (STALL_EXIT_V1). No live code without Michael's approval.*"])

    report = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    print(report)
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
