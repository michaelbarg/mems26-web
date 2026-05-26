"""Fixtures for build_status tests.

CRITICAL: Tests 14 and 16 MUST use real FiveMinSystem/WoodiesSystem instances.
FakeFiveMinSystem or MagicMock for FiveMinSystem is FORBIDDEN per mega-prompt §CRITICAL.
This counters the Memorial Day dead-code wiring bug — fake mocks passed unit tests
but real wiring failed silently.
"""

import sqlite3
import tempfile
import os
from datetime import date, datetime, timezone, timedelta

import pytest

from backend.v9.systems.five_min.five_min_system import FiveMinSystem
from backend.v9.systems.woodies.woodies_system import WoodiesSystem


@pytest.fixture
def real_five_min_system():
    """Real FiveMinSystem instance with 14 bar fixtures manually injected.

    Does NOT call hydrate() to avoid real DB access.
    Directly populates _bar_buffer with synthetic 5-min bars.
    Used in test_build_status_live_repro_with_real_five_min_system_instance (test #16).
    """
    fm = FiveMinSystem()
    fm._hydrated = True
    fm.buffer_size = 0
    fm._bar_buffer = []  # Reset class-level shared list

    base_ts = datetime(2026, 5, 26, 14, 0, 0, tzinfo=timezone.utc)
    for i in range(14):
        ts = base_ts + timedelta(minutes=5 * i)
        bar = {
            "ts": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "o": 4700.0 + i * 0.25,
            "h": 4705.0 + i * 0.25,
            "l": 4695.0 + i * 0.25,
            "c": 4702.0 + i * 0.25,
            "v": 1000 + i * 10,
        }
        fm._bar_buffer.append(bar)
    fm.buffer_size = len(fm._bar_buffer)
    return fm


@pytest.fixture
def real_woodies_system():
    """Real WoodiesSystem instance with minimal state set.

    Does NOT call hydrate() to avoid real DB access.
    Sets current_state fields to reflect a hydrated-but-quiet system.
    """
    ws = WoodiesSystem()
    ws.current_state.update({
        "running": True,
        "hydrated": True,
        "cci_14": 45.3,
        "cci_6_tcci": 38.1,
        "trend_state": "BLUE",
        "active_patterns": [],
        "classification": "NO_SETUP",
        "ready_to_route": False,
        "buffer_size": 14,
    })
    return ws


@pytest.fixture
def temp_db_with_five_min_setups(tmp_path):
    """Temp SQLite DB with v9_five_min_setups and v9_bars_5min tables.

    Used by tests that need to simulate S2 pattern fires.
    Returns (db_path, today_str).
    """
    db_path = str(tmp_path / "test_mems26.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE v9_five_min_setups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            pattern TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_price REAL NOT NULL,
            t1_price REAL,
            t2_price REAL,
            time_stop_min INTEGER,
            confidence REAL NOT NULL DEFAULT 75.0,
            day_type_at_fire TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE v9_bars_5min (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            symbol TEXT NOT NULL DEFAULT 'MES',
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE v9_bars_5min_woodies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE v9_day_type_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            day_type TEXT,
            probability REAL,
            directional_certainty REAL,
            trading_confidence REAL,
            ib_high REAL,
            ib_low REAL,
            ib_width REAL,
            ib_width_class TEXT,
            opening_type TEXT,
            last_updated_at TEXT,
            reasoning_notes TEXT,
            active_zohar_rules TEXT
        )
    """)
    conn.commit()
    conn.close()

    today = date.today().isoformat()
    return db_path, today


@pytest.fixture
def temp_db_with_today_fire(temp_db_with_five_min_setups):
    """Temp DB with one REACTIVE_LONG fire inserted for today."""
    db_path, today = temp_db_with_five_min_setups
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO v9_five_min_setups (ts, pattern, direction, entry_price, stop_price, confidence) VALUES (?,?,?,?,?,?)",
        (now_ts, "REACTIVE_LONG", "LONG", 4700.0, 4698.0, 75.0),
    )
    conn.commit()
    conn.close()
    return db_path, today


@pytest.fixture
def temp_db_with_day_type_row(temp_db_with_five_min_setups):
    """Temp DB with a classified day type row for today (NeuC = Neutral_Center)."""
    db_path, today = temp_db_with_five_min_setups
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO v9_day_type_history
           (date, day_type, probability, directional_certainty, ib_width_class, opening_type, last_updated_at, active_zohar_rules)
           VALUES (?,?,?,?,?,?,?,?)""",
        (today, "Neutral_Center", 0.72, 0.65, "NORMAL", "OD", datetime.now(timezone.utc).isoformat(), "[]"),
    )
    conn.commit()
    conn.close()
    return db_path, today


@pytest.fixture
def temp_db_with_developing_day_type(temp_db_with_five_min_setups):
    """Temp DB with an IB DEVELOPING row for today."""
    db_path, today = temp_db_with_five_min_setups
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO v9_day_type_history
           (date, day_type, probability, directional_certainty, ib_width_class, opening_type, last_updated_at, active_zohar_rules)
           VALUES (?,?,?,?,?,?,?,?)""",
        (today, "UNKNOWN", 0.3, 0.2, "DEVELOPING", "OD", datetime.now(timezone.utc).isoformat(), "[]"),
    )
    conn.commit()
    conn.close()
    return db_path, today
