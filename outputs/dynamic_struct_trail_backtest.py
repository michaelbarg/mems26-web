#!/usr/bin/env python3
"""Backtest: DYNAMIC_STRUCT_TRAIL vs static trail on shadow history.

For each runner trade (T1 hit), replays the 5-min bars from entry to exit and
applies the consolidation detector. Reports: per day-type runner P&L delta.

Usage: python3 outputs/dynamic_struct_trail_backtest.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.v9.db.read import read_all, read_one
from backend.v9.services.trade_manager.consolidation import detect_consolidation

TICK = 0.25
ANCHOR_OFFSET_TICKS = 3


def replay_trade(trade):
    """Replay a single runner trade with dynamic struct trail.
    Returns (dynamic_exit_price, dynamic_pnl, n_reanchors)."""
    tid = trade["id"]
    direction = trade["direction"]
    entry = float(trade["entry_price"])
    initial_stop = float(trade["initial_stop"]) if trade["initial_stop"] else float(trade["final_stop"])
    risk = abs(entry - initial_stop)
    if risk <= 0:
        return None

    # Fetch 5-min bars between entry and exit
    bars_rows = read_all(
        "SELECT high, low, close FROM v9_bars_5min_woodies "
        "WHERE ts >= :entry AND ts <= :exit "
        "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
        "AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' "
        "ORDER BY ts",
        {"entry": str(trade["entry_ts"]), "exit": str(trade["exit_ts"])})
    if not bars_rows or len(bars_rows) < 3:
        return None

    bars = [{"high": float(b["high"]), "low": float(b["low"]), "close": float(b["close"])}
            for b in bars_rows]

    # Simulate dynamic trail
    current_stop = entry + TICK if direction == "LONG" else entry - TICK  # BE+1T after T1
    n_reanchors = 0
    dynamic_exit = None

    bars_since_anchor = []
    for bar in bars:
        h, l, c = bar["high"], bar["low"], bar["close"]

        # Check stop hit first
        if direction == "LONG" and l <= current_stop:
            dynamic_exit = current_stop
            break
        if direction == "SHORT" and h >= current_stop:
            dynamic_exit = current_stop
            break

        bars_since_anchor.append(bar)

        # Try consolidation detection
        zone = detect_consolidation(
            bars=bars_since_anchor, direction=direction,
            last_anchor_price=current_stop, entry_price=entry,
            initial_risk=risk, min_bars=3, max_range_atr_frac=0.5,
            min_advance_risk_mult=1.0, atr_14=risk * 2, range_floor_pts=2.0)

        if zone:
            if direction == "LONG":
                new_stop = round(zone["anchor_extreme"] - ANCHOR_OFFSET_TICKS * TICK, 2)
                new_stop = max(new_stop, entry + TICK)
                if new_stop > current_stop:
                    current_stop = new_stop
                    n_reanchors += 1
                    bars_since_anchor = []  # reset for next consolidation
            else:
                new_stop = round(zone["anchor_extreme"] + ANCHOR_OFFSET_TICKS * TICK, 2)
                new_stop = min(new_stop, entry - TICK)
                if new_stop < current_stop:
                    current_stop = new_stop
                    n_reanchors += 1
                    bars_since_anchor = []

    if dynamic_exit is None:
        # Trade ended by time_stop or T2/T3 — use the last bar's close
        dynamic_exit = bars[-1]["close"]

    if direction == "LONG":
        dynamic_pnl = (dynamic_exit - entry) * 12.50 * 2  # 2 runner contracts
    else:
        dynamic_pnl = (entry - dynamic_exit) * 12.50 * 2

    return {
        "dynamic_exit": dynamic_exit,
        "dynamic_pnl": round(dynamic_pnl, 2),
        "n_reanchors": n_reanchors,
        "dynamic_stop_at_end": current_stop,
    }


def main():
    trades = read_all(
        "SELECT id, direction, entry_price, "
        "  COALESCE((quality::json->>'initial_stop')::float, stop::float) AS initial_stop, "
        "  stop AS final_stop, exit_price, pnl_usd, exit_reason, "
        "  entry_ts, exit_ts, day_type_at_entry "
        "FROM v9_trades "
        "WHERE t1_hit_ts IS NOT NULL AND state = 'CLOSED' "
        "ORDER BY entry_ts", {})

    results_by_daytype = {}
    total_static = 0
    total_dynamic = 0
    replayed = 0

    print("=" * 90)
    print("DYNAMIC_STRUCT_TRAIL Backtest — shadow history runners")
    print("=" * 90)
    print(f"{'ID':>4} {'Dir':>5} {'DayType':>16} {'Static$':>9} {'Dynamic$':>9} "
          f"{'Delta$':>8} {'Reanchor':>8} {'ExitReason':>12}")
    print("-" * 90)

    for t in trades:
        result = replay_trade(t)
        if result is None:
            continue

        static_pnl = float(t["pnl_usd"])
        dynamic_pnl = result["dynamic_pnl"]
        delta = dynamic_pnl - static_pnl
        dt = t["day_type_at_entry"] or "UNKNOWN"

        if dt not in results_by_daytype:
            results_by_daytype[dt] = {"static": 0, "dynamic": 0, "count": 0}
        results_by_daytype[dt]["static"] += static_pnl
        results_by_daytype[dt]["dynamic"] += dynamic_pnl
        results_by_daytype[dt]["count"] += 1

        total_static += static_pnl
        total_dynamic += dynamic_pnl
        replayed += 1

        if abs(delta) > 10:  # only print meaningful deltas
            print(f"{t['id']:>4} {t['direction']:>5} {dt:>16} {static_pnl:>+9.0f} "
                  f"{dynamic_pnl:>+9.0f} {delta:>+8.0f} {result['n_reanchors']:>8} "
                  f"{t['exit_reason']:>12}")

    print("-" * 90)
    print(f"\n{'TOTAL':>26} {total_static:>+9.0f} {total_dynamic:>+9.0f} "
          f"{total_dynamic - total_static:>+8.0f}   ({replayed} trades replayed)")

    print(f"\n{'Day-Type Breakdown':>30}")
    print(f"{'DayType':>16} {'Count':>6} {'Static$':>9} {'Dynamic$':>9} {'Delta$':>8}")
    print("-" * 55)
    for dt in sorted(results_by_daytype.keys()):
        r = results_by_daytype[dt]
        print(f"{dt:>16} {r['count']:>6} {r['static']:>+9.0f} {r['dynamic']:>+9.0f} "
              f"{r['dynamic'] - r['static']:>+8.0f}")

    print(f"\nNOT-DONE: This replay uses v9_bars_5min_woodies (contiguous) between entry/exit.")
    print(f"The consolidation detector uses K=3, R=0.5×ATR, M=1.0×risk (defaults).")
    print(f"S4 variant params not applied (needs Michael's values).")


if __name__ == "__main__":
    main()
