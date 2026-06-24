"""Wiring regression: idempotency dedup inside TradingGateway.route_setup.

Catches the 2026-06-22 double-fire (ids 199/200: identical S2 REACTIVE_SHORT @7537.75,
2.16s apart). Drives the REAL route_setup; asserts the SECOND identical fire is
blocked_by "duplicate_fire" while a different price/pattern is not. Flag DEDUP_FIRE_GUARD.
"""
import pytest

from backend.v9.gateway import trading_gateway as tg


def _gw(monkeypatch):
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})
    monkeypatch.setattr(gw, "_capture_cross_context",
                        lambda: {"day_type_machine": {}, "woodies_system": {}, "tpo_system": {}})
    return gw


def _setup(price=7537.75, pat="REACTIVE_SHORT", direction="SHORT"):
    return {"direction": direction, "classification": pat, "metadata": {"pattern": pat},
            "entry_price": price, "stop": 7546.25, "t1": 7531.38}


def test_second_identical_fire_blocked(monkeypatch):
    monkeypatch.setenv("DEDUP_FIRE_GUARD", "1")
    gw = _gw(monkeypatch)
    r1 = gw.route_setup(_setup(), 2)
    assert r1["blocked_by"] != "duplicate_fire"          # first passes dedup
    r2 = gw.route_setup(_setup(), 2)
    assert r2["blocked_by"] == "duplicate_fire"          # identical re-fire → blocked


def test_different_price_not_dup(monkeypatch):
    monkeypatch.setenv("DEDUP_FIRE_GUARD", "1")
    gw = _gw(monkeypatch)
    gw.route_setup(_setup(7537.75), 2)
    r2 = gw.route_setup(_setup(7530.0), 2)               # 7.75pt away → not a dup
    assert r2["blocked_by"] != "duplicate_fire"


def test_different_pattern_system_not_dup(monkeypatch):
    monkeypatch.setenv("DEDUP_FIRE_GUARD", "1")
    gw = _gw(monkeypatch)
    gw.route_setup(_setup(pat="REACTIVE_SHORT"), 2)
    r2 = gw.route_setup(_setup(pat="ZLR"), 4)            # different system+pattern (id201) → not a dup
    assert r2["blocked_by"] != "duplicate_fire"


def test_flag_off_allows_dup(monkeypatch):
    monkeypatch.delenv("DEDUP_FIRE_GUARD", raising=False)
    gw = _gw(monkeypatch)
    gw.route_setup(_setup(), 2)
    r2 = gw.route_setup(_setup(), 2)
    assert r2["blocked_by"] != "duplicate_fire"          # gate inert when flag off
