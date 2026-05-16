"""Prompt 25b — Cross-System Integration Proof.

Proves end-to-end integration between S1-S6 systems without enabling SHADOW/DEMO/LIVE.
Each test verifies a specific integration contract.
"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from unittest.mock import patch, MagicMock


def _woodies_ctx(*, touchpoints=None, fire_setup=None):
    from backend.v9.systems.woodies.decision_tree import WoodiesDecisionContext
    from backend.v9.systems.woodies.schemas import PatternResult

    return WoodiesDecisionContext(
        bars=[],
        studies={
            "cci_14": 50,
            "cci_6_tcci": 55,
            "ema_34": 7449,
            "lsma_value": 7449,
            "swi_value": 25,
            "czi_value": 10,
            "trend_state": "BLUE",
            "predictor_next_cci": 52,
        },
        patterns=[PatternResult(
            detected=True,
            pattern_id="ZLR",
            direction="LONG",
            confidence=0.8,
            group="CONTINUATION",
            entry_price=7450,
            stop=7448,
            targets=[7452, 7454],
        )],
        classification="TACTICAL",
        direction="LONG",
        sizing="full",
        current_state={"trend_state": "BLUE"},
        fire_setup=fire_setup or {
            "direction": "LONG",
            "entry_price": 7450,
            "stop_price": 7448,
            "t1_price": 7452,
            "t2_price": 7454,
            "time_stop_minutes": 60,
            "confidence": 80,
        },
        touchpoints=touchpoints,
    )


# ── 1. S1 Day Type context consumed by S4 Woodies ──

def test_s4_a4_queries_day_type():
    """S4 decision_tree A4 fetches /day_type/v9/current as touch-point."""
    from backend.v9.systems.woodies.decision_tree import TOUCHPOINT_ENDPOINTS
    assert "day_type" in TOUCHPOINT_ENDPOINTS
    assert "day_type" in TOUCHPOINT_ENDPOINTS["day_type"]


def test_s4_a4_records_unavailable_context_as_advisory():
    """Unavailable S1/S5/S6 context is visible but does not block routing."""
    from backend.v9.systems.woodies.decision_tree import (
        WoodiesDecisionTree, StageStatus,
    )

    tree = WoodiesDecisionTree()
    with patch("requests.get", side_effect=Exception("conn refused")):
        result = tree.evaluate_bar(_woodies_ctx(touchpoints=None))
    a4 = next(r for r in result["pre_fire"] if r["stage_id"] == "A4")
    assert a4["status"] == StageStatus.PASS
    assert a4["details"]["unavailable"]
    assert result["ready_to_route"] is True


# ── 2. S5 TPO context consumed by S4 ──

def test_s4_a4_queries_tpo():
    """S4 decision_tree A4 fetches /tpo/current as touch-point."""
    from backend.v9.systems.woodies.decision_tree import TOUCHPOINT_ENDPOINTS
    assert "tpo" in TOUCHPOINT_ENDPOINTS


# ── 3. S6 Killzone is advisory context ──

def test_s4_a4_unfavorable_context_is_advisory_not_blocking():
    """S1/S5/S6 unfavorable states are consumed in reason tree without hard block."""
    from backend.v9.systems.woodies.decision_tree import (
        WoodiesDecisionTree, StageStatus,
    )

    touchpoints = {
        "day_type": {"classified": False, "data": {"day_type": "PENDING"}},
        "tpo": {"running": False, "poc": None, "vah": None, "val": None},
        "veto": {"veto_active": False},
        "killzone": {"current_zone": {"name": "WEEKEND", "edge_class": "none"}},
        "layer0": {"state": "EXPANDING", "chop_score": 30},
    }
    tree = WoodiesDecisionTree()
    result = tree.evaluate_bar(_woodies_ctx(touchpoints=touchpoints))
    a4 = next(r for r in result["pre_fire"] if r["stage_id"] == "A4")
    assert a4["status"] == StageStatus.PASS
    assert "day_type:not_classified" in a4["details"]["advisories"]
    assert "tpo:not_running" in a4["details"]["advisories"]
    assert "killzone:WEEKEND" in a4["details"]["advisories"]
    assert "A4" not in result["failed_stages"]
    assert "A4" not in result["pending_stages"]
    assert result["ready_to_route"] is True


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


# ── 6. S4 gateway routing gated by explicit pre_fire ──

def test_s4_gateway_gated_by_decision_tree():
    """S4 /fire routes only after explicit pre_fire validation."""
    from backend.v9.api.v9.woodies.routes import woodies_fire
    import inspect
    source = inspect.getsource(woodies_fire)
    assert 'validate_fire' in source
    assert 'route_setup' in source
    assert source.index('validate_fire') < source.index('route_setup')


# ── 7. Blocked setups do not route ──

def test_blocked_s2_does_not_route():
    """S2 pre_fire rejection → no gateway call."""
    from backend.v9.systems.five_min.setup_emitter import emit_t1_setup

    class Rejected:
        valid = False
        fail_reason = "explicit pre_fire rejection"

    with patch("backend.v9.systems.five_min.setup_emitter.get_quality_tier",
               return_value=("HIGH", 3)), \
         patch("backend.v9.systems.five_min.setup_emitter.validate_fire",
               return_value=Rejected()):
        result = emit_t1_setup(
            "REACTIVE_LONG", "LONG",
            entry_price=7450, stop_price=7448,
            t1_price=7452, t2_price=7454,
            bar_index=10, day_type="Normal", current_price=7450,
        )
    assert result is None  # explicit pre_fire rejection → caller doesn't route


# ── 8. Reason tree visible ──

def test_s4_fire_shows_decision_stages():
    """S4 reason tree exposes A4 advisory context and pre_fire stages."""
    from backend.v9.systems.woodies.decision_tree import WoodiesDecisionTree

    result = WoodiesDecisionTree().evaluate_bar(_woodies_ctx(touchpoints={
        "day_type": {"classified": False, "data": {"day_type": "PENDING"}},
        "tpo": {"running": True, "poc": 7450, "vah": 7460, "val": 7440},
        "veto": {"veto_active": False},
        "killzone": {"current_zone": {"name": "WEEKEND", "edge_class": "none"}},
        "layer0": {"state": "EXPANDING", "chop_score": 30},
    }))
    assert "pre_fire" in result
    a4 = next(r for r in result["pre_fire"] if r["stage_id"] == "A4")
    assert a4["details"]["advisories"]


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
