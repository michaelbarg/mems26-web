"""W1b — GET /api/v9/account/state endpoint tests (2026-07-25).

Reads sierra_state.json (NOT DB synthesis). Returns all fields + open trade
from TM + reconciler verdict. Missing fields = None (Rule 1).
"""
import json
import time
import types
from pathlib import Path

import pytest


def _mk_state_file(tmp_path, data):
    p = tmp_path / "sierra_state.json"
    p.write_text(json.dumps(data))
    return p


def test_read_state_ok(tmp_path, monkeypatch):
    """Fresh state file → ok=True, stale=False, all fields returned."""
    import backend.v9.api.v9.account_state_routes as mod
    state_path = _mk_state_file(tmp_path, {
        "ts": int(time.time()),
        "is_sim": 0,
        "order_placement_armed": 1,
        "position_qty": 2,
        "avg_price": 7460.25,
        "working_orders": 4,
        "open_pnl": 125.50,
        "daily_pnl": -35.0,
        "high_during_pos": 7489.75,
        "low_during_pos": 7455.00,
        "trade_account": "37138283",
        "symbol": "MESQ26",
        "daily_total_qty_filled": 8,
        "last_price": 7478.50,
        "orders": [],
    })
    monkeypatch.setattr(mod, "STATE", state_path)

    result = mod._read_state()
    assert result["ok"] is True
    assert result["stale"] is False
    assert result["position_qty"] == 2
    assert result["avg_price"] == 7460.25
    assert result["open_pnl"] == 125.50
    assert result["trade_account"] == "37138283"


def test_read_state_missing(tmp_path, monkeypatch):
    """Missing state file → ok=False."""
    import backend.v9.api.v9.account_state_routes as mod
    monkeypatch.setattr(mod, "STATE", tmp_path / "nonexistent.json")

    result = mod._read_state()
    assert result["ok"] is False
    assert result["stale"] is True


def test_verdict_flat(tmp_path, monkeypatch):
    """position_qty=0 and no open trade → verdict='flat'."""
    import backend.v9.api.v9.account_state_routes as mod
    state_path = _mk_state_file(tmp_path, {
        "position_qty": 0, "avg_price": 0.0, "working_orders": 0,
        "is_sim": 0, "order_placement_armed": 1,
    })
    monkeypatch.setattr(mod, "STATE", state_path)

    # Mock request with no trade_manager
    req = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace()))
    result = mod.account_state(req)
    assert result["verdict"] == "flat"
    assert result["open_trade"] is None
    assert result["sierra_state"]["position_qty"] == 0


def test_verdict_system(tmp_path, monkeypatch):
    """position_qty!=0 and TM has open trade → verdict='system'."""
    import backend.v9.api.v9.account_state_routes as mod
    state_path = _mk_state_file(tmp_path, {
        "position_qty": 2, "avg_price": 7460.25, "working_orders": 4,
        "is_sim": 0, "order_placement_armed": 1,
    })
    monkeypatch.setattr(mod, "STATE", state_path)

    trade = types.SimpleNamespace(
        id=513, direction="LONG", entry_price=7460.25, stop=7444.0,
        t1=7476.0, t2=7492.0, t3=None, state="FILLED", mode="live",
        pattern="ZLR", quality={"contracts": 2},
    )
    tm = types.SimpleNamespace(get_active_trades=lambda: [trade])
    req = types.SimpleNamespace(app=types.SimpleNamespace(
        state=types.SimpleNamespace(trade_manager=tm)))

    result = mod.account_state(req)
    assert result["verdict"] == "system"
    assert result["open_trade"]["id"] == 513
    assert result["open_trade"]["direction"] == "LONG"
    assert result["open_trade"]["contracts"] == 2


def test_verdict_manual(tmp_path, monkeypatch):
    """position_qty!=0 but no TM trade → verdict='manual' (Michael's position)."""
    import backend.v9.api.v9.account_state_routes as mod
    state_path = _mk_state_file(tmp_path, {
        "position_qty": -2, "avg_price": 7490.0, "working_orders": 2,
        "is_sim": 0, "order_placement_armed": 1,
    })
    monkeypatch.setattr(mod, "STATE", state_path)

    tm = types.SimpleNamespace(get_active_trades=lambda: [])
    req = types.SimpleNamespace(app=types.SimpleNamespace(
        state=types.SimpleNamespace(trade_manager=tm)))

    result = mod.account_state(req)
    assert result["verdict"] == "manual"


def test_missing_w1_fields_none(tmp_path, monkeypatch):
    """Pre-W1 sierra_state (no new fields) → all W1 fields are None."""
    import backend.v9.api.v9.account_state_routes as mod
    state_path = _mk_state_file(tmp_path, {
        "position_qty": 0, "avg_price": 0.0, "working_orders": 0,
        "is_sim": 1, "order_placement_armed": 1,
    })
    monkeypatch.setattr(mod, "STATE", state_path)

    req = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace()))
    result = mod.account_state(req)

    s = result["sierra_state"]
    assert s["open_pnl"] is None
    assert s["daily_pnl"] is None
    assert s["high_during_pos"] is None
    assert s["low_during_pos"] is None
    assert s["trade_account"] is None
    assert s["symbol"] is None
    assert s["daily_total_qty_filled"] is None
    assert s["last_price"] is None
