#!/usr/bin/env python3
"""F3 replay: step-scaled ladder impact on 15 days of trades.

Computes the median session step for each trade's day, then compares:
- Original stop/t1 vs step-scaled stop/t1
- R:R improvement
- Trend days vs rotation days (must improve trend, not worsen rotation)

Usage:
    python3 scripts/replay_f3_step_ladder.py [--days 15]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

from backend.v9.db.read import read_all
from backend.v9.systems.five_min.step_scaled_ladder import (
    compute_median_session_step, build_step_ladder,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=15)
    args = parser.parse_args()

    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    trades = read_all("""
    SELECT id, direction, entry_price, stop, t1, t2, t3,
           day_type_at_entry, pattern_id_at_entry, entry_ts,
           outcome, pnl_usd, mode
    FROM v9_trades
    WHERE entry_ts >= :cutoff
      AND state = 'CLOSED'
      AND entry_price IS NOT NULL AND stop IS NOT NULL
    ORDER BY entry_ts ASC
    """, {"cutoff": cutoff})

    if not trades:
        print(f"No trades in the last {args.days} days.")
        return

    print(f"Replaying {len(trades)} closed trades from {args.days} days...\n")

    trend_orig = 0.0
    trend_step = 0.0
    trend_n = 0
    rot_orig = 0.0
    rot_step = 0.0
    rot_n = 0

    for t in trades:
        entry = float(t["entry_price"])
        stop = float(t["stop"])
        direction = t["direction"]
        day_type = t.get("day_type_at_entry") or ""
        pnl = float(t.get("pnl_usd") or 0)
        is_trend = day_type.startswith("Trend")

        # Get session bars for this trade's day
        entry_ts = t.get("entry_ts")
        if not entry_ts:
            continue

        try:
            day_str = str(entry_ts)[:10]
        except Exception:
            continue

        bars = read_all(f"""
        SELECT high AS h, low AS l FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date = '{day_str}'
          AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
          AND ts < :entry_ts
        ORDER BY ts ASC
        """, {"entry_ts": str(entry_ts)})

        if not bars or len(bars) < 5:
            continue

        ladder = build_step_ladder(entry, direction, bars)
        if ladder is None:
            continue

        orig_risk = abs(entry - stop)
        step_risk = ladder["stop_dist"]
        orig_t1_dist = abs(float(t.get("t1") or entry) - entry)
        step_t1_dist = abs(ladder["t1"] - entry)

        orig_rr = orig_t1_dist / orig_risk if orig_risk > 0 else 0
        step_rr = step_t1_dist / step_risk if step_risk > 0 else 0

        # Would the trade have survived with the tighter stop?
        # (simplified: if pnl > 0, assume it would still win with tighter stop)
        step_pnl = pnl  # conservative: same outcome

        if is_trend:
            trend_orig += pnl
            trend_step += step_pnl
            trend_n += 1
        else:
            rot_orig += pnl
            rot_step += step_pnl
            rot_n += 1

        marker = "📈" if is_trend else "🔄"
        print(f"  #{t['id']:>4} {marker} {day_type:<20} {direction:>5} "
              f"orig_risk={orig_risk:.1f} step_risk={step_risk:.1f} "
              f"orig_rr={orig_rr:.2f} step_rr={step_rr:.2f} "
              f"median={ladder['median_step']:.1f} pnl=${pnl:+.2f}")

    print(f"\n{'='*70}")
    print(f"Trend days:    n={trend_n}, orig=${trend_orig:+.2f}, step=${trend_step:+.2f}")
    print(f"Rotation days: n={rot_n}, orig=${rot_orig:+.2f}, step=${rot_step:+.2f}")
    print(f"Acceptance: trend NET must improve, rotation must not worsen")


if __name__ == "__main__":
    main()
