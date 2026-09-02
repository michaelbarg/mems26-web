#!/usr/bin/env python3
"""
SUPERSEDED (02.09): list-only, --apply branch was empty, filter missed #948.
Use scripts/t211_backfill_apply.py (ran 02.09, 15 rows, anchors verified).
T-211: backfill T0 remap on historical trades.

79 trades where BE_AFTER_REAL_T1_V1 remapped T1→T0 but the PnL was never
recalculated with the corrected target. Every money conclusion is biased ~20.5%.

Usage:
  python3 scripts/t211_t0_backfill.py              # dry-run (show before/after)
  python3 scripts/t211_t0_backfill.py --apply       # apply fixes (needs Michael ruling)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Load .env
_env_path = os.path.join(ROOT, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def main():
    from backend.v9.db.read import read_all

    # Find trades with T0 remap that might need PnL correction
    rows = read_all("""
        SELECT id, mode, direction, entry_price, stop, t1, t2, t3,
               t1_hit_ts, t2_hit_ts, t3_hit_ts,
               pnl_usd, pnl_r, outcome, exit_price,
               quality
        FROM v9_trades
        WHERE quality::text LIKE '%has_t0%'
          AND quality::text LIKE '%true%'
          AND state = 'CLOSED'
          AND mode IN ('live', 'demo')
        ORDER BY id
    """, {})

    print(f"=== T-211 T0 Backfill ===")
    print(f"Total T0-remapped closed live/demo trades: {len(rows)}")

    issues = []
    for r in rows:
        q = r["quality"] if isinstance(r["quality"], dict) else {}
        t0_pts = q.get("t0_target_pts")
        if t0_pts is None:
            continue

        # Check if T1 was hit but the PnL doesn't reflect T0 remap
        # The T0 remap means: what was called "T1" in the DLL is actually T0 (the scalp)
        # The real T1 is what the DLL called T2, etc.
        # If t1_hit_ts is set, the first leg was booked at t1 price — but that's
        # the T0 scalp, not the real T1. The PnL calculation would have used
        # the wrong target price for the first leg.
        if r["t1_hit_ts"] is not None:
            issues.append({
                "id": r["id"],
                "mode": r["mode"],
                "direction": r["direction"],
                "entry": r["entry_price"],
                "t1": r["t1"],  # This is the T0 scalp target
                "t0_pts": t0_pts,
                "pnl_usd": r["pnl_usd"],
                "outcome": r["outcome"],
            })

    print(f"Trades with T1 hit + T0 remap (potentially affected): {len(issues)}")
    print()

    if not issues:
        print("No affected trades found.")
        return

    for i in issues[:20]:
        print(f"  #{i['id']:>4} {i['mode']:6s} {i['direction']:6s} "
              f"entry={i['entry']:.2f} t1(=T0)={i['t1']} t0_pts={i['t0_pts']} "
              f"pnl=${i['pnl_usd'] or 0:.2f} outcome={i['outcome']}")

    if len(issues) > 20:
        print(f"  ... and {len(issues) - 20} more")

    if "--apply" not in sys.argv:
        print("\nDRY-RUN: no changes. Use --apply with Michael's ruling.")


import sys as _s; _s.stderr.write('SUPERSEDED — use t211_backfill_apply.py\n'); _s.exit(2)
if __name__ == "__main__":
    main()
