"""Wiring regression: direction-context veto inside TradingGateway.route_setup (#68).

Anti-tautological: drives the REAL route_setup and asserts result["blocked_by"].
Flipping the live direction (UP<->DOWN) flips WHICH side is blocked — proving the
gate consults direction_context, not a constant. Removing the block from
route_setup → RED. Flag DIRECTION_CONTEXT default-OFF → inert (last test).
"""
import pytest

from backend.v9.gateway import trading_gateway as tg
from backend.v9.systems import direction_context_live as DCL


def _gateway(monkeypatch):
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    gw = tg.TradingGateway()
    # neutralize the DB-touching shadow execution (we only assert routing decisions)
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "test"})
    cc = {"day_type_machine": {"day_type": "Trend_Normal"},
          "woodies_system": {"trend_state": "BLUE"}}
    monkeypatch.setattr(gw, "_capture_cross_context", lambda: cc)
    return gw


def _set_dc(monkeypatch, d):
    monkeypatch.setattr(DCL, "current",
                        lambda: {"dir": d, "reason": "test", "breakout_state": "x"})


def test_blocks_short_when_context_up(monkeypatch):
    monkeypatch.setenv("DIRECTION_CONTEXT", "1")
    _set_dc(monkeypatch, "UP")
    gw = _gateway(monkeypatch)
    res = gw.route_setup(
        {"direction": "SHORT", "metadata": {"pattern": "REACTIVE_SHORT"}, "entry_price": 7600}, 2)
    assert res["blocked_by"] == "direction_context"


def test_flip_context_down_blocks_long(monkeypatch):
    # SAME long setup; context now DOWN → the LONG is now the wrong side → blocked.
    monkeypatch.setenv("DIRECTION_CONTEXT", "1")
    _set_dc(monkeypatch, "DOWN")
    gw = _gateway(monkeypatch)
    res = gw.route_setup(
        {"direction": "LONG", "metadata": {"pattern": "REACTIVE_LONG"}, "entry_price": 7600}, 2)
    assert res["blocked_by"] == "direction_context"


def test_allows_with_direction_long_when_up(monkeypatch):
    # LONG WITH an UP context → not blocked by direction_context.
    monkeypatch.setenv("DIRECTION_CONTEXT", "1")
    _set_dc(monkeypatch, "UP")
    gw = _gateway(monkeypatch)
    res = gw.route_setup(
        {"direction": "LONG", "metadata": {"pattern": "REACTIVE_LONG"}, "entry_price": 7600}, 2)
    assert res["blocked_by"] != "direction_context"


def test_neutral_context_does_not_block(monkeypatch):
    # NEUTRAL/chop context → no direction veto (stand-aside is for the gate to allow,
    # other gates decide); direction_context itself must not block.
    monkeypatch.setenv("DIRECTION_CONTEXT", "1")
    _set_dc(monkeypatch, "NEUTRAL")
    gw = _gateway(monkeypatch)
    res = gw.route_setup(
        {"direction": "SHORT", "metadata": {"pattern": "REACTIVE_SHORT"}, "entry_price": 7600}, 2)
    assert res["blocked_by"] != "direction_context"


def test_flag_off_does_not_block(monkeypatch):
    # flag OFF (default) → gate inert even with a conflicting context.
    monkeypatch.delenv("DIRECTION_CONTEXT", raising=False)
    _set_dc(monkeypatch, "UP")
    gw = _gateway(monkeypatch)
    res = gw.route_setup(
        {"direction": "SHORT", "metadata": {"pattern": "REACTIVE_SHORT"}, "entry_price": 7600}, 2)
    assert res["blocked_by"] != "direction_context"
