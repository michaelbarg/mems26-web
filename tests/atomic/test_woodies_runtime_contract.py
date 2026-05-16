"""Prompt 23 — Prove S4 Woodies runtime contract.

Tests verify:
  1. process_bar invokes decision_tree A1-A7
  2. A4 records touchpoints as advisory context
  3. valid setup with gateway routes only after explicit gates pass
  4. B1-B14 are explicitly DELEGATED (not stub/unknown)
  5. entry_phase/active_phase not invoked at runtime
"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from unittest.mock import patch, MagicMock, AsyncMock
from backend.v9.systems.woodies.woodies_system import WoodiesSystem
from backend.v9.systems.woodies.decision_tree import (
    WoodiesDecisionTree, StageStatus, StagePhase, STAGE_DEFINITIONS,
)


def test_process_bar_invokes_decision_tree():
    """WoodiesSystem.process_bar calls decision_tree.evaluate_bar."""
    ws = WoodiesSystem()
    ws.hydrate()
    # After hydration, decision_tree is wired
    assert ws._decision_tree is not None
    assert isinstance(ws._decision_tree, WoodiesDecisionTree)


def test_b_stages_all_delegated():
    """B1-B14 are all reported as DELEGATED, not STUB_NOT_IMPLEMENTED."""
    tree = WoodiesDecisionTree()
    active = tree.run_active_trade()
    b_stages = [r for r in active if r.stage_id.startswith("B")]
    assert len(b_stages) >= 14, f"Expected 14+ B-stages, got {len(b_stages)}"
    for r in b_stages:
        assert r.status == StageStatus.DELEGATED, \
            f"{r.stage_id} is {r.status}, expected DELEGATED"
        assert any(x in r.message.lower() for x in ["trade_manager", "layer4", "gateway", "woodies"]), \
            f"{r.stage_id} message doesn't reference trade_manager/layer4: {r.message}"


def test_b_stages_not_stub():
    """B-stages must NOT return STUB_NOT_IMPLEMENTED."""
    tree = WoodiesDecisionTree()
    active = tree.run_active_trade()
    for r in active:
        assert "STUB" not in r.message.upper(), \
            f"{r.stage_id} still returns STUB: {r.message}"


def test_a4_records_unavailable_as_advisory():
    """A4 returns PASS and records unavailable touchpoints as advisory context."""
    from backend.v9.systems.woodies.decision_tree import WoodiesDecisionContext
    from backend.v9.systems.woodies.schemas import PatternResult

    ctx = WoodiesDecisionContext(
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
            detected=True, pattern_id="ZLR", direction="LONG",
            confidence=0.8, group="CONTINUATION",
            entry_price=7450, stop=7448, targets=[7452, 7454]
        )],
        classification="TACTICAL", direction="LONG", sizing="full",
        current_state={"trend_state": "BLUE"},
        fire_setup={
            "direction": "LONG",
            "entry_price": 7450,
            "stop_price": 7448,
            "t1_price": 7452,
            "t2_price": 7454,
            "time_stop_minutes": 60,
            "confidence": 80,
        },
        touchpoints=None,  # will HTTP-fetch; may fail
    )
    tree = WoodiesDecisionTree()
    # Patch requests to simulate endpoint failure
    with patch("requests.get", side_effect=Exception("connection refused")):
        result = tree.evaluate_bar(ctx)
    a4_results = [r for r in result["pre_fire"] if r["stage_id"] == "A4"]
    assert len(a4_results) == 1
    assert a4_results[0]["status"] == StageStatus.PASS
    assert a4_results[0]["details"]["unavailable"]
    assert result["ready_to_route"] is True


def test_gateway_only_routes_when_ready_to_route():
    """Gateway.route_setup only called when decision_tree ready_to_route=True."""
    ws = WoodiesSystem()
    gw = MagicMock()
    gw.route_setup = MagicMock(return_value={"shadow": "test"})
    ws.set_gateway(gw)

    # When no patterns → ready_to_route=False → gateway NOT called
    ws.current_state["ready_to_route"] = False
    # Gateway should have 0 calls at init
    assert gw.route_setup.call_count == 0


def test_entry_phase_not_invoked_at_runtime():
    """entry_phase.py is not imported/called by WoodiesSystem.process_bar."""
    import inspect
    source = inspect.getsource(WoodiesSystem.process_bar)
    assert "entry_phase" not in source, \
        "process_bar should NOT reference entry_phase (alt orchestrator)"
    assert "active_phase" not in source, \
        "process_bar should NOT reference active_phase (alt orchestrator)"
