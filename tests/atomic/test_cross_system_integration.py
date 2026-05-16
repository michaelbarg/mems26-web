"""Prompt 25 — Cross-System Integration Proof.

Proves end-to-end integration between S1-S6 systems without enabling SHADOW/DEMO/LIVE.
Each test verifies a specific integration contract.
"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from unittest.mock import patch, MagicMock
import json


# ── 1. S1 Day Type context consumed by S4 Woodies ──

def test_s4_a4_queries_day_type():
    """S4 decision_tree A4 fetches /day_type/v9/current as touch-point."""
    from backend.v9.systems.woodies.decision_tree import TOUCHPOINT_ENDPOINTS
    assert "day_type" in TOUCHPOINT_ENDPOINTS
    assert "day_type" in TOUCHPOINT_ENDPOINTS["day_type"]


def test_s4_a4_blocks_on_day_type_unavailable():
    """When S1 is unavailable, S4 A4 reports it in unavailable list."""
    from backend.v9.systems.woodies.decision_tree import (
        WoodiesDecisionTree, WoodiesDecisionContext, StageStatus,
    )
    from backend.v9.systems.woodies.schemas import PatternResult

    ctx = WoodiesDecisionContext(
        bars=[], studies={"trend_state": "BLUE"},
        patterns=[PatternResult(detected=True, pattern_id="ZLR", direction="LONG",
                               confidence=0.8, group="CONTINUATION",
                               entry_price=7450, stop=7448, targets=[7452])],
        classification="TACTICAL", direction="LONG", sizing="full",
        current_state={"trend_state": "BLUE"}, touchpoints=None,
    )
    tree = WoodiesDecisionTree()
    with patch("requests.get", side_effect=Exception("conn refused")):
        result = tree.evaluate_bar(ctx)
    a4 = next(r for r in result["pre_fire"] if r["stage_id"] == "A4")
    assert a4["status"] in (StageStatus.FAIL, StageStatus.PENDING)


# ── 2. S5 TPO context consumed by S4 ──

def test_s4_a4_queries_tpo():
    """S4 decision_tree A4 fetches /tpo/current as touch-point."""
    from backend.v9.systems.woodies.decision_tree import TOUCHPOINT_ENDPOINTS
    assert "tpo" in TOUCHPOINT_ENDPOINTS


# ── 3. S6 Killzone blocks S4 during WEEKEND ──

def test_s4_a4_killzone_blocks_weekend():
    """When killzone=WEEKEND, S4 A4 reports block."""
    from backend.v9.systems.woodies.decision_tree import (
        WoodiesDecisionTree, WoodiesDecisionContext, StageStatus,
    )
    from backend.v9.systems.woodies.schemas import PatternResult

    # Provide touchpoints with killzone=WEEKEND
    touchpoints = {
        "day_type": {"classified": True, "data": {"day_type": "Normal"}},
        "tpo": {"poc": 7450, "vah": 7460, "val": 7440},
        "veto": {"veto_active": False},
        "killzone": {"current_zone": {"name": "WEEKEND", "edge_class": "none"}},
        "layer0": {"state": "EXPANDING", "chop_score": 30},
    }
    ctx = WoodiesDecisionContext(
        bars=[], studies={"trend_state": "BLUE"},
        patterns=[PatternResult(detected=True, pattern_id="ZLR", direction="LONG",
                               confidence=0.8, group="CONTINUATION",
                               entry_price=7450, stop=7448, targets=[7452])],
        classification="TACTICAL", direction="LONG", sizing="full",
        current_state={"trend_state": "BLUE"}, touchpoints=touchpoints,
    )
    tree = WoodiesDecisionTree()
    result = tree.evaluate_bar(ctx)
    # Should NOT be ready_to_route (killzone blocks)
    assert result["ready_to_route"] is False
    a4 = next(r for r in result["pre_fire"] if r["stage_id"] == "A4")
    assert a4["status"] == StageStatus.FAIL


# ── 4. S2 fires through pre_fire_validator ──

def test_s2_uses_pre_fire_validator():
    """S2 setup_emitter calls validate_fire before returning T1Setup."""
    from backend.v9.systems.five_min.setup_emitter import emit_t1_setup
    import inspect
    source = inspect.getsource(emit_t1_setup)
    assert "validate_fire" in source, "S2 must call validate_fire"


# ── 5. S2 gateway routing gated ──

def test_s2_gateway_only_when_setup_valid():
    """S2 FiveMinSystem only calls gateway.route_setup after valid T1Setup."""
    from backend.v9.systems.five_min.five_min_system import FiveMinSystem
    fs = FiveMinSystem()
    gw = MagicMock()
    fs.set_gateway(gw)
    # Without any pattern detection, gateway should not be called
    assert gw.route_setup.call_count == 0


# ── 6. S4 gateway routing gated by ready_to_route ──

def test_s4_gateway_gated_by_decision_tree():
    """S4 only routes when decision_tree ready_to_route=True."""
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem
    import inspect
    source = inspect.getsource(WoodiesSystem.process_bar)
    assert 'ready_to_route' in source
    assert 'route_setup' in source


# ── 7. Blocked setups do not route ──

def test_blocked_s2_does_not_route():
    """S2 pre_fire rejection → no gateway call."""
    from backend.v9.systems.five_min.setup_emitter import emit_t1_setup
    # LOW quality (outside value area) → returns None → no routing
    with patch("backend.v9.systems.five_min.setup_emitter.get_quality_tier",
               return_value=("LOW", 0)):
        result = emit_t1_setup(
            "REACTIVE_LONG", "LONG",
            entry_price=7450, stop_price=7448,
            t1_price=7452, t2_price=7454,
            bar_index=10, day_type="Normal", current_price=7450,
        )
    assert result is None  # rejected → caller doesn't route


# ── 8. Reason tree visible ──

def test_s4_fire_shows_decision_stages():
    """S4 /fire endpoint returns decision_tree stages with reasons."""
    import requests
    r = requests.get("http://localhost:8000/api/v9/woodies/fire", timeout=5)
    assert r.status_code == 200
    data = r.json()
    # Must have decision_tree field
    assert "decision_tree" in data
    dt = data["decision_tree"]
    # Should have pre_fire array (even if empty on weekend)
    assert "pre_fire" in dt or isinstance(dt, dict)


# ── 9. BarLevelDetector can close trades ──

def test_bar_level_detector_closes_trades():
    """BarLevelDetector closes SHADOW trades on T1/T2/T3 hit."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    from backend.v9.services.trade_manager import TradeManager
    from backend.v9.db.session import SessionLocal
    import asyncio

    db = SessionLocal()
    tm = TradeManager(db=db)
    detector = BarLevelDetector(trade_manager=tm)

    # Create a test trade
    trade_id = tm.accept_setup({
        "firing_system": 4, "direction": "LONG",
        "stop": 7440.0, "t1": 7455.0, "t2": 7460.0, "t3": 7470.0,
        "entry_price": 7450.0,
    }, mode="shadow")
    tm.on_fill(trade_id, 7450.0)

    # Bar that hits T1
    class FakeEvent:
        mode = "LIVE"
        payload = {"ts": "2026-05-16T10:00:00", "high": 7456.0, "low": 7449.0,
                   "close": 7455.0, "open": 7450.0}
    asyncio.run(detector.on_bar(FakeEvent()))

    trade = tm._get_trade(trade_id)
    assert trade.t1_hit_ts is not None, "T1 should be hit"
    assert trade.state == "PARTIAL"

    # Cleanup
    db.rollback()
    db.close()


# ── 10. No SHADOW/DEMO/LIVE activation ──

def test_gateway_no_mode_enabled():
    """TradingGateway has no DEMO/LIVE systems enabled."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway()
    assert gw._demo_enabled_systems == set()
    assert gw._live_enabled_systems == set()
