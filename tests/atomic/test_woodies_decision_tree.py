"""Atomic tests — Woodies 21-stage decision tree (Option B)."""
from backend.v9.systems.woodies.decision_tree import (
    STAGE_DEFINITIONS,
    StagePhase,
    StageStatus,
    WoodiesDecisionContext,
    WoodiesDecisionTree,
    all_stage_ids,
)
from backend.v9.systems.woodies.schemas import PatternResult, WoodiesBar


def _bar(**kwargs) -> WoodiesBar:
    defaults = dict(
        ts=1.0, open=100.0, high=101.0, low=99.0, close=100.5, volume=1000.0,
        cci_14=50.0, cci_6_tcci=55.0, ema_34=100.0, lsma_value=99.5,
        swi_value=25.0, czi_value=10.0, trend_state="BLUE",
        predictor_next_cci=52.0,
    )
    defaults.update(kwargs)
    return WoodiesBar(**defaults)


def _pattern() -> PatternResult:
    return PatternResult(
        detected=True,
        pattern_id="ZLR", direction="LONG", confidence=0.8, group="CONTINUATION",
        entry_price=100.0, stop=99.0, targets=[101.0, 102.0],
    )


def _studies(**kwargs):
    defaults = {"cci_14": 50, "cci_6_tcci": 55, "ema_34": 100, "lsma_value": 99,
                "swi_value": 25, "czi_value": 10, "trend_state": "BLUE", "predictor_next_cci": 52}
    defaults.update(kwargs)
    return defaults


def _touchpoints(**overrides):
    defaults = {
        "day_type": {"classified": True, "data": {"day_type": "Normal"}},
        "tpo": {"running": True, "poc": 100.0, "vah": 102.0, "val": 98.0},
        "veto": {"suffering_side": "NONE", "veto_active": False},
        "killzone": {"running": True, "current_zone": {"name": "NY_OPEN", "edge_class": "high"}},
        "layer0": {"state": "EXPANDING", "chop_score": 36.0},
    }
    defaults.update(overrides)
    return defaults


def _fire_setup(**kwargs):
    defaults = {
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_price": 99.0,
        "t1_price": 101.0,
        "t2_price": 102.0,
        "time_stop_minutes": 60,
        "confidence": 80,
    }
    defaults.update(kwargs)
    return defaults


def test_all_21_stages_defined():
    assert len(STAGE_DEFINITIONS) == 21
    assert len(all_stage_ids()) == 21
    assert len([s for s in STAGE_DEFINITIONS if s.phase == StagePhase.PRE_FIRE]) == 7
    assert len([s for s in STAGE_DEFINITIONS if s.phase == StagePhase.ACTIVE]) == 14


def test_pre_fire_skip_without_patterns():
    tree = WoodiesDecisionTree()
    ctx = WoodiesDecisionContext(
        bars=[_bar()],
        studies=_studies(),
        patterns=[],
        classification="NO_SETUP",
        direction=None,
        sizing="reject",
        current_state={},
    )
    pre = tree.run_pre_fire(ctx)
    a3 = next(r for r in pre if r.stage_id == "A3")
    assert a3.status == StageStatus.SKIP


def test_a6_maps_tactical_to_reactive():
    tree = WoodiesDecisionTree()
    pat = _pattern()
    ctx = WoodiesDecisionContext(
        bars=[_bar()],
        studies=_studies(),
        patterns=[pat],
        classification="TACTICAL",
        direction="LONG",
        sizing="half",
        current_state={},
        touchpoints=_touchpoints(),
    )
    pre = tree.run_pre_fire(ctx)
    a6 = next(r for r in pre if r.stage_id == "A6")
    assert a6.status == StageStatus.PASS
    assert a6.details["spec_classification"] == "REACTIVE"


def test_b_stages_all_delegated():
    tree = WoodiesDecisionTree()
    active = tree.run_active_trade({"trade_id": "t1"})
    assert len(active) == 14
    assert all(r.status == StageStatus.DELEGATED for r in active)


def test_a7_pre_fire_with_valid_setup():
    tree = WoodiesDecisionTree()
    ctx = WoodiesDecisionContext(
        bars=[_bar()],
        studies=_studies(),
        patterns=[],
        classification="TACTICAL",
        direction="LONG",
        sizing="half",
        current_state={},
        fire_setup=_fire_setup(),
    )
    a7 = next(r for r in tree.run_pre_fire(ctx) if r.stage_id == "A7")
    assert a7.status == StageStatus.PASS


def test_a4_touchpoints_pass_when_context_available():
    tree = WoodiesDecisionTree()
    ctx = WoodiesDecisionContext(
        bars=[_bar()],
        studies=_studies(),
        patterns=[_pattern()],
        classification="TACTICAL",
        direction="LONG",
        sizing="half",
        current_state={},
        fire_setup=_fire_setup(),
        touchpoints=_touchpoints(),
    )
    summary = tree.evaluate_bar(ctx)
    a4 = next(r for r in summary["pre_fire"] if r["stage_id"] == "A4")
    assert a4["status"] == StageStatus.PASS
    assert summary["ready_to_route"] is True


def test_a4_missing_context_stays_pending_and_blocks_route():
    tree = WoodiesDecisionTree()
    ctx = WoodiesDecisionContext(
        bars=[_bar()],
        studies=_studies(),
        patterns=[_pattern()],
        classification="TACTICAL",
        direction="LONG",
        sizing="half",
        current_state={},
        fire_setup=_fire_setup(),
        touchpoints={"day_type": {"classified": True, "data": {"day_type": "Normal"}}},
    )
    summary = tree.evaluate_bar(ctx)
    a4 = next(r for r in summary["pre_fire"] if r["stage_id"] == "A4")
    assert a4["status"] == StageStatus.PENDING
    assert "touch-point context unavailable" in a4["message"]
    assert summary["pending_stages"] == ["A4"]
    assert summary["ready_to_route"] is False


def test_ready_to_route_false_when_prefire_fails():
    tree = WoodiesDecisionTree()
    ctx = WoodiesDecisionContext(
        bars=[_bar()],
        studies=_studies(),
        patterns=[_pattern()],
        classification="TACTICAL",
        direction="LONG",
        sizing="half",
        current_state={},
        fire_setup=_fire_setup(stop_price=101.0),
        touchpoints=_touchpoints(),
    )
    summary = tree.evaluate_bar(ctx)
    assert "A7" in summary["failed_stages"]
    assert summary["ready_to_route"] is False


def test_shadow_env_does_not_bypass_missing_touchpoints(monkeypatch):
    monkeypatch.setenv("MEMS26_MODE", "shadow")
    tree = WoodiesDecisionTree()
    ctx = WoodiesDecisionContext(
        bars=[_bar()],
        studies=_studies(),
        patterns=[_pattern()],
        classification="TACTICAL",
        direction="LONG",
        sizing="half",
        current_state={},
        fire_setup=_fire_setup(),
        touchpoints={},
    )
    summary = tree.evaluate_bar(ctx)
    assert "A4" in summary["pending_stages"]
    assert summary["ready_to_route"] is False
