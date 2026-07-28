#!/usr/bin/env python3
"""Close SHADOW trades left open from a previous session.

Why this exists (2026-07-28): 13 shadow rows from 07-27 were still OPEN the next
morning. Shadow trades are managed by bar_level_detector during the session; when
the backend restarts (or the detector stops before they resolve) they simply stay
FILLED/PARTIAL forever. They are not a trading risk — but they poison every
shadow statistic, which is exactly the data being used to judge the patterns.

HOW THEY ARE CLOSED — deliberately with NO outcome:

    state       → CLOSED
    exit_reason → STALE_UNRESOLVED
    exit_price  → NULL
    pnl_usd     → NULL   (left as-is if already set)

We do NOT mark them to the session close, and we do NOT replay the bars to guess
whether the stop or the target would have been hit. Both would manufacture a
winner or a loser that never existed — the precise failure Michael caught on
07-28 ("אתה לא לוקח נתונים או מציב נכונים"). An unresolved trade has no result;
`pnl_usd IS NULL` says so honestly and keeps them out of every SUM.

If a real outcome is wanted later, replay them through the detector — not here.

SAFETY: shadow only, and only rows created before today. Refuses everything else.
Dry-run by default; --apply to write.

    python3 scripts/close_stale_shadow.py            # show what would change
    python3 scripts/close_stale_shadow.py --apply    # do it
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

try:
    import psycopg2
except ImportError:
    sys.exit("psycopg2 not available")

DB = os.getenv("DATABASE_URL", "postgresql://localhost/mems26")
OPEN_STATES = ("CLOSED", "CANCELLED")   # anything NOT in here is "open"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write (default: dry-run)")
    ap.add_argument("--before", default=None,
                    help="only rows created before this date (default: today)")
    args = ap.parse_args()
    cutoff = args.before or date.today().isoformat()

    cn = psycopg2.connect(DB)
    cur = cn.cursor()
    cur.execute(
        "SELECT id, state, mode, direction, entry_price, pattern_id_at_entry, "
        "       created_at AT TIME ZONE 'Asia/Jerusalem' "
        "FROM v9_trades "
        "WHERE state NOT IN %s AND mode = 'shadow' AND created_at < %s "
        "ORDER BY id",
        (OPEN_STATES, cutoff))
    rows = cur.fetchall()
    if not rows:
        print("no stale shadow trades — nothing to do")
        return 0

    print(f"stale SHADOW trades created before {cutoff}:")
    for r in rows:
        print(f"   {r[0]:>4} {r[1]:<8} {r[3]:<5} entry={r[4]:<9} {str(r[5]):<16} {r[6]:%m-%d %H:%M}")

    # Guard: nothing non-shadow, nothing from today, may pass.
    cur.execute(
        "SELECT count(*) FROM v9_trades "
        "WHERE state NOT IN %s AND (mode <> 'shadow' OR created_at >= %s)",
        (OPEN_STATES, cutoff))
    other = cur.fetchone()[0]
    print(f"\nleft untouched (live/demo or created today): {other}")

    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply")
        return 0

    ids = [r[0] for r in rows]
    cur.execute(
        "UPDATE v9_trades SET state='CLOSED', exit_reason='STALE_UNRESOLVED', "
        "updated_at=now() "
        "WHERE id = ANY(%s) AND mode='shadow' AND state NOT IN %s",
        (ids, OPEN_STATES))
    n = cur.rowcount

    # A row that never filled and never hit anything but carries pnl_usd = 0 is
    # claiming "breakeven" when the truth is "unknown" — a small lie that still
    # counts as a non-loss in every win-rate. NULL it. A row with a REAL partial
    # (t1/t2/t3/stop timestamp present) keeps its realized P&L: that part of the
    # trade genuinely happened.
    cur.execute(
        "UPDATE v9_trades SET pnl_usd = NULL, updated_at = now() "
        "WHERE id = ANY(%s) AND exit_reason = 'STALE_UNRESOLVED' AND pnl_usd = 0 "
        "  AND t1_hit_ts IS NULL AND t2_hit_ts IS NULL "
        "  AND t3_hit_ts IS NULL AND stop_hit_ts IS NULL",
        (ids,))
    nulled = cur.rowcount
    cn.commit()
    print(f"\nclosed {n} shadow trade(s) as STALE_UNRESOLVED (no exit price)")
    print(f"nulled a fabricated 0.0 P&L on {nulled} of them "
          f"(rows with a real partial keep their realized P&L)")

    cur.execute("SELECT count(*) FROM v9_trades WHERE state NOT IN %s", (OPEN_STATES,))
    print(f"still open in books: {cur.fetchone()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
