"""Migration 020: G1 trade context columns.

Adds 3 queryable columns to v9_trades for calibration cuts:
  - day_type_at_entry  (String 20, nullable, indexed)
  - pattern_id_at_entry (String 40, nullable, indexed)
  - session_at_entry    (String 20, nullable, indexed)

These promote data already in cross_context JSON into SQL-queryable columns.
No backfill — trades are truncated in the B-13 reset (start from 0).

Run:  python backend/v9/db/migrations/versions/020_g1_trade_context_columns.py
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
        ("day_type_at_entry", "VARCHAR(20)"),
        ("pattern_id_at_entry", "VARCHAR(40)"),
        ("session_at_entry", "VARCHAR(20)"),
    ]

    for col_name, col_type in columns:
        try:
            cur.execute(f"ALTER TABLE v9_trades ADD COLUMN {col_name} {col_type}")
            print(f"[020] Added column {col_name}")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"[020] Column {col_name} already exists — skipping")
            else:
                raise

        try:
            idx_name = f"ix_v9_trades_{col_name}"
            cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON v9_trades ({col_name})")
            print(f"[020] Index {idx_name} created/verified")
        except Exception as e:
            print(f"[020] Index for {col_name} warning: {e}")

    cur.close()
    conn.close()
    print("[020] Migration complete")


def downgrade() -> None:
    conn = _get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    for col_name in ("day_type_at_entry", "pattern_id_at_entry", "session_at_entry"):
        try:
            cur.execute(f"ALTER TABLE v9_trades DROP COLUMN IF EXISTS {col_name}")
            print(f"[020] Dropped column {col_name}")
        except Exception as e:
            print(f"[020] Drop {col_name} warning: {e}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    if "--down" in sys.argv:
        downgrade()
    else:
        migrate()
