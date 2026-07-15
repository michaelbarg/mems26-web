"""Migration 021: T4 contract columns (Michael 07-15, 4 contracts).

Adds t4 (Float) and t4_hit_ts (DateTime) to v9_trades for the 4th OCO pair.
No backfill needed — existing trades were 3-contract; t4 is NULL for them.

Run:  python backend/v9/db/migrations/versions/021_t4_contract_columns.py
Idempotent: duplicate-column errors are silently caught.
"""

from __future__ import annotations

import os
import sys


def _get_connection():
    """Connect to Postgres (local only per CLAUDE.md)."""
    db_url = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
    if db_url.startswith("postgresql"):
        import psycopg2
        return psycopg2.connect(db_url)
    raise RuntimeError(f"Unsupported DB: {db_url} — expected postgresql://localhost/mems26")


def migrate() -> None:
    conn = _get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    columns = [
        ("t4", "DOUBLE PRECISION"),
        ("t4_hit_ts", "TIMESTAMPTZ"),
    ]

    for col_name, col_type in columns:
        try:
            cur.execute(f"ALTER TABLE v9_trades ADD COLUMN {col_name} {col_type}")
            print(f"  added {col_name} ({col_type})")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"  {col_name} already exists — skip")
            else:
                raise

    cur.close()
    conn.close()
    print("Migration 021 complete.")


if __name__ == "__main__":
    migrate()
