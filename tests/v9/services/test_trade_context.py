"""Tests for SHADOW trade context extraction (pattern, trigger, PnL fields)."""

import os
from types import SimpleNamespace

os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")

from backend.v9.services.trade_context import (
    compute_trade_pnl,
    extract_system_agreement,
    extract_trade_display,
    extract_trade_insight,
)


def _trade(**kwargs):
    defaults = dict(
        quality=None,
        cross_context=None,
        firing_system=1,
        pnl_usd=-50.0,
        pnl_r=-1.0,
        outcome="LOSS",
        exit_reason="STOP_HIT",
        state="CLOSED",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_extract_from_quality_and_entry_row():
    t = _trade(
        quality={
            "classification": "TACTICAL",
            "confidence": 0.82,
            "trigger": "FIRE_LONG",
            "metadata": {"pattern": "CCI_CROSS_UP", "group": "woodies"},
        },
        cross_context=[
            {
                "trigger": "FIRE_LONG",
                "classification": "TACTICAL",
                "systems": {
                    "woodies_system": {"signal": "CCI_CROSS_UP", "day_type": "TREND"},
                    "day_type_machine": {"day_type": "TREND"},
                },
            }
        ],
    )
    d = extract_trade_display(t)
    assert d["pattern_id"] == "CCI_CROSS_UP"
    assert d["trigger"] == "FIRE_LONG"
    assert d["pnl_usd"] == -50.0
    assert d["day_type"] == "TREND"


def test_extract_legacy_dict_cross_context():
    t = _trade(
        cross_context={
            "systems": {
                "footprint_system": {"last_pattern": "ABSORPTION", "last_classification": "STRATEGIC"},
            }
        },
    )
    d = extract_trade_display(t)
    assert d["pattern_id"] == "ABSORPTION"
    assert d["footprint_classification"] == "STRATEGIC"


def test_extract_gateway_registry_top_level_keys():
    t = _trade(
        firing_system=4,
        cross_context={
            "footprint_system": {
                "last_pattern": "FIRE_SHORT",
                "last_classification": "TACTICAL",
            },
        },
    )
    d = extract_trade_display(t)
    assert d["pattern_id"] == "FIRE_SHORT"
    assert d["trigger"] == "FIRE_SHORT"
    assert d["classification"] == "TACTICAL"


def test_compute_trade_pnl_partial_two_hits():
    """PARTIAL with C1+C2 hit: realized sum only; C3 open at entry."""
    t = SimpleNamespace(
        entry_price=7435.25,
        direction="SHORT",
        stop=7438.25,
        t1=7431.25,
        t2=7427.25,
        t3=0.0,
        t1_hit_ts="2026-05-21T02:15:00",
        t2_hit_ts="2026-05-21T02:15:00",
        t3_hit_ts=None,
        state="PARTIAL",
        exit_reason=None,
        exit_price=None,
        pnl_usd=None,
        pnl_r=None,
    )
    pnl = compute_trade_pnl(t)
    assert pnl["pnl_mode"] == "partial"
    assert pnl["pnl_usd"] == 60.0  # C1 $20 + C2 $40
    assert len(pnl["contracts_pnl"]) == 3
    assert pnl["contracts_pnl"][0]["status"] == "HIT"
    assert pnl["contracts_pnl"][2]["status"] == "OPEN"
    assert pnl["contracts_pnl"][2]["pnl_usd"] == 0.0


from typing import Optional


def _killzone_trade(direction: str, edge: Optional[str]):
    """Helper: trade with a Killzone blob for RCA-1 regression tests."""
    blob: dict = {}
    if edge is not None:
        blob = {"current_zone": {"edge_class": edge, "name": "NY_OPEN"}}
    return _trade(
        firing_system=4,
        direction=direction,
        cross_context=[
            {
                "trigger": "ZLR",
                "systems": {
                    "killzone_system": blob,
                    "woodies_system": {"trend_state": "GREEN"},
                },
            }
        ],
    )


def _s6_agree(direction: str, edge: Optional[str]) -> Optional[bool]:
    t = _killzone_trade(direction, edge)
    agreements = extract_system_agreement(t)
    s6 = next(a for a in agreements if a["id"] == 6)
    return s6["agree"]


# RCA-1 regression tests — S6 (Killzone) direction-aware fix
def test_s6_high_edge_long_disagrees():
    """LONG trade at high edge: price at resistance → S6 disagrees."""
    assert _s6_agree("LONG", "high") is False


def test_s6_high_edge_short_agrees():
    """SHORT trade at high edge: fade off resistance → S6 agrees."""
    assert _s6_agree("SHORT", "high") is True


def test_s6_low_edge_long_agrees():
    """LONG trade at low edge: bounce off support → S6 agrees."""
    assert _s6_agree("LONG", "low") is True


def test_s6_low_edge_short_disagrees():
    """SHORT trade at low edge: fading support → S6 disagrees."""
    assert _s6_agree("SHORT", "low") is False


def test_s6_empty_blob_neutral():
    """Empty Killzone blob → neutral (None)."""
    assert _s6_agree("LONG", None) is None


def test_extract_trade_insight_fire_and_recognition():
    t = _trade(
        firing_system=4,
        direction="SHORT",
        cross_context=[
            {
                "trigger": "TLB",
                "classification": "TLB",
                "confidence": 0.82,
                "systems": {
                    "woodies_system": {"trend_state": "RED", "active_patterns": [{"pattern_id": "TLB"}]},
                    "footprint_system": {"last_signal": {"direction": "LONG", "signal": "sweep_return"}},
                },
            },
            {"trigger": "t1_hit", "systems": {"woodies_system": {"trend_state": "RED"}}},
        ],
    )
    ins = extract_trade_insight(t)
    assert "S4" in ins["fire"]["headline"]
    assert ins["fire"]["trigger"] == "TLB"
    assert len(ins["recognition"]) == 6
    s4 = next(r for r in ins["recognition"] if r["id"] == 4)
    assert s4["is_firing"] is True
    assert s4["agree"] is True
    s3 = next(r for r in ins["recognition"] if r["id"] == 3)
    assert s3["agree"] is False
    assert len(ins["lifecycle"]) >= 2


def test_flat_gateway_cross_context_recognition():
    """Legacy gateway persisted registry blobs at top level (no systems wrapper)."""
    t = _trade(
        firing_system=4,
        direction="SHORT",
        cross_context={
            "woodies_system": {
                "trend_state": "GRAY",
                "active_patterns": [{"pattern_id": "HTLB"}],
            },
            "five_min_system": {"mode": "DAY_TYPE_MODE", "last_confluence": 3},
            "day_type_machine": {"day_type": "Normal"},
        },
    )
    ins = extract_trade_insight(t)
    s4 = next(r for r in ins["recognition"] if r["id"] == 4)
    assert "No snapshot at entry" not in s4["lines"][0]
    assert any("HTLB" in ln or "GRAY" in ln for ln in s4["lines"])
    s2 = next(r for r in ins["recognition"] if r["id"] == 2)
    assert any("DAY_TYPE_MODE" in ln for ln in s2["lines"])
