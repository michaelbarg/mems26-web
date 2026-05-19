"""P30.9b — Tests for /api/v9/cumulative_delta/current.

Proves the GET endpoint reads Sierra cumulative_delta.json correctly,
rejects stale files, and handles missing files without crashing.
"""

import json
import os
import time
import tempfile

import pytest
from fastapi.testclient import TestClient

from backend.v9.api.v9 import cumulative_delta_routes
from backend.v9.app import app

client = TestClient(app)

SAMPLE_CVD = {
    "type": "cumulative_delta",
    "version": "v9.4.0-p30.9",
    "export_ts": int(time.time()),
    "points": [
        {"i": 100, "d": -88.0, "cum": -88.0, "p": 7400.0},
        {"i": 105, "d": 150.0, "cum": 62.0, "p": 7405.0},
        {"i": 110, "d": -30.0, "cum": 32.0, "p": 7402.0},
    ],
    "current_delta": 32.0,
    "session_delta": 32.0,
    "peak": 62.0,
    "trough": -88.0,
}


def test_cvd_returns_200_with_fresh_file(monkeypatch, tmp_path):
    """Endpoint returns points from a fresh Sierra file."""
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(SAMPLE_CVD))

    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    resp = client.get("/api/v9/cumulative_delta/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "sierra_cumulative_delta_json"
    assert data["stale"] is False
    assert data["point_count"] == 3
    assert data["current_delta"] == 32.0
    assert data["peak"] == 62.0
    assert len(data["points"]) == 3


def test_cvd_returns_stale_when_old(monkeypatch, tmp_path):
    """Endpoint flags stale when file is older than threshold."""
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(SAMPLE_CVD))
    # Set mtime to 60s ago
    old_time = time.time() - 60
    os.utime(f, (old_time, old_time))

    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    monkeypatch.setattr(cumulative_delta_routes, "MAX_AGE_S", 30.0)
    resp = client.get("/api/v9/cumulative_delta/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stale"] is True
    assert "error" in data


def test_cvd_returns_missing_when_no_file(monkeypatch, tmp_path):
    """Endpoint returns source=missing when file doesn't exist."""
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", tmp_path / "nonexistent.json")
    resp = client.get("/api/v9/cumulative_delta/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "missing"


def test_cvd_latency_under_100ms(monkeypatch, tmp_path):
    """Endpoint responds within budget."""
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(SAMPLE_CVD))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)

    start = time.monotonic()
    resp = client.get("/api/v9/cumulative_delta/current")
    elapsed_ms = (time.monotonic() - start) * 1000
    assert resp.status_code == 200
    assert elapsed_ms < 100, f"CVD endpoint took {elapsed_ms:.1f}ms"
