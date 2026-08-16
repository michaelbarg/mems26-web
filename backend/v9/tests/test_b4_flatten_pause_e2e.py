"""B4 — FLATTEN/PAUSE/RESUME end-to-end tests (2026-08-11).

These endpoints exist in mobile_monitor.py but were never tested E2E.
Test the full HTTP flow: double-confirm, flag gates, pause-file creation,
and flatten command writing.
"""
import json
import os
import tempfile

import pytest
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.v9.api.v9.mobile_monitor import router, _PAUSE_FILE


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    """No access key required, no remote URL, clean pause file."""
    monkeypatch.delenv("MOBILE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("MOBILE_REMOTE_URL", raising=False)
    # Use a temp pause file to avoid touching the real one
    _tmp_pause = str(tmp_path / "trading_paused.json")
    monkeypatch.setattr("backend.v9.api.v9.mobile_monitor._PAUSE_FILE", _tmp_pause)
    yield
    # Clean up
    if os.path.exists(_tmp_pause):
        os.unlink(_tmp_pause)


# ── PAUSE ─────────────────────────────────────────────────────────────────

class TestPause:
    def test_pause_requires_confirm(self, client):
        """POST /pause without confirm=PAUSE → rejected."""
        r = client.post("/api/v9/mobile/pause", json={})
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is False
        assert "confirm" in d["error"].lower() or "confirm" in d.get("error", "")

    def test_pause_wrong_confirm(self, client):
        """POST /pause with wrong confirm value → rejected."""
        r = client.post("/api/v9/mobile/pause", json={"confirm": "YES"})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_pause_creates_file(self, client, monkeypatch):
        """POST /pause with confirm=PAUSE → creates pause file."""
        import backend.v9.api.v9.mobile_monitor as mm
        pause_path = mm._PAUSE_FILE

        r = client.post("/api/v9/mobile/pause", json={"confirm": "PAUSE"})
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert "PAUSED" in d["msg"]
        assert os.path.exists(pause_path)

        # Verify file content
        content = json.loads(open(pause_path).read())
        assert content["paused"] is True
        assert content["source"] == "mobile"

    def test_pause_with_access_key(self, client, monkeypatch):
        """When MOBILE_ACCESS_KEY is set, request without key → 401."""
        monkeypatch.setenv("MOBILE_ACCESS_KEY", "secret123")
        r = client.post("/api/v9/mobile/pause", json={"confirm": "PAUSE"})
        assert r.status_code == 401

    def test_pause_with_correct_key(self, client, monkeypatch):
        """When MOBILE_ACCESS_KEY is set, request with key → succeeds."""
        monkeypatch.setenv("MOBILE_ACCESS_KEY", "secret123")
        r = client.post("/api/v9/mobile/pause?key=secret123",
                        json={"confirm": "PAUSE"})
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ── RESUME ────────────────────────────────────────────────────────────────

class TestResume:
    def test_resume_requires_confirm(self, client):
        """POST /resume without confirm=RESUME → rejected."""
        r = client.post("/api/v9/mobile/resume", json={})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_resume_removes_pause_file(self, client, monkeypatch):
        """POST /resume removes the pause file."""
        import backend.v9.api.v9.mobile_monitor as mm

        # First pause
        client.post("/api/v9/mobile/pause", json={"confirm": "PAUSE"})
        assert os.path.exists(mm._PAUSE_FILE)

        # Then resume
        r = client.post("/api/v9/mobile/resume", json={"confirm": "RESUME"})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert "RESUMED" in r.json()["msg"]
        assert not os.path.exists(mm._PAUSE_FILE)

    def test_resume_idempotent(self, client):
        """Resuming when not paused → still succeeds."""
        r = client.post("/api/v9/mobile/resume", json={"confirm": "RESUME"})
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ── FLATTEN ───────────────────────────────────────────────────────────────

class TestFlatten:
    def test_flatten_requires_confirm(self, client):
        """POST /flatten without confirm=FLATTEN → rejected."""
        r = client.post("/api/v9/mobile/flatten", json={})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_flatten_requires_flag(self, client, monkeypatch):
        """Flatten with MANUAL_FLATTEN_V1=0 → rejected."""
        monkeypatch.setenv("MANUAL_FLATTEN_V1", "0")
        r = client.post("/api/v9/mobile/flatten", json={"confirm": "FLATTEN"})
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is False
        assert "MANUAL_FLATTEN_V1" in d["error"]

    def test_flatten_calls_sierra_command(self, client, monkeypatch):
        """Flatten with flag ON → calls write_flatten_account (T1 2026-08-15:
        the old write_trade_command shape raised TypeError — the phone button
        never sent anything)."""
        monkeypatch.setenv("MANUAL_FLATTEN_V1", "1")
        with patch("backend.v9.services.sierra_command.write_flatten_account") as mock_cmd:
            r = client.post("/api/v9/mobile/flatten", json={"confirm": "FLATTEN"})
            assert r.status_code == 200
            d = r.json()
            assert d["ok"] is True
            assert "FLATTEN_ACCOUNT" in d["msg"]
            mock_cmd.assert_called_once()
            args = mock_cmd.call_args
            assert args[1]["source"] == "mobile_manual"

    def test_flatten_with_access_key(self, client, monkeypatch):
        """Access key gate applies to flatten."""
        monkeypatch.setenv("MOBILE_ACCESS_KEY", "s3cret")
        monkeypatch.setenv("MANUAL_FLATTEN_V1", "1")
        r = client.post("/api/v9/mobile/flatten", json={"confirm": "FLATTEN"})
        assert r.status_code == 401


# ── PAGE ──────────────────────────────────────────────────────────────────

class TestPage:
    def test_page_serves_html(self, client):
        """GET /api/v9/mobile → HTML 200."""
        r = client.get("/api/v9/mobile")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "MEMS26" in r.text

    def test_page_requires_key_when_set(self, client, monkeypatch):
        """When MOBILE_ACCESS_KEY is set → 401 without key."""
        monkeypatch.setenv("MOBILE_ACCESS_KEY", "mykey")
        r = client.get("/api/v9/mobile")
        assert r.status_code == 401

    def test_page_with_key(self, client, monkeypatch):
        """Key in query string → 200."""
        monkeypatch.setenv("MOBILE_ACCESS_KEY", "mykey")
        r = client.get("/api/v9/mobile?key=mykey")
        assert r.status_code == 200

    def test_page_contains_flatten_button(self, client):
        """Page must contain the FLATTEN button."""
        r = client.get("/api/v9/mobile")
        assert "FLATTEN" in r.text or "flatten" in r.text

    def test_page_contains_pause_button(self, client):
        """Page must contain the PAUSE button."""
        r = client.get("/api/v9/mobile")
        assert "PAUSE" in r.text or "pause" in r.text

    def test_page_contains_per_contract_renderer(self, client):
        """Page must contain the B2 per-contract leg rendering code."""
        r = client.get("/api/v9/mobile")
        assert "legs" in r.text
        assert "legRow" in r.text


# ── PAUSE-RESUME cycle ────────────────────────────────────────────────────

class TestPauseResumeCycle:
    def test_full_cycle(self, client, monkeypatch):
        """Pause → verify paused → Resume → verify not paused."""
        import backend.v9.api.v9.mobile_monitor as mm

        # Not paused initially
        assert not os.path.exists(mm._PAUSE_FILE)

        # Pause
        r = client.post("/api/v9/mobile/pause", json={"confirm": "PAUSE"})
        assert r.json()["ok"] is True
        assert os.path.exists(mm._PAUSE_FILE)

        # Resume
        r = client.post("/api/v9/mobile/resume", json={"confirm": "RESUME"})
        assert r.json()["ok"] is True
        assert not os.path.exists(mm._PAUSE_FILE)

        # Pause again
        r = client.post("/api/v9/mobile/pause", json={"confirm": "PAUSE"})
        assert r.json()["ok"] is True
        assert os.path.exists(mm._PAUSE_FILE)
