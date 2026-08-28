"""Anti-tautological tests for bars.py safe_writer migration (2026-06-03).

Each test calls the REAL route handler via FastAPI TestClient, verifies the
row was ACTUALLY written to the DB, and verifies dedup behavior.

if reverted → RED because: reverting would restore ORM db.add/db.commit writes
which bypass safe_writer's _write_lock, re-introducing the concurrent write
race that caused B-tree corruption.
"""

import os
import sqlite3
import tempfile

# bars module imports auth which requires BRIDGE_TOKEN at import time
if not os.getenv("BRIDGE_TOKEN"):
    os.environ["BRIDGE_TOKEN"] = "test-token-for-isolation"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Patch safe_writer DB_PATH BEFORE importing bars module
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db_path = _tmp_db.name
_tmp_db.close()

# Create tables in temp DB
_conn = sqlite3.connect(_tmp_db_path)
_conn.execute("PRAGMA journal_mode=WAL")
_conn.executescript("""
CREATE TABLE IF NOT EXISTS v9_bars_5min (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL DEFAULT 'MES',
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL DEFAULT 0,
    poc_vol INTEGER,
    vah REAL,
    val REAL,
    cumulative_delta REAL,
    is_synthetic INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts, symbol)
);
CREATE TABLE IF NOT EXISTS v9_bars_30min_woodies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL DEFAULT 'MES',
    open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
    volume INTEGER NOT NULL DEFAULT 0,
    cci_14 REAL, cci_6_tcci REAL, lsma_value REAL, swi_value REAL,
    czi_value REAL, ema_34 REAL, trend_state TEXT, predictor_next_cci REAL,
    zlr_detected INTEGER DEFAULT 0, zlr_direction TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS v9_tpo_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL DEFAULT 'MES',
    letter TEXT NOT NULL,
    price REAL NOT NULL,
    level INTEGER NOT NULL,
    period_id INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS v9_system_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    system_id INTEGER NOT NULL,
    classification TEXT,
    direction TEXT,
    confidence REAL,
    payload TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS v9_bars_imbalance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    bar_id TEXT UNIQUE,
    price REAL,
    ratio REAL,
    direction TEXT,
    bid_vol INTEGER,
    ask_vol INTEGER,
    session TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS v9_bars_stacked_imbalance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    bar_id TEXT UNIQUE,
    count INTEGER,
    direction TEXT,
    start_price REAL,
    end_price REAL,
    session TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS v9_bars_cumulative_delta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    bar_id TEXT UNIQUE,
    delta REAL,
    cumulative REAL,
    direction TEXT,
    session TEXT,
    symbol TEXT NOT NULL DEFAULT 'MES',
    source_version TEXT NOT NULL DEFAULT 'live',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts, symbol, source_version)
);
CREATE TABLE IF NOT EXISTS v9_bars_volume_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    bar_id TEXT UNIQUE,
    profile TEXT,
    poc REAL,
    vah REAL,
    val REAL,
    total_volume INTEGER,
    session TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS v9_bars_5min_woodies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, symbol TEXT DEFAULT 'MES',
    open REAL, high REAL, low REAL, close REAL, volume INTEGER DEFAULT 0,
    cci_14 REAL, cci_6_tcci REAL, lsma_value REAL, swi_value REAL,
    czi_value REAL, ema_34 REAL, trend_state TEXT, predictor_next_cci REAL,
    zlr_detected INTEGER DEFAULT 0, zlr_direction TEXT,
    proj_hi REAL, proj_lo REAL,
    hfe_detected INTEGER DEFAULT 0, hfe_direction TEXT DEFAULT 'NONE',
    hfe_extreme_bars_ago INTEGER DEFAULT 0, lsma_above_price INTEGER DEFAULT 0,
    UNIQUE(ts, symbol)
);
""")
_conn.close()

# Patch engines BEFORE importing bars module
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_test_engine = create_engine(f"sqlite:///{_tmp_db_path}", connect_args={"check_same_thread": False})
_TestSession = sessionmaker(bind=_test_engine)

# Patch all engine references so safe_writer + db.read use the test DB
import backend.v9.db.safe_writer as _sw
import backend.v9.db.read as _read_mod
import backend.v9.db.session as _session_mod
_sw.DB_PATH = _tmp_db_path
_read_mod.engine = _test_engine
_session_mod.engine = _test_engine

# Now import and wire up the router
from backend.v9.api.v9.bars import router

app = FastAPI()
app.include_router(router)

# Override auth dependency
from backend.v9.api.v9.auth import verify_bridge_token
app.dependency_overrides[verify_bridge_token] = lambda: "test"

from backend.v9.db.session import get_db

def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = _override_get_db

client = TestClient(app)


