"""P0-1 (cursor audit 07-22 16:14, verified by cowork): the structural T1 must
SURVIVE the real `route_setup` — both gateway stompers (DAYTYPE_TARGETS_STRUCTURAL
C1 + PATTERN_T1_OVERRIDE per-pattern shelf) skip t1 when T1_STRUCTURE_END_V1=1.

Reuses the anti-tautological route harness from test_t2t3_no_stomp_route.py:
REACTIVE_SHORT × Variation HAS a targets.yaml row (9.0pt) — without the guard,
setup t1 7500.0 becomes 7499.75 (proven by the existing route test).
"""
from __future__ import annotations

import zoneinfo

from backend.v9.gateway import trading_gateway as tg


TPO = {
    "ib_high": 7520.0, "ib_low": 7480.0, "poc": 7505.0,
    "vah": 7527.5, "val": 7490.0, "ib_width": 40.0,
}


def _isolate_gates(monkeypatch):
    for flag in (
        "DIRECTION_CONTEXT", "CONT_TREND_FILTER", "ZONE_LIMIT_ENTRY_V1",
        "LSMA_FLAT_GATE_V1", "DAYTYPE_POSITION_GATE", "RR_ENTRY_GATE_V1",
        "RISK_CONSECUTIVE_LOSS_LIMIT", "EOD_RISK_WINDOW_V1", "NEWS_BLACKOUT_V1",
        "OPENING_TYPE_GATE", "RISK_HALT_V1", "DAYTYPE_PLAYBOOK",
        "TARGET_ZONES_V1", "DAYTYPE_LOCATION_GATE", "REV_EDGE_DAY_STRUCTURE_V1",
    ):
        monkeypatch.setenv(flag, "0")


class _TZBoom:
    def __init__(self, *a, **k):
        raise RuntimeError("test: force IB-locked fail-open")


def _gw(monkeypatch):
    _isolate_gates(monkeypatch)
    monkeypatch.setenv("DAYTYPE_TARGETS_STRUCTURAL", "1")
    monkeypatch.setenv("T2T3_NO_STOMP_V1", "1")
    monkeypatch.setattr(zoneinfo, "ZoneInfo", _TZBoom)
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    monkeypatch.setattr(
        tg, "extract_g1_entry_context", lambda cc: {"day_type_at_entry": "Variation"})
    monkeypatch.setattr(tg, "resolve_pattern_id", lambda setup, g1: "REACTIVE_SHORT")
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})
    monkeypatch.setattr(
        gw, "_capture_cross_context",
        lambda: {
            "day_type_machine": {"day_type": "Variation"},
            "woodies_system": {"trend_state": "RED"},
            "tpo_system": dict(TPO),
        },
    )
    return gw


def _setup():
    # t1 = the SYSTEM's structural T1 (entry-structure end) — must survive
    return {
        "direction": "SHORT",
        "classification": "REACTIVE_SHORT",
        "metadata": {"pattern": "REACTIVE_SHORT"},
        "entry_price": 7508.75,
        "stop": 7515.0,
        "t1": 7496.5,
    }


def test_structural_t1_survives_route_when_flag_on(monkeypatch):
    monkeypatch.setenv("T1_STRUCTURE_END_V1", "1")
    gw = _gw(monkeypatch)
    setup = _setup()
    res = gw.route_setup(setup, 2)
    assert res.get("blocked_by") is None, f"unexpected block: {res}"
    # THE assertion: neither C1 nor the 9.0pt pattern shelf stomped it
    assert setup["t1"] == 7496.5, f"structural t1 stomped → {setup['t1']}"
    # structural t2/t3 still applied (POC / VAL shelves)
    assert setup.get("t2") is not None and setup.get("t3") is not None


def test_flag_off_byte_identical_legacy_stomp(monkeypatch):
    monkeypatch.delenv("T1_STRUCTURE_END_V1", raising=False)
    gw = _gw(monkeypatch)
    setup = _setup()
    res = gw.route_setup(setup, 2)
    assert res.get("blocked_by") is None, f"unexpected block: {res}"
    assert setup["t1"] == 7499.75  # entry − 9 (pattern table) — legacy exact


def test_flag_on_but_no_incoming_t1_falls_back(monkeypatch):
    """Guard requires an actual structural t1; t1=None → shelves apply as today."""
    monkeypatch.setenv("T1_STRUCTURE_END_V1", "1")
    gw = _gw(monkeypatch)
    setup = _setup()
    setup["t1"] = None
    res = gw.route_setup(setup, 2)
    assert res.get("blocked_by") is None, f"unexpected block: {res}"
    # No system t1 → the structural C1 fills the gap first and is then kept
    # (it IS a structural t1). Either way the gap is filled honestly.
    assert setup["t1"] is not None
