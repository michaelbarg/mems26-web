"""Migration 023: v9_trades pnl_sierra cross-check column (P9, 2026-07-22).

Adds pnl_sierra (DOUBLE PRECISION, nullable) — Sierra's own P&L from
trade_activity_events (CLOSED_TRADE_PNL). Does NOT replace pnl_usd (the
backend-computed P&L). The two values are cross-checked in the live_ledger
endpoint; divergence = investigation, not auto-correction.

Run:  python backend/v9/db/migrations/versions/023_pnl_sierra_column.py
Idempotent: duplicate-column errors are silently caught.
"""

from __future__ import annotations
import os


def _get_connection():
    db_url = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
    if db_url.startswith("postgresql"):
        import psycopg2
        return psycopg2.connect(db_url)
    raise RuntimeError(f"Unsupported DB: {db_url}")


def migrate() -> None:
    conn = _get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE v9_trades ADD COLUMN pnl_sierra DOUBLE PRECISION")
        print("  added pnl_sierra (DOUBLE PRECISION)")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("  pnl_sierra already exists — skip")
        else:
            raise
    cur.close()
    conn.close()
    print("Migration 023 complete.")


if __name__ == "__main__":
    migrate()
