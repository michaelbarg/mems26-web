"""Tests for day_type.prev_day loader (P30 Wave 1a)."""
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from backend.v9.systems.day_type import prev_day as pd


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE v9_bars_5min (
            ts TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL
        )"""
    )
    conn.execute(
        """CREATE TABLE v9_tpo_sessions (
            id INTEGER PRIMARY KEY,
            trading_date TEXT,
            session_type TEXT,
            poc_price REAL,
            vah_price REAL,
            val_price REAL,
            ib_high REAL,
            ib_low REAL,
            ib_width REAL,
            profile_shape TEXT,
            opening_type TEXT,
            range_high REAL,
            range_low REAL
        )"""
    )
    conn.commit()
    conn.close()
    return path


def test_missing_bars_and_tpo_returns_degraded(db_path: Path):
    out = pd.load_previous_day_context(db_path, previous_trading_day="2026-05-16")

    assert out["pd_context_status"] == "DEGRADED"
    assert out["degraded_reason"] == "missing_previous_day_context"
    assert set(out["missing_pd_fields"]) == {"pd_high", "pd_low", "pd_close"}


def test_happy_path_tpo_range_and_bar_close(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO v9_bars_5min VALUES (?,?,?,?,?,?)",
        ("2026-05-16 15:55:00", 100.0, 110.0, 90.0, 105.0, 1000.0),
    )
    conn.execute(
        """INSERT INTO v9_tpo_sessions
           (trading_date, session_type, range_high, range_low)
           VALUES (?, 'CASH', 108.0, 92.0)""",
        ("2026-05-16",),
    )
    conn.commit()
    conn.close()

    out = pd.load_previous_day_context(db_path, previous_trading_day="2026-05-16")

    assert out["pd_context_status"] == "OK"
    assert out["pd_high"] == 108.0
    assert out["pd_low"] == 92.0
    assert out["pd_close"] == 105.0


def test_bars_fallback_when_tpo_missing_range(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO v9_bars_5min VALUES (?,?,?,?,?,?)",
        ("2026-05-16 10:00:00", 100.0, 120.0, 80.0, 115.0, 500.0),
    )
    conn.commit()
    conn.close()

    out = pd.load_previous_day_context(db_path, previous_trading_day="2026-05-16")

    assert out["pd_context_status"] == "OK"
    assert out["pd_high"] == 120.0
    assert out["pd_low"] == 80.0
    assert out["pd_close"] == 115.0


def test_tpo_summary_found(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO v9_tpo_sessions
           (trading_date, session_type, poc_price, vah_price, val_price,
            ib_high, ib_low, profile_shape)
           VALUES ('2026-05-16', 'CASH', 100.5, 102.0, 98.0, 101.0, 99.0, 'D')"""
    )
    conn.commit()
    conn.close()

    out = pd.load_tpo_previous_day_summary(db_path, previous_trading_day="2026-05-16")

    assert out["found"] is True
    assert out["poc"] == 100.5
    assert out["vah"] == 102.0
    assert out["profile_shape"] == "D"


def test_tpo_summary_not_found(db_path: Path):
    out = pd.load_tpo_previous_day_summary(db_path, previous_trading_day="2026-05-16")

    assert out["found"] is False
    assert out["session_date"] == "2026-05-16"
