"""Migration 024: Candidate Ledger identity columns (T-103, 2026-08-25).

Additive nullable columns on v9_five_min_setups and v9_woodies_signals so
JSONL ledger events can join to detection rows. Observability only.
No backfill. No third table. Historical rows stay NULL.

Run after snapshot:
  DATABASE_URL=postgresql://localhost/mems26 \
    python3 backend/v9/db/migrations/versions/024_candidate_ledger_columns.py

Idempotent: duplicate-column / duplicate-index errors are skipped.
"""
from __future__ import annotations

import os
import sys

from psycopg2.extensions import parse_dsn


COLUMNS = [
    ("candidate_id", "VARCHAR(64)"),
    ("detected_at", "TIMESTAMPTZ"),
    ("confirmed_at", "TIMESTAMPTZ"),
    ("source_pid", "INTEGER"),
    ("source_commit", "VARCHAR(40)"),
    ("policy_id", "VARCHAR(64)"),
]
TABLES = ("v9_five_min_setups", "v9_woodies_signals")


def _local_dsn(dsn: str) -> bool:
    try:
        params = parse_dsn(dsn)
    except Exception:
        return False
    if params.get("service") or os.getenv("PGSERVICE"):
        return False
    host = params.get("host") or os.getenv("PGHOST")
    hostaddr = params.get("hostaddr") or os.getenv("PGHOSTADDR")
    if hostaddr not in (None, "", "127.0.0.1", "::1"):
        return False
    if host in (None, "", "localhost", "127.0.0.1", "::1"):
        return True
    return str(host).startswith("/")


def _get_connection():
    db_url = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
    if not db_url.startswith("postgresql"):
        raise RuntimeError(f"Unsupported DB: {db_url}")
    if not _local_dsn(db_url):
        raise RuntimeError(
            "Migration 024 accepts local Postgres only "
            "(localhost/127.0.0.1/unix socket)")
    import psycopg2
    return psycopg2.connect(db_url)


def migrate() -> None:
    conn = _get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    for table in TABLES:
        for col_name, col_type in COLUMNS:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                print(f"  {table}.{col_name}: ADDED ({col_type})")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"  {table}.{col_name}: already exists — skip")
                else:
                    raise
        try:
            cur.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_candidate_id "
                f"ON {table} (candidate_id) WHERE candidate_id IS NOT NULL"
            )
            print(f"  {table}: unique candidate_id index OK")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  {table}: candidate_id index exists — skip")
            else:
                raise
    try:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_v9_five_min_setups_detected_pat_dir "
            "ON v9_five_min_setups (detected_at, pattern, direction)"
        )
        print("  v9_five_min_setups: detected_at index OK")
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise
    cur.close()
    conn.close()
    print("Migration 024 complete.")


if __name__ == "__main__":
    migrate()
    sys.exit(0)
