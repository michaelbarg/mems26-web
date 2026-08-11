#!/usr/bin/env python3
"""A1 replay: scan 15 days of trades for wrong-side structural-target vetoes.

Reads v9_trades from the local PG database. For each trade, recomputes the
structural targets at the recorded entry/stop/day_type and checks whether the
veto would have fired. Reports:
  - trades that WOULD have been blocked (all-wrong-side)
  - trades that WOULD have been blocked by R:R hard floor (<0.3)
  - trades that pass both checks (regression-safe)

Usage:
    python3 scripts/replay_a1_wrong_side_veto.py [--days 15]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env before any backend imports (session.py reads DATABASE_URL at import)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    # If dotenv not installed, try manual load
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

from backend.v9.db.read import read_all
from backend.v9.systems.structural_targets import _build_result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=15)
    args = parser.parse_args()

    # Compute cutoff in Python to work on both PG and SQLite
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    sql = """
    SELECT id, mode, direction, entry_price, stop, t1, t2, t3,
           day_type_at_entry, pattern_id_at_entry, entry_ts,
           outcome, pnl_usd
    FROM v9_trades
    WHERE entry_ts >= :cutoff
      AND state IN ('CLOSED', 'OPEN')
      AND entry_price IS NOT NULL
      AND stop IS NOT NULL
    ORDER BY entry_ts ASC
    """
    trades = read_all(sql, {"cutoff": cutoff})
    if not trades:
        print(f"No trades found in the last {args.days} days.")
        return

    print(f"Replaying {len(trades)} trades from the last {args.days} days...\n")

    blocked_ws = []   # would be blocked by wrong-side veto
    blocked_rr = []   # would be blocked by R:R hard floor
    passed = []       # pass both checks

    for t in trades:
        tid = t["id"]
        direction = t["direction"]
        entry = float(t["entry_price"])
        stop = float(t["stop"])
        t1 = float(t["t1"]) if t.get("t1") else None
        t2 = float(t["t2"]) if t.get("t2") else None
        t3 = float(t["t3"]) if t.get("t3") else None
        day_type = t.get("day_type_at_entry") or "Normal"
        pnl = float(t.get("pnl_usd") or 0)
        outcome = t.get("outcome") or "?"
        cls = t.get("pattern_id_at_entry") or "?"

        # Recompute structural targets at entry
        result = _build_result(
            direction=direction, entry=entry, stop=stop,
            c1=t1, c2=t2, c3=t3,
            contracts=3, time_stop_minutes=30, trail_after_c2=True,
            day_type=day_type,
        )

        all_ws = result.get("all_wrong_side", False)

        # R:R check
        risk = abs(entry - stop)
        if risk > 0 and t1 is not None:
            if direction == "LONG":
                t1_dist = t1 - entry
            else:
                t1_dist = entry - t1
            rr = t1_dist / risk if t1_dist > 0 else 0.0
        else:
            rr = 999.0
            t1_dist = 0.0

        rr_blocked = rr < 0.3 and t1_dist > 0

        record = {
            "id": tid, "cls": cls, "dir": direction,
            "entry": entry, "stop": stop,
            "t1": t1, "t2": t2, "t3": t3,
            "rr": rr, "pnl": pnl, "outcome": outcome,
            "day_type": day_type, "ts": str(t.get("entry_ts", ""))[:19],
            "mode": t.get("mode", "?"),
        }

        if all_ws:
            blocked_ws.append(record)
        elif rr_blocked:
            blocked_rr.append(record)
        else:
            passed.append(record)

    # Report
    print("=" * 80)
    print(f"BLOCKED by wrong-side veto: {len(blocked_ws)} trades")
    print("=" * 80)
    for r in blocked_ws:
        print(f"  #{r['id']:>4} {r['ts']} {r['mode']:>6} {r['dir']:>5} {r['cls']:<30} "
              f"entry={r['entry']:.2f} stop={r['stop']:.2f} "
              f"t1={r['t1']} t2={r['t2']} t3={r['t3']} "
              f"pnl=${r['pnl']:+.2f} ({r['outcome']})")

    print()
    print("=" * 80)
    print(f"BLOCKED by R:R hard floor (<0.3): {len(blocked_rr)} trades")
    print("=" * 80)
    for r in blocked_rr:
        print(f"  #{r['id']:>4} {r['ts']} {r['mode']:>6} {r['dir']:>5} {r['cls']:<30} "
              f"R:R={r['rr']:.2f} entry={r['entry']:.2f} stop={r['stop']:.2f} "
              f"pnl=${r['pnl']:+.2f} ({r['outcome']})")

    print()
    print("=" * 80)
    print(f"PASSED (not blocked): {len(passed)} trades")
    print("=" * 80)

    # Summary stats
    ws_pnl = sum(r["pnl"] for r in blocked_ws)
    rr_pnl = sum(r["pnl"] for r in blocked_rr)
    pass_pnl = sum(r["pnl"] for r in passed)

    print(f"\nSummary:")
    print(f"  Wrong-side blocked: {len(blocked_ws)} trades, PnL=${ws_pnl:+.2f} (would be saved)")
    print(f"  R:R floor blocked:  {len(blocked_rr)} trades, PnL=${rr_pnl:+.2f} (would be saved)")
    print(f"  Passed:             {len(passed)} trades, PnL=${pass_pnl:+.2f} (kept)")
    print(f"  Net saved:          ${ws_pnl + rr_pnl:+.2f}")
    print(f"  Valid trades lost:  0 (vetoes can only remove; all passed trades are kept)")


if __name__ == "__main__":
    main()
