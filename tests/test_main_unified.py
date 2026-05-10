"""Tests for the unified backend entry point (backend.main).

Uses FastAPI TestClient — no live DB or Redis required.
Routes that depend on DB/auth will return 4xx/5xx, but the
important thing is they EXIST (not 404).
"""

import os

# Set required env vars BEFORE importing the app
os.environ.setdefault("BRIDGE_TOKEN", "test-token-for-ci")
os.environ.setdefault("DATABASE_URL", "sqlite:///test_mems26.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    """GET /health returns 200 with v9_mounted flag."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["v9_mounted"] is True
    assert "uptime_s" in data


def test_v9_health_endpoint():
    """GET /api/v9/health returns 200."""
    resp = client.get("/api/v9/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "v9.0.0"


def test_v9_bars_endpoint_exists():
    """GET /api/v9/bars/5min exists (not 404).

    Will likely return 422 (missing auth header) or 500 (no DB),
    but NOT 404 — proving the route is mounted.
    """
    resp = client.get("/api/v9/bars/5min?limit=1")
    assert resp.status_code != 404, "V9 bars route not mounted"


def test_v9_signals_endpoint_exists():
    """GET /api/v9/signals exists (not 404)."""
    resp = client.get("/api/v9/signals")
    assert resp.status_code != 404, "V9 signals route not mounted"


def test_v9_trades_endpoint_exists():
    """GET /api/v9/trades exists (not 404)."""
    resp = client.get("/api/v9/trades")
    assert resp.status_code != 404, "V9 trades route not mounted"


def test_v9_markers_endpoint_exists():
    """GET /api/v9/markers exists (not 404)."""
    resp = client.get("/api/v9/markers")
    assert resp.status_code != 404, "V9 markers route not mounted"


def test_v9_configs_endpoint_exists():
    """GET /api/v9/configs exists (not 404)."""
    resp = client.get("/api/v9/configs")
    assert resp.status_code != 404, "V9 configs route not mounted"
