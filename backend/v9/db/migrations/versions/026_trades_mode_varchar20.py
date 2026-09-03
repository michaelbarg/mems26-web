"""Migration 026: v9_trades.mode varchar(10) → varchar(20) (T-219, 2026-09-03).

T-219 writes `mode='shadow_blocked'` — **14 characters**. The column was
`character varying(10)`, so even with the `_capture_cross_context(setup)`
TypeError fixed, every shadow_blocked INSERT would have failed on
`value too long for type character varying(10)`.

Verified before the change (2026-09-03 23:3x, local PG):
    SELECT column_name,data_type,character_maximum_length
      FROM information_schema.columns
     WHERE table_name='v9_trades' AND column_name='mode';
    -> mode | character varying | 10
    SELECT mode,count(*) FROM v9_trades GROUP BY 1;
    -> demo 29 / live 165 / shadow 678   (no 'shadow_blocked' row has ever existed)

Widening a varchar is a non-rewriting, non-blocking ALTER in PostgreSQL and
cannot truncate existing data.

⚠️ LOCK SAFETY (learned the hard way, 2026-09-03 23:39): ALTER COLUMN TYPE needs
ACCESS EXCLUSIVE on v9_trades. The first attempt ran while the backend was up and
queued behind an `idle in transaction` session — which in turn blocked the
backend's own `SELECT id FROM v9_trades ...` for 98s (pg_stat_activity showed
wait_event_type='Lock'). It was cancelled with pg_cancel_backend and re-run with
the backend stopped. This script therefore sets a 5s `lock_timeout`: it fails
loudly instead of wedging the trading backend. Run it with the backend DOWN.

Run:  python backend/v9/db/migrations/versions/026_trades_mode_varchar20.py
Idempotent: re-running on an already-widened column is a no-op.
"""

from __future__ import annotations
import os

TARGET_LEN = 20
LOCK_TIMEOUT_MS = 5000


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
    # Never wedge the live backend behind an ACCESS EXCLUSIVE wait — fail fast.
    cur.execute(f"SET lock_timeout = '{LOCK_TIMEOUT_MS}ms'")
    cur.execute(
        "SELECT character_maximum_length FROM information_schema.columns "
        "WHERE table_name='v9_trades' AND column_name='mode'")
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("v9_trades.mode not found — wrong DB?")
    cur_len = row[0]
    if cur_len is not None and cur_len >= TARGET_LEN:
        print(f"  v9_trades.mode already varchar({cur_len}) — skip")
    else:
        cur.execute(
            f"ALTER TABLE v9_trades ALTER COLUMN mode TYPE varchar({TARGET_LEN})")
        print(f"  v9_trades.mode varchar({cur_len}) -> varchar({TARGET_LEN})")
    cur.close()
    conn.close()
    print("Migration 026 complete.")


if __name__ == "__main__":
    migrate()
