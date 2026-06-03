"""Tests for V9 Day Type API endpoints (3a-S4 REVISED C3).

Tests /api/v9/day_type/v9/current, /history, /stats.
Postgres migration (2026-06-03): fixture patches db.read.engine and
db.session.engine to use a temp SQLite DB (same engine the code reads from).
"""
import pytest
import sqlite3
import tempfile
import os
from datetime import date
from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.v9.api.v9 import day_type_v9_routes
import backend.v9.db.read as _read_mod
import backend.v9.db.session as _session_mod


@pytest.fixture
def tmp_db():
    """Create a temporary SQLite DB with the v9_day_type_history table."""
    fd, path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE v9_day_type_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL UNIQUE,
            day_type VARCHAR(32) NOT NULL,
            status VARCHAR(16),
            confidence FLOAT,
            ib_high FLOAT,
            ib_low FLOAT,
            ib_width_ticks INTEGER,
            opening_type VARCHAR(32),
            locked_at DATETIME,
            reasoning_notes VARCHAR(1024),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            probability FLOAT,
            directional_certainty VARCHAR(8),
            trading_confidence VARCHAR(8),
            ib_width FLOAT,
            ib_width_class VARCHAR(8),
            active_zohar_rules JSON DEFAULT '[]',
            last_updated_at DATETIME,
            updated_at DATETIME
        )
    """)
    conn.commit()
    conn.close()
    yield path
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def client(tmp_db):
    """TestClient with engine patched to temp SQLite DB."""
    test_engine = create_engine(f"sqlite:///{tmp_db}", connect_args={"check_same_thread": False})
    with mock.patch.object(_read_mod, "engine", test_engine), \
         mock.patch.object(_session_mod, "engine", test_engine):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(day_type_v9_routes.router)
        yield TestClient(app)


def _insert_row(db_path, session_date, day_type, probability=0.7, **kwargs):
    """Insert a test row into the tmp DB."""
    conn = sqlite3.connect(db_path)
    defaults = {
        "directional_certainty": "HIGH",
        "trading_confidence": "LOW",
        "ib_high": 5260.0,
        "ib_low": 5240.0,
        "ib_width": 20.0,
        "ib_width_class": "MEDIUM",
        "opening_type": "OPEN_DRIVE",
        "reasoning_notes": "test",
        "active_zohar_rules": '["delta"]',
    }
    defaults.update(kwargs)
    conn.execute(
        """INSERT INTO v9_day_type_history
           (date, day_type, probability, directional_certainty, trading_confidence,
            ib_high, ib_low, ib_width, ib_width_class, opening_type,
            reasoning_notes, active_zohar_rules)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_date, day_type, probability,
            defaults["directional_certainty"], defaults["trading_confidence"],
            defaults["ib_high"], defaults["ib_low"],
            defaults["ib_width"], defaults["ib_width_class"],
            defaults["opening_type"], defaults["reasoning_notes"],
            defaults["active_zohar_rules"],
        ),
    )
    conn.commit()
    conn.close()


def test_get_current_no_data(client):
    resp = client.get("/api/v9/day_type/v9/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["classified"] is False
    assert data["data"] is None


def test_get_current_with_data(client, tmp_db):
    from backend.v9.common.trading_date import et_today
    today = et_today().isoformat()
    _insert_row(tmp_db, today, "Trend_Normal", 0.7)
    resp = client.get("/api/v9/day_type/v9/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["classified"] is True
    assert data["data"]["day_type"] == "Trend_Normal"
    assert data["data"]["probability"] == 0.7
    assert data["data"]["active_zohar_rules"] == ["delta"]


def test_get_history_default(client, tmp_db):
    _insert_row(tmp_db, "2026-05-14", "Normal", 0.6)
    _insert_row(tmp_db, "2026-05-15", "Variation", 0.8)
    resp = client.get("/api/v9/day_type/v9/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["items"][0]["day_type"] == "Variation"
    assert data["items"][1]["day_type"] == "Normal"


def test_get_history_custom_days(client, tmp_db):
    _insert_row(tmp_db, "2026-05-14", "Normal", 0.6)
    _insert_row(tmp_db, "2026-05-15", "Variation", 0.8)
    resp = client.get("/api/v9/day_type/v9/history?days=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1


def test_get_history_bounds(client):
    resp = client.get("/api/v9/day_type/v9/history?days=0")
    assert resp.status_code == 422
    resp = client.get("/api/v9/day_type/v9/history?days=366")
    assert resp.status_code == 422


def test_get_stats(client, tmp_db):
    _insert_row(tmp_db, "2026-05-13", "Normal", 0.6)
    _insert_row(tmp_db, "2026-05-14", "Normal", 0.65)
    _insert_row(tmp_db, "2026-05-15", "Variation", 0.8)
    resp = client.get("/api/v9/day_type/v9/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_days"] == 3
    assert data["distribution"]["Normal"]["count"] == 2
    assert data["distribution"]["Normal"]["percentage"] == pytest.approx(66.7, abs=0.1)
