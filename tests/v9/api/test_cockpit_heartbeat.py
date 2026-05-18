"""P30.5 — Tests for /api/v9/cockpit/heartbeat.

Proves the heartbeat endpoint returns quickly with cheap local truth.
No Redis, no bridge, no external calls.
"""

import time

from fastapi.testclient import TestClient

from backend.v9.app import app


client = TestClient(app)


def test_heartbeat_returns_200():
    resp = client.get("/api/v9/cockpit/heartbeat")
    assert resp.status_code == 200
    data = resp.json()
    assert data["alive"] is True
    assert "mode" in data
    assert "ts" in data
    assert "price_file_age_ms" in data
    assert "ws_clients" in data


def test_heartbeat_latency_under_100ms():
    start = time.monotonic()
    resp = client.get("/api/v9/cockpit/heartbeat")
    elapsed_ms = (time.monotonic() - start) * 1000
    assert resp.status_code == 200
    assert elapsed_ms < 100, f"Heartbeat took {elapsed_ms:.1f}ms, budget is 100ms"


def test_heartbeat_does_not_call_status():
    """Heartbeat must not proxy through the heavy /api/v9/status."""
    resp = client.get("/api/v9/cockpit/heartbeat")
    data = resp.json()
    # Status endpoint returns keys like 'session', 'sierra', 'bridge', 'event_bus'
    # Heartbeat must NOT contain these
    for heavy_key in ("session", "sierra", "bridge", "event_bus", "audit", "hydration"):
        assert heavy_key not in data, f"Heartbeat leaked heavy key: {heavy_key}"
