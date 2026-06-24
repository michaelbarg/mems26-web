"""Wiring regression: opening-type gate INSIDE TradingGateway.route_setup (#68 FIX B).

Anti-tautological at the GATEWAY level — proves the RTH bars actually reach the gate
through the system_registry["day_type_machine"]._opening_gate_bars path (the exact
plumbing that was dead-wired in an earlier draft: self._app never set). Drives the
REAL route_setup and asserts result["blocked_by"]. If the bars don't reach the gate,
it fail-opens and blocked_by != "opening_type_gate" → RED.
"""
import pytest

from backend.v9.gateway import trading_gateway as tg

# 06-22 first-hour shape: OPEN_DRIVE UP (drove off the open, no return through it).
DRIVE_UP_BARS = [
    {"o": 7527, "h": 7540, "l": 7525, "c": 7538, "v": 5000},
    {"o": 7538, "h": 7555, "l": 7536, "c": 7552, "v": 5000},
    {"o": 7552, "h": 7568, "l": 7550, "c": 7565, "v": 5000},
    {"o": 7565, "h": 7580, "l": 7563, "c": 7578, "v": 5000},
    {"o": 7578, "h": 7590, "l": 7575, "c": 7588, "v": 5000},
    {"o": 7588, "h": 7599, "l": 7585, "c": 7595, "v": 5000},
]


class _FakeDTM:
    def __init__(self, bars):
        self._opening_gate_bars = bars


def _gateway(monkeypatch, bars, ib_locked=False):
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "test"})
    # the live plumbing: bars exposed on day_type_machine in the system registry
    gw.set_system_registry({"day_type_machine": _FakeDTM(bars)})
    cc = {"day_type_machine": {}, "woodies_system": {},
          "tpo_system": {"ib_locked": ib_locked}}
    monkeypatch.setattr(gw, "_capture_cross_context", lambda: cc)
    return gw


def test_gateway_blocks_counter_drive_short(monkeypatch):
    # OPEN_DRIVE UP + SHORT → blocked BY THE GATEWAY (proves bars reached the gate).
    monkeypatch.setenv("OPENING_TYPE_GATE", "1")
    gw = _gateway(monkeypatch, DRIVE_UP_BARS, ib_locked=False)
    res = gw.route_setup({"direction": "SHORT", "metadata": {"pattern": "HFE"}, "entry_price": 7595}, 4)
    assert res["blocked_by"] == "opening_type_gate"


def test_gateway_allows_with_drive_long(monkeypatch):
    monkeypatch.setenv("OPENING_TYPE_GATE", "1")
    gw = _gateway(monkeypatch, DRIVE_UP_BARS, ib_locked=False)
    res = gw.route_setup({"direction": "LONG", "metadata": {"pattern": "ZLR"}, "entry_price": 7595}, 4)
    assert res["blocked_by"] != "opening_type_gate"


def test_gateway_inert_post_ib_lock(monkeypatch):
    # IB locked → gate inert even on a counter-drive short.
    monkeypatch.setenv("OPENING_TYPE_GATE", "1")
    gw = _gateway(monkeypatch, DRIVE_UP_BARS, ib_locked=True)
    res = gw.route_setup({"direction": "SHORT", "metadata": {"pattern": "HFE"}, "entry_price": 7595}, 4)
    assert res["blocked_by"] != "opening_type_gate"


def test_gateway_flag_off_inert(monkeypatch):
    monkeypatch.delenv("OPENING_TYPE_GATE", raising=False)
    gw = _gateway(monkeypatch, DRIVE_UP_BARS, ib_locked=False)
    res = gw.route_setup({"direction": "SHORT", "metadata": {"pattern": "HFE"}, "entry_price": 7595}, 4)
    assert res["blocked_by"] != "opening_type_gate"


def test_gateway_empty_bars_fail_open(monkeypatch):
    # No bars reach the gate (dead-wiring scenario) → fail-open, NOT blocked.
    # This documents that the block only bites when bars are present.
    monkeypatch.setenv("OPENING_TYPE_GATE", "1")
    gw = _gateway(monkeypatch, [], ib_locked=False)
    res = gw.route_setup({"direction": "SHORT", "metadata": {"pattern": "HFE"}, "entry_price": 7595}, 4)
    assert res["blocked_by"] != "opening_type_gate"
