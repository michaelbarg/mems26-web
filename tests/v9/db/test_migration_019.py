"""P31.1-T5: Migration 019 round-trip test on isolated temp DB."""
import sqlite3
import tempfile

import importlib
m019 = importlib.import_module("backend.v9.db.migrations.versions.019_archive_and_session_meta")


# Minimal seed DDL — just enough for the ALTER TABLE statements
SEED_DDL = [
    "CREATE TABLE v9_bars_5min (id INTEGER PRIMARY KEY, ts TEXT, close REAL, symbol TEXT)",
    "CREATE TABLE v9_woodies_signals (id INTEGER PRIMARY KEY, ts TEXT, signal_type TEXT)",
    "CREATE TABLE v9_trades (id INTEGER PRIMARY KEY, entry_ts TEXT, mode TEXT)",
    "CREATE TABLE v9_five_min_setups (id INTEGER PRIMARY KEY, ts TEXT, pattern TEXT)",
    "CREATE TABLE v9_audit_events (id INTEGER PRIMARY KEY, ts_ms INTEGER, event_type TEXT)",
    "CREATE TABLE v9_day_type_history (id INTEGER PRIMARY KEY, date DATE, day_type TEXT, status TEXT)",
    "CREATE TABLE v9_tpo_sessions (id INTEGER PRIMARY KEY, trading_date TEXT, session_type TEXT, opened_ts TEXT)",
    "CREATE TABLE v9_woodies_signals_src (id INTEGER PRIMARY KEY, ts TEXT)",  # alias for archive source
]


def _run_on_temp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    conn = sqlite3.connect(f.name)
    for ddl in SEED_DDL:
        conn.execute(ddl)
    conn.commit()
    conn.close()
    m019.migrate(f.name)
    return f.name


def test_creates_all_archive_tables():
    db = _run_on_temp_db()
    conn = sqlite3.connect(db)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND "
        "(name LIKE 'v9_%_archive' OR name='v9_session_meta') ORDER BY name"
    ).fetchall()]
    conn.close()
    assert "v9_day_type_archive" in tables
    assert "v9_tpo_sessions_archive" in tables
    assert "v9_woodies_signals_archive" in tables
    assert "v9_build_status_archive" in tables
    assert "v9_session_meta" in tables


def test_adds_is_synthetic_columns():
    db = _run_on_temp_db()
    conn = sqlite3.connect(db)
    for t in ["v9_bars_5min", "v9_woodies_signals", "v9_trades",
              "v9_five_min_setups", "v9_audit_events"]:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()]
        assert "is_synthetic" in cols, f"{t} missing is_synthetic"
    conn.close()


def test_idempotent_double_run():
    """Running twice should not error."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    conn = sqlite3.connect(f.name)
    for ddl in SEED_DDL:
        conn.execute(ddl)
    conn.commit()
    conn.close()
    m019.migrate(f.name)
    m019.migrate(f.name)  # second run — must not raise


def test_seeds_last_rollover_date():
    db = _run_on_temp_db()
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT value FROM v9_session_meta WHERE key='last_rollover_date'"
    ).fetchone()
    conn.close()
    assert row is not None
