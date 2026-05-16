"""Atomic tests — S4 Woodies /fire endpoint gates through pre_fire."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.v9.api.v9.woodies.routes import router


class _WoodiesSystemStub:
    def get_current(self):
        return {
            "ready_to_route": True,
            "classification": "TACTICAL",
            "direction": "LONG",
            "entry_classification_spec": "REACTIVE",
            "decision_tree": {"failed_stages": []},
            "active_patterns": [
                {
                    "pattern_id": "ZLR",
                    "direction": "LONG",
                    "confidence": 0.82,
                    "entry_price": 100.0,
                    "stop": 99.0,
                    "targets": [101.0, 102.0, 103.0],
                }
            ],
        }


class _GatewayStub:
    def __init__(self):
        self.calls = []

    def route_setup(self, setup, system_id):
        self.calls.append((setup, system_id))
        return {"shadow": "shadow-1", "demo": None, "live": None, "blocked_by": None}


def _client():
    app = FastAPI()
    app.include_router(router)
    app.state.woodies_system = _WoodiesSystemStub()
    app.state.trading_gateway = _GatewayStub()
    return TestClient(app), app


def test_woodies_fire_get_reports_readiness():
    client, _ = _client()
    resp = client.get("/api/v9/woodies/fire")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready_to_route"] is True
    assert body["entry_classification_spec"] == "REACTIVE"


def test_woodies_fire_post_routes_valid_setup():
    client, app = _client()
    resp = client.post("/api/v9/woodies/fire", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["routed"] is True
    assert body["gateway"]["shadow"] == "shadow-1"
    assert app.state.trading_gateway.calls[0][1] == 4
    setup = app.state.trading_gateway.calls[0][0]
    assert setup["firing_system"] == 4
    assert setup["stop"] == 99.0


def test_woodies_fire_blocks_bad_stop_before_gateway():
    client, app = _client()
    resp = client.post("/api/v9/woodies/fire", json={"stop_price": 101.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["routed"] is False
    assert body["blocked_by"] == "pre_fire_validator"
    assert app.state.trading_gateway.calls == []

