"""P30.6 — Tests for /api/v9/cockpit/systems-snapshot."""

import time

from fastapi.testclient import TestClient

from backend.v9.app import app


client = TestClient(app)


def test_systems_snapshot_returns_all_six_systems():
    resp = client.get("/api/v9/cockpit/systems-snapshot")
    assert resp.status_code == 200
    data = resp.json()

    assert data["count"] == 6
    assert set(data["systems"].keys()) == {"1", "2", "3", "4", "5", "6"}
    for system_id, system in data["systems"].items():
        assert system["id"] == int(system_id)
        assert "name" in system
        assert "state" in system
        assert "subState" in system
        assert "confidence" in system
        assert "health" in system
        assert "raw" in system


def test_systems_snapshot_latency_under_100ms():
    start = time.monotonic()
    resp = client.get("/api/v9/cockpit/systems-snapshot")
    elapsed_ms = (time.monotonic() - start) * 1000

    assert resp.status_code == 200
    assert elapsed_ms < 100, f"Systems snapshot took {elapsed_ms:.1f}ms, budget is 100ms"


def test_systems_snapshot_does_not_call_heavy_status():
    resp = client.get("/api/v9/cockpit/systems-snapshot")
    data = resp.json()

    for heavy_key in ("session", "sierra", "bridge", "event_bus", "audit", "hydration"):
        assert heavy_key not in data, f"Snapshot leaked heavy key: {heavy_key}"
