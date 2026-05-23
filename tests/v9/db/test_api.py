"""Tests: V9 API endpoints — simulates Bridge pushes."""

import time
from unittest.mock import patch

from .conftest import BRIDGE_HEADERS
from backend.v9.db.models import V9Bar5Min


def test_health(client):
    r = client.get("/api/v9/health")
    assert r.status_code == 200
    assert r.json()["version"] == "v9.0.0"


def test_auth_required(client):
    r = client.post("/api/v9/bars/5min", json=[])
    assert r.status_code in (401, 422)


def test_auth_bad_token(client):
    r = client.post(
        "/api/v9/bars/5min", json=[],
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code == 403


def test_post_5min_upserts_same_timestamp(client, db):
    ts = 1715299800.0
    payload = [
        {"ts": ts, "symbol": "MES", "o": 5400.0, "h": 5405.0, "l": 5398.0, "c": 5403.0, "vol": 250},
    ]

    r1 = client.post("/api/v9/bars/5min", json=payload, headers=BRIDGE_HEADERS)
    assert r1.status_code == 200
    assert r1.json()["inserted"] == 1

    payload[0]["c"] = 5404.25
    payload[0]["vol"] = 300
    r2 = client.post("/api/v9/bars/5min", json=payload, headers=BRIDGE_HEADERS)
    assert r2.status_code == 200
    assert r2.json()["inserted"] == 0

    rows = db.query(V9Bar5Min).all()
    assert len(rows) == 1
    assert rows[0].close == 5404.25
    assert rows[0].volume == 300


def test_post_5min_routes_bar_on_update(client, db):
    """P31-02: BarRouter must see live bar updates, not only INSERT."""
    ts = 1715299900.0
    payload = [
        {"ts": ts, "symbol": "MES", "o": 5400.0, "h": 5405.0, "l": 5398.0, "c": 5403.0, "vol": 250},
    ]
    with patch("backend.v9.api.v9.bars._route_bar") as route:
        r1 = client.post("/api/v9/bars/5min", json=payload, headers=BRIDGE_HEADERS)
        assert r1.status_code == 200
        assert route.call_count == 1

        payload[0]["c"] = 5404.25
        r2 = client.post("/api/v9/bars/5min", json=payload, headers=BRIDGE_HEADERS)
        assert r2.status_code == 200
        assert r2.json()["inserted"] == 0
        assert route.call_count == 2
        bar_type, bar_payload = route.call_args_list[-1][0]
        assert bar_type == "5min"
        assert bar_payload["close"] == 5404.25
        assert bar_payload["c"] == 5404.25


def test_post_tick_reversal(client):
    """Simulates Bridge tick_reversal_15 push."""
    payload = {
        "type": "tick_reversal",
        "tick_count": 15,
        "version": "v9.0.0",
        "bar_count": 1,
        "export_ts": time.time(),
        "bars": [
            {"idx": 0, "o": 5412.50, "h": 5415.00, "l": 5410.25, "c": 5411.00,
             "vol": 1234, "ask_vol": 700, "bid_vol": 534, "delta": 166, "dir": 1,
             "ts": time.time()}
        ],
    }
    r = client.post(
        "/api/v9/bars/tick_reversal?tick_count=15",
        json=payload, headers=BRIDGE_HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["inserted"] == 1
    assert r.json()["tick_count"] == 15


def test_post_footprint(client):
    """Simulates Bridge footprint push."""
    payload = {
        "type": "footprint",
        "version": "v9.0.0",
        "bar_count": 1,
        "cumulative_delta": 4521.00,
        "export_ts": time.time(),
        "bars": [
            {"idx": 170, "o": 5412.50, "h": 5413.25, "l": 5411.75, "c": 5412.75,
             "vol": 856, "delta": 122, "poc_price": 5412.50, "poc_vol": 234,
             "stacked_buy": 0, "stacked_sell": 0,
             "levels": [{"p": 5411.75, "bid": 45, "ask": 120, "d": 75, "ib": True, "is": False}],
             "ts": time.time()}
        ],
    }
    r = client.post("/api/v9/bars/footprint", json=payload, headers=BRIDGE_HEADERS)
    assert r.status_code == 200
    assert r.json()["inserted"] == 1


def test_post_imbalance(client):
    payload = {
        "type": "imbalance_flags",
        "version": "v9.0.0",
        "total_buy_imbalances": 12,
        "total_sell_imbalances": 8,
        "bars_with_imbalances": 15,
        "export_ts": time.time(),
        "bars": [
            {"bar_idx": 175, "price": 5412.75, "stacked_buy": 3, "stacked_sell": 0,
             "levels": [{"p": 5412.50, "bid": 30, "ask": 250, "ratio": 8.33, "side": "BUY"}],
             "ts": time.time()}
        ],
    }
    r = client.post("/api/v9/bars/imbalance", json=payload, headers=BRIDGE_HEADERS)
    assert r.status_code == 200
    assert r.json()["inserted"] == 1


def test_post_signals(client):
    payload = {
        "signals": [
            {"system_id": 1, "classification": "TACTICAL",
             "direction": "LONG", "confidence": 0.85,
             "payload": {"confluence": 6}, "ts": time.time()},
        ]
    }
    r = client.post("/api/v9/signals", json=payload, headers=BRIDGE_HEADERS)
    assert r.status_code == 200
    assert r.json()["inserted"] == 1

    # GET
    r = client.get("/api/v9/signals?system_id=1", headers=BRIDGE_HEADERS)
    assert r.status_code == 200
    assert len(r.json()["signals"]) == 1


def test_post_markers(client):
    payload = {
        "markers": [
            {"system_id": 3, "marker_type": "ARROW", "price": 5412.50,
             "color": "#56d364", "label": "Cluster", "ts": time.time()},
        ]
    }
    r = client.post("/api/v9/markers", json=payload, headers=BRIDGE_HEADERS)
    assert r.status_code == 200
    assert r.json()["inserted"] == 1


def test_trade_lifecycle(client):
    # Create trade
    trade = {
        "mode": "SHADOW", "dominant_system": 1, "direction": "LONG",
        "entry_ts": time.time(), "entry_price": 5412.50,
        "stop_initial": 5408.00, "t1_price": 5416.00,
    }
    r = client.post("/api/v9/trades", json=trade, headers=BRIDGE_HEADERS)
    assert r.status_code == 200
    trade_id = r.json()["trade_id"]

    # Add management log
    log = {"trade_id": trade_id, "action": "STOP_MOVED",
           "value": {"old": 5408.00, "new": 5412.50}, "ts": time.time()}
    r = client.post("/api/v9/trades/log", json=log, headers=BRIDGE_HEADERS)
    assert r.status_code == 200

    # GET trade with log
    r = client.get(f"/api/v9/trades/{trade_id}", headers=BRIDGE_HEADERS)
    assert r.status_code == 200
    assert r.json()["trade"]["entry_price"] == 5412.50
    assert len(r.json()["management_log"]) == 1

    # GET trades list
    r = client.get("/api/v9/trades?mode=SHADOW", headers=BRIDGE_HEADERS)
    assert r.status_code == 200
    assert len(r.json()["trades"]) == 1


def test_configs_crud(client):
    # PUT (upsert)
    config = {"params": {"min_confluence": 5, "max_trades_day": 3}}
    r = client.put("/api/v9/configs/1/SHADOW", json=config, headers=BRIDGE_HEADERS)
    assert r.status_code == 200

    # GET
    r = client.get("/api/v9/configs/1/SHADOW", headers=BRIDGE_HEADERS)
    assert r.status_code == 200
    assert r.json()["params"]["min_confluence"] == 5

    # GET all
    r = client.get("/api/v9/configs", headers=BRIDGE_HEADERS)
    assert r.status_code == 200
    assert len(r.json()["configs"]) == 1