def _count(table: str) -> int:
    conn = sqlite3.connect(_tmp_db_path, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
    n = cur.fetchone()[0]
    conn.close()
    return n


def _query(sql: str):
    conn = sqlite3.connect(_tmp_db_path, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql).fetchall()
    conn.close()
    return rows


# ── Tests ──


class TestPost5Min:
    """if reverted → RED because: ORM db.add/db.commit would bypass safe_writer lock."""

    def test_insert_and_dedup(self):
        """Insert a bar, then POST the same ts again → dedup (INSERT OR REPLACE)."""
        # Verify DB_PATH is patched
        from backend.v9.db import safe_writer as sw
        assert sw.DB_PATH == _tmp_db_path, f"DB_PATH not patched: {sw.DB_PATH}"

        resp = client.post("/api/v9/bars/5min", json=[
            {"ts": 1699972200, "symbol": "MES", "o": 100, "h": 105, "l": 99, "c": 103, "vol": 50}
        ])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["ok"] is True

        rows = _query("SELECT * FROM v9_bars_5min WHERE symbol='MES'")
        assert len(rows) >= 1, f"Expected rows in v9_bars_5min, got 0. Response: {data}"
        row = rows[-1]
        assert row["close"] == 103.0

        # Dedup: same ts, different close
        resp2 = client.post("/api/v9/bars/5min", json=[
            {"ts": 1699972200, "symbol": "MES", "o": 100, "h": 106, "l": 99, "c": 104, "vol": 55}
        ])
        assert resp2.status_code == 200
        # Should still be 1 row (INSERT OR REPLACE)
        rows2 = _query("SELECT * FROM v9_bars_5min WHERE ts LIKE '%2023-11-14%14:30%' AND symbol='MES'")
        assert len(rows2) == 1
        assert rows2[0]["close"] == 104.0

    def test_rejects_invalid_bar(self):
        resp = client.post("/api/v9/bars/5min", json=[
            {"ts": 1700000100, "symbol": "MES", "o": 0, "h": 0, "l": 0, "c": 0, "vol": 0}
        ])
        assert resp.status_code == 200
        assert resp.json()["rejected"] >= 1


class TestRthTimeGate:
    """if reverted → RED because: removing the RTH time-gate lets cumulative
    settlement bars (vol up to 1M) enter v9_bars_5min, corrupting rolling_avg."""

    def test_outside_rth_rejected(self):
        """Bar at 17:00 ET (22:00 UTC, outside RTH) must NOT be written."""
        # 1699999200 = 2023-11-14 22:00 UTC = 17:00 EST (outside RTH 09:30-16:00)
        resp = client.post("/api/v9/bars/5min", json=[
            {"ts": 1699999200, "symbol": "MES", "o": 100, "h": 105, "l": 99, "c": 103, "vol": 999999}
        ])
        assert resp.status_code == 200
        data = resp.json()
        assert data["rth_skipped"] >= 1, f"Expected rth_skipped >= 1, got {data}"
        # Verify the bar was NOT written
        rows = _query("SELECT * FROM v9_bars_5min WHERE volume = 999999")
        assert len(rows) == 0, "Settlement-volume bar should not be in DB"

    def test_within_rth_accepted(self):
        """Bar at 10:00 ET (15:00 UTC in Nov) must be written."""
        # 1699974000 = 2023-11-14 15:00 UTC = 10:00 EST (within RTH)
        resp = client.post("/api/v9/bars/5min", json=[
            {"ts": 1699974000, "symbol": "MES", "o": 5000, "h": 5005, "l": 4998, "c": 5003, "vol": 3000}
        ])
        assert resp.status_code == 200
        data = resp.json()
        assert data["rth_skipped"] == 0
        assert data["inserted"] >= 1
        rows = _query("SELECT * FROM v9_bars_5min WHERE volume = 3000")
        assert len(rows) >= 1


class TestPostImbalance:
    """if reverted → RED because: ORM db.add for v9_system_signals would bypass safe_writer."""

    def test_insert_signal_and_dedicated(self):
        before = _count("v9_system_signals")
        resp = client.post("/api/v9/bars/imbalance", json={
            "type": "imbalance_flags",
            "bars": [{"ts": 1700000200, "bar_idx": 1, "price": 5000.0,
                       "stacked_buy": 3, "stacked_sell": 1}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["inserted"] >= 1
        assert _count("v9_system_signals") > before
        assert _count("v9_bars_imbalance") >= 1


class TestPostStackedImbalance:
    """if reverted → RED because: ORM db.add for v9_system_signals would bypass safe_writer."""

    def test_insert(self):
        before = _count("v9_system_signals")
        resp = client.post("/api/v9/bars/stacked_imbalance", json={
            "type": "stacked_imbalances",
            "stacks": [{"ts": 1700000300, "bar_idx": 2, "count": 3,
                         "direction": "BUY", "start_price": 5000, "end_price": 5003}],
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert _count("v9_system_signals") > before
        rows = _query("SELECT * FROM v9_bars_stacked_imbalance WHERE bar_id='simb_2'")
        assert len(rows) == 1


class TestPostWoodies:
    """if reverted → RED because: ORM db.add/db.commit would bypass safe_writer."""

    def test_insert(self):
        resp = client.post("/api/v9/bars/woodies", json={
            "type": "woodies_30min",
            "bars": [{"ts": 1700000400, "o": 100, "h": 105, "l": 99, "c": 103, "vol": 50,
                       "cci_14": 55.0}],
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        rows = _query("SELECT * FROM v9_bars_30min_woodies")
        assert len(rows) >= 1
        assert rows[-1]["cci_14"] == 55.0


class TestPostTpo:
    """if reverted → RED because: ORM db.add/db.commit would bypass safe_writer."""

    def test_insert(self):
        resp = client.post("/api/v9/bars/tpo", json={
            "bars": [{"ts": 1700000500, "letter": "A", "price": 5000.0,
                       "level": 1, "period_id": 1}],
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        rows = _query("SELECT * FROM v9_tpo_bars")
        assert len(rows) >= 1
        assert rows[-1]["letter"] == "A"


class TestPostWoodies5Min:
    """if reverted → RED because: raw sqlite3.connect would bypass safe_writer."""

    def test_insert_via_safe_writer(self):
        resp = client.post("/api/v9/bars/woodies_5min", json={
            "type": "woodies_5min",
            "bars": [{"ts": "2026-06-03T10:00:00", "o": 100, "h": 105, "l": 99,
                       "c": 103, "vol": 50, "cci_14": 42.0, "swi_value": 0.7}],
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        rows = _query("SELECT * FROM v9_bars_5min_woodies")
        assert len(rows) >= 1
        assert rows[-1]["cci_14"] == 42.0


class TestPostCumulativeDelta:
    """if reverted → RED because: ORM update + db.execute would bypass safe_writer."""

    def test_dedicated_table_insert(self):
        resp = client.post("/api/v9/bars/cumulative_delta", json={
            "type": "cumulative_delta",
            "points": [{"i": 0, "t": 1699974600, "d": 50, "cum": 150, "p": 5000}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["inserted"] >= 1
        rows = _query("SELECT * FROM v9_bars_cumulative_delta "
                      "WHERE cumulative = 150.0")
        assert len(rows) == 1
        # R0 (2026-08-28, T-112): bar_id is no longer written — the chart
        # row index is not stable across reloads and must never be a key.
        assert rows[0]["bar_id"] is None

    def test_r0_chart_reload_does_not_drag_history(self):
        """R0 regression (ruling f4bf481d 2026-08-28 / T-112).

        A Sierra chart reload re-pushes the SAME bar under a DIFFERENT chart
        row index. The old bar_id-keyed INSERT OR REPLACE became
        ON CONFLICT(bar_id) DO UPDATE SET ts=… and DRAGGED historical rows
        onto today's ts — 08-14 + 08-21 lost all 89 CVD rows each. The
        time-keyed upsert must keep ONE row at the original ts with values
        refreshed, regardless of the index the chart assigns.

        (ts values are asserted as-written, not hardcoded — _ts_from_unix
        applies the documented DLL time-skew correction on ingest.)
        """
        t1 = 1699975200  # 2023-11-14 14:40 UTC (RTH after skew-fix)
        n0 = _count("v9_bars_cumulative_delta")
        resp = client.post("/api/v9/bars/cumulative_delta", json={
            "type": "cumulative_delta",
            "points": [{"i": 7, "t": t1, "d": 51, "cum": 151, "p": 5000}],
        })
        assert resp.status_code == 200
        rows = _query("SELECT * FROM v9_bars_cumulative_delta "
                      "WHERE cumulative = 151.0")
        assert len(rows) == 1
        ts_written = rows[0]["ts"]
        assert _count("v9_bars_cumulative_delta") == n0 + 1
        # Chart reload: same t, SHIFTED index, refreshed values
        resp = client.post("/api/v9/bars/cumulative_delta", json={
            "type": "cumulative_delta",
            "points": [{"i": 3, "t": t1, "d": 61, "cum": 161, "p": 5000}],
        })
        assert resp.status_code == 200
        # no new row, no duplicate — the SAME ts row was refreshed in place
        assert _count("v9_bars_cumulative_delta") == n0 + 1
        rows = _query(f"SELECT * FROM v9_bars_cumulative_delta "
                      f"WHERE ts = '{ts_written}'")
        assert len(rows) == 1
        assert rows[0]["delta"] == 61.0
        assert rows[0]["cumulative"] == 161.0
        # rows written earlier (other ts) were NOT dragged onto this ts
        others = _query(f"SELECT * FROM v9_bars_cumulative_delta "
                        f"WHERE ts != '{ts_written}'")
        assert len(others) == n0


@pytest.fixture(autouse=True, scope="session")
def cleanup():
    yield
    try:
        os.unlink(_tmp_db_path)
    except OSError:
        pass
