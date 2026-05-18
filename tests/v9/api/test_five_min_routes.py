"""Regression tests for /api/v9/five_min/* routes.

P27.5f — Proves the routes read app.state.five_min_system (the live
instance wired to BarRouter) and never create a separate FiveMinSystem.
"""

import types
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.v9.api.v9.five_min.routes import router


def _make_app(five_min_system=None):
    """Create a minimal FastAPI app with the five_min router mounted."""
    app = FastAPI()
    if five_min_system is not None:
        app.state.five_min_system = five_min_system
    app.include_router(router)
    return app


def _mock_system(**overrides):
    """Return a mock FiveMinSystem with sensible defaults."""
    defaults = {
        "running": True,
        "hydrated": True,
        "mode": "FIRST_HOUR",
        "buffer_size": 42,
        "opening_type": "OD",
        "last_pattern": "poc_return",
        "last_confluence": 3,
        "last_classification": "Trend",
    }
    state = {**defaults, **overrides}
    sys = MagicMock()
    sys.get_state.return_value = state
    sys.mode = state["mode"]
    sys.buffer_size = state["buffer_size"]
    # current_state attribute used by /fire
    sys.current_state = {"last_reasoning_notes": "test note"}
    return sys


# ── /current ──────────────────────────────────────────────────────

class TestCurrentRoute:
    def test_returns_live_system_state(self):
        """Route returns get_state() from app.state.five_min_system."""
        sys = _mock_system()
        client = TestClient(_make_app(five_min_system=sys))
        resp = client.get("/api/v9/five_min/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["buffer_size"] == 42
        assert data["mode"] == "FIRST_HOUR"
        sys.get_state.assert_called_once()

    def test_503_when_system_missing(self):
        """If app.state has no five_min_system, return 503 — not a new instance."""
        client = TestClient(_make_app(five_min_system=None))
        resp = client.get("/api/v9/five_min/current")
        assert resp.status_code == 503
        assert "not initialized" in resp.json()["error"]

    def test_no_module_level_system_created(self):
        """The routes module must not hold a module-level FiveMinSystem."""
        import backend.v9.api.v9.five_min.routes as mod
        # The old bug: module had `_system = None` that lazily created FiveMinSystem()
        assert not hasattr(mod, "_system"), \
            "Module-level _system still exists — route would create a separate instance"


# ── /fire ─────────────────────────────────────────────────────────

class TestFireRoute:
    def test_returns_fire_state(self):
        sys = _mock_system()
        client = TestClient(_make_app(five_min_system=sys))
        resp = client.get("/api/v9/five_min/fire")
        assert resp.status_code == 200
        data = resp.json()
        assert data["fired"] is True
        assert data["pattern"] == "poc_return"
        assert data["confluence"] == 3

    def test_503_when_system_missing(self):
        client = TestClient(_make_app(five_min_system=None))
        resp = client.get("/api/v9/five_min/fire")
        assert resp.status_code == 503


# ── /stats ────────────────────────────────────────────────────────

class TestStatsRoute:
    def test_returns_stats(self):
        sys = _mock_system()
        client = TestClient(_make_app(five_min_system=sys))
        resp = client.get("/api/v9/five_min/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "FIRST_HOUR"
        assert data["buffer_size"] == 42

    def test_503_when_system_missing(self):
        client = TestClient(_make_app(five_min_system=None))
        resp = client.get("/api/v9/five_min/stats")
        assert resp.status_code == 503


# ── /setups (placeholder, no system dependency) ───────────────────

class TestSetupsRoute:
    def test_returns_empty(self):
        client = TestClient(_make_app(five_min_system=_mock_system()))
        resp = client.get("/api/v9/five_min/setups")
        assert resp.status_code == 200
        assert resp.json() == {"setups": [], "count": 0}
