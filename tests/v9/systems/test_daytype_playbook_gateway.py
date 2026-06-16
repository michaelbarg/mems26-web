"""Wiring regression: day-type playbook veto inside TradingGateway.route_setup.

Anti-tautological: drives the REAL route_setup and asserts result["blocked_by"]
(the real consumer). Removing the playbook block from route_setup → RED.
"""
import pytest

from backend.v9.gateway import trading_gateway as tg
from backend.v9.systems import daytype_playbook as P


@pytest.fixture(autouse=True)
def _reset():
    P.reset_cache()
    yield
    P.reset_cache()


def _gateway(monkeypatch, trend_state="RED"):
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    gw = tg.TradingGateway()
    # neutralize the DB-touching shadow execution (we only assert routing decisions)
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "test"})
    cc = {"day_type_machine": {"day_type": "Trend_Normal"},
          "woodies_system": {"trend_state": trend_state}}
    monkeypatch.setattr(gw, "_capture_cross_context", lambda: cc)
    return gw


def test_gateway_blocks_reversal_on_trend(monkeypatch):
    # HFE on a Trend day = SKIP → blocked. Remove the wiring → RED.
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    P.reset_cache()
    gw = _gateway(monkeypatch)
    res = gw.route_setup({"direction": "SHORT", "metadata": {"pattern": "HFE"}, "entry_price": 7600}, 4)
    assert res["blocked_by"] == "daytype_playbook"


def test_gateway_off_does_not_block(monkeypatch):
    # flag OFF → gate inert, never blocked by playbook.
    monkeypatch.delenv("DAYTYPE_PLAYBOOK", raising=False)
    P.reset_cache()
    gw = _gateway(monkeypatch)
    res = gw.route_setup({"direction": "SHORT", "metadata": {"pattern": "HFE"}, "entry_price": 7600}, 4)
    assert res["blocked_by"] != "daytype_playbook"


def test_gateway_allows_with_trend_reactive(monkeypatch):
    # REACTIVE long WITH the up-trend (BLUE) = allowed → not blocked by playbook.
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    P.reset_cache()
    gw = _gateway(monkeypatch, trend_state="BLUE")
    res = gw.route_setup({"direction": "LONG", "metadata": {"pattern": "REACTIVE_LONG"}, "entry_price": 7600}, 2)
    assert res["blocked_by"] != "daytype_playbook"
