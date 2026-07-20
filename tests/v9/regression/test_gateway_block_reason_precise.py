"""07-20: blocked decisions must carry precise reason for UI (not gate-key only).

Display-only: trading outcome unchanged; reason is what the playbook already computed.
"""
from __future__ import annotations

from backend.v9.gateway import trading_gateway as tg
from backend.v9.systems.daytype_playbook import Decision


def _gw(monkeypatch):
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})
    monkeypatch.setattr(
        gw,
        "_capture_cross_context",
        lambda: {
            "day_type_machine": {"day_type": "Variation"},
            "woodies_system": {"trend_state": "BLUE"},
            "tpo_system": {"vah": 7528.25, "val": 7506.25, "ib_width": 46.25},
        },
    )
    return gw


def test_playbook_block_records_precise_reason(monkeypatch):
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setenv("DAYTYPE_POSITION_GATE", "0")
    monkeypatch.setenv("REQUIRE_WITH_TREND_DAY_DIRECTION_V1", "1")
    monkeypatch.setattr(
        "backend.v9.systems.daytype_playbook.decide",
        lambda *a, **k: Decision(
            "SKIP", 0, "REACTIVE responsive SHORT not at VAH (below_value) on Variation"
        ),
    )
    monkeypatch.setattr(
        tg,
        "extract_g1_entry_context",
        lambda cc: {"day_type_at_entry": "Variation"},
    )
    monkeypatch.setattr(tg, "resolve_pattern_id", lambda setup, g1: "REACTIVE_SHORT")

    gw = _gw(monkeypatch)
    setup = {
        "direction": "SHORT",
        "classification": "REACTIVE_SHORT",
        "metadata": {"pattern": "REACTIVE_SHORT"},
        "entry_price": 7503.0,
        "stop": 7511.0,
        "t1": 7495.0,
    }
    res = gw.route_setup(setup, 2)
    assert res.get("blocked_by") == "daytype_playbook"
    assert "not at VAH" in (res.get("reason") or "")
    d = gw.decisions[-1]
    assert d["blocked_by"] == "daytype_playbook"
    assert d.get("reason") and "not at VAH" in d["reason"]


def test_shadow_decision_reason_is_none(monkeypatch):
    """Pass path: reason absent/None — UI falls back to GATE_HE."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "0")
    gw = _gw(monkeypatch)
    gw.route_setup(
        {
            "direction": "SHORT",
            "classification": "REACTIVE_SHORT",
            "metadata": {"pattern": "REACTIVE_SHORT"},
            "entry_price": 7503.0,
            "stop": 7511.0,
            "t1": 7495.0,
        },
        2,
    )
    d = gw.decisions[-1]
    assert d["blocked_by"] is None
    assert d.get("reason") in (None, "")
