"""Migration 019: archive tables + v9_session_meta + is_synthetic columns.

Run manually:  python backend/v9/db/migrations/versions/019_archive_and_session_meta.py

Idempotent: CREATE TABLE IF NOT EXISTS + duplicate-column errors silently caught.
"""

from __future__ import annotations

import sqlite3
import os
import sys
from typing import Optional


DB_PATH = os.environ.get(
    "V9_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "v9.db"),
)


def migrate(db_path: Optional[str] = None) -> None:
    path = db_path or DB_PATH
    print(f"[019] Connecting to {path}")
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    # ── 1. v9_session_meta ───────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS v9_session_meta (
            key        TEXT PRIMARY KEY,
            value      TEXT,
            updated_at TEXT
        )
    """)
    print("[019] v9_session_meta: OK")

    # Seed initial row (idempotent via INSERT OR IGNORE)
    cur.execute("""
        INSERT OR IGNORE INTO v9_session_meta (key, value, updated_at)
        VALUES ('last_rollover_date', '', datetime('now'))
    """)
    print("[019] Seeded last_rollover_date")

    # ── 2. v9_day_type_archive ───────────────────────────────────────
    # Same schema as v9_day_type_history + archived_at
    cur.execute("""
        CREATE TABLE IF NOT EXISTS v9_day_type_archive (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            date                  DATE    NOT NULL,
            day_type              VARCHAR(32) NOT NULL,
            status                VARCHAR(16),
            confidence            FLOAT,
            ib_high               FLOAT,
            ib_low                FLOAT,
            ib_width_ticks        INTEGER,
            opening_type          VARCHAR(32),
            locked_at             DATETIME,
            reasoning_notes       VARCHAR(1024),
            created_at            DATETIME,
            probability           FLOAT,
            directional_certainty VARCHAR(8),
            trading_confidence    VARCHAR(8),
            ib_width              FLOAT,
            ib_width_class        VARCHAR(8),
            active_zohar_rules    TEXT,
            last_updated_at       DATETIME,
            updated_at            DATETIME,
            archived_at           TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("[019] v9_day_type_archive: OK")

    # ── 3. v9_tpo_sessions_archive ───────────────────────────────────
    # Same schema as v9_tpo_sessions + archived_at
    cur.execute("""
        CREATE TABLE IF NOT EXISTS v9_tpo_sessions_archive (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT    NOT NULL,
            session_type  TEXT    NOT NULL,
            trading_date  TEXT    NOT NULL,
            opened_ts     DATETIME NOT NULL,
            closed_ts     DATETIME,
            poc_price     REAL,
            vah_price     REAL,
            val_price     REAL,
            range_high    REAL,
            range_low     REAL,
            total_volume  INTEGER,
            profile_shape TEXT,
            opening_type  TEXT,
            ib_high       REAL,
            ib_low        REAL,
            ib_locked     INTEGER DEFAULT 0,
            letter_count  INTEGER DEFAULT 0,
            archived_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("[019] v9_tpo_sessions_archive: OK")

    # ── 4. v9_woodies_signals_archive ────────────────────────────────
    # Same schema as v9_woodies_signals + archived_at
    cur.execute("""
        CREATE TABLE IF NOT EXISTS v9_woodies_signals_archive (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT NOT NULL,
            bar_id      TEXT,
            cci_14      REAL,
            cci_prev    REAL,
            signal_type TEXT,
            direction   TEXT,
            strength    INTEGER,
            reasoning   TEXT,
            session     TEXT,
            created_at  TEXT NOT NULL,
            archived_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("[019] v9_woodies_signals_archive: OK")

    # ── 5-8. is_synthetic columns ────────────────────────────────────
    # ALTER TABLE ADD COLUMN fails if column already exists in SQLite.
    # Catch "duplicate column name" for idempotency.
    alter_statements = [
        "ALTER TABLE v9_bars_5min ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE v9_woodies_signals ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE v9_trades ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE v9_five_min_setups ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0",
    ]

    for stmt in alter_statements:
        table = stmt.split("TABLE ")[1].split(" ADD")[0]
        try:
            cur.execute(stmt)
            print(f"[019] {table}.is_synthetic: ADDED")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"[019] {table}.is_synthetic: already exists (OK)")
            else:
                raise

    conn.commit()
    conn.close()
    print("[019] Migration complete.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    migrate(path)
