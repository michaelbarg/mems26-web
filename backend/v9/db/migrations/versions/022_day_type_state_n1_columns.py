"""Migration 022: v9_day_type_state N1 observability columns (2026-07-17).

N1 RC#4 (docs/handoff/N1B_TRANSITIONS_DIAGNOSIS_2026-07-17.md §4/§5.5):
v9_day_type_state had NO direction/reason/sides columns — "Variation-DOWN" was
not even representable, so diagnosing the 07-15/07-16 missed transitions
required memory + replay. Adds the ADDITIVE observability columns the
backend/main.py single-writer publisher now fills from the canonical
classify_session result:

    direction  TEXT              -- strategy(leg), e.g. "with_extension(DOWN)"
    reason     TEXT              -- classifier's reason string
    sides      INTEGER           -- measured sides 0/1/2
    rib        DOUBLE PRECISION  -- measured range/IB ratio

No backfill — historical rows stay NULL (honest: the values were never
computed for them). Observability only; no gate reads these columns.

Run:  python backend/v9/db/migrations/versions/022_day_type_state_n1_columns.py
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


COLUMNS = [
    ("direction", "TEXT"),
    ("reason", "TEXT"),
    ("sides", "INTEGER"),
    ("rib", "DOUBLE PRECISION"),
]


def migrate() -> None:
    conn = _get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    for col_name, col_type in COLUMNS:
        try:
            cur.execute(f"ALTER TABLE v9_day_type_state ADD COLUMN {col_name} {col_type}")
            print(f"  added {col_name} ({col_type})")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"  {col_name} already exists — skip")
            else:
                raise

    cur.close()
    conn.close()
    print("Migration 022 complete.")


if __name__ == "__main__":
    migrate()
