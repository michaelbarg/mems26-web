"""Tests for Woodies Active Phase Scaffold (PROMPT 2 · 2.3).

Acceptance criteria per PROMPT 2 § COMMIT 2.3:
- All 14 stage classes instantiable
- Each stage has correct priority_class attribute
- Each stage has docstring referencing Decision Tree V1 § B<N>
- ActivePhaseEngine routes B1→B14 (verify call order)
- ActivePhaseEngine returns valid ActiveAction
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest

from backend.v9.systems.woodies.stages.b1_stop_check import B1StopCheck, B1Output
from backend.v9.systems.woodies.stages.b2_eod_check import B2EodCheck, B2Output
from backend.v9.systems.woodies.stages.b3_color_flip import B3ColorFlip, B3Output
from backend.v9.systems.woodies.stages.b4_poc_migration_query import B4PocMigrationQuery, B4Output
from backend.v9.systems.woodies.stages.b5_otf_mid_trade_query import B5OtfMidTradeQuery, B5Output
from backend.v9.systems.woodies.stages.b6_news_window import B6NewsWindow, B6Output
from backend.v9.systems.woodies.stages.b7_time_stop import B7TimeStop, B7Output
from backend.v9.systems.woodies.stages.b8_counter_pattern import B8CounterPattern, B8Output
from backend.v9.systems.woodies.stages.b9_market_state_query import B9MarketStateQuery, B9Output
from backend.v9.systems.woodies.stages.b10_t1_milestone import B10T1Milestone, B10Output
from backend.v9.systems.woodies.stages.b11_t2_milestone import B11T2Milestone, B11Output
from backend.v9.systems.woodies.stages.b12_t3_milestone import B12T3Milestone, B12Output
from backend.v9.systems.woodies.stages.b13_trail_check import B13TrailCheck, B13Output
from backend.v9.systems.woodies.stages.b14_hold import B14Hold, B14Output
from backend.v9.systems.woodies.active_phase import (
    ActiveAction,
    ActivePhaseEngine,
    ActiveResult,
    STAGE_CLASSES,
)


# ── All stage classes and expected attributes ─────────────────────

STAGE_INFO = [
    (B1StopCheck, "B1", "ABSOLUTE_EXIT", B1Output),
    (B2EodCheck, "B2", "ABSOLUTE_EXIT", B2Output),
    (B3ColorFlip, "B3", "STRATEGIC_EXIT", B3Output),
    (B4PocMigrationQuery, "B4", "ADVISORY_EXIT", B4Output),
    (B5OtfMidTradeQuery, "B5", "ADVISORY_EXIT", B5Output),
    (B6NewsWindow, "B6", "ABSOLUTE_EXIT", B6Output),
    (B7TimeStop, "B7", "TIME_EXIT", B7Output),
    (B8CounterPattern, "B8", "TIGHTEN", B8Output),
    (B9MarketStateQuery, "B9", "PARTIAL", B9Output),
    (B10T1Milestone, "B10", "TARGET", B10Output),
    (B11T2Milestone, "B11", "TARGET", B11Output),
    (B12T3Milestone, "B12", "TARGET", B12Output),
    (B13TrailCheck, "B13", "TRAIL", B13Output),
    (B14Hold, "B14", "NO_ACTION", B14Output),
]


# ── Test: All 14 stage classes instantiable ───────────────────────

class TestStageInstantiation:
    @pytest.mark.parametrize("cls,section,pc,out_cls", STAGE_INFO,
                             ids=[f"B{i+1}" for i in range(14)])
    def test_instantiable(self, cls, section, pc, out_cls):
        stage = cls()
        assert stage is not None

    def test_14_stage_classes_registered(self):
        assert len(STAGE_CLASSES) == 14


# ── Test: Correct priority_class attribute ────────────────────────

class TestPriorityClass:
    @pytest.mark.parametrize("cls,section,pc,out_cls", STAGE_INFO,
                             ids=[f"B{i+1}" for i in range(14)])
    def test_priority_class(self, cls, section, pc, out_cls):
        stage = cls()
        assert stage.priority_class == pc, (
            f"{cls.__name__}.priority_class should be {pc}, got {stage.priority_class}"
        )


# ── Test: Docstrings reference Decision Tree V1 ──────────────────

class TestDocstrings:
    @pytest.mark.parametrize("cls,section,pc,out_cls", STAGE_INFO,
                             ids=[f"B{i+1}" for i in range(14)])
    def test_docstring_references_spec(self, cls, section, pc, out_cls):
        doc = cls.__doc__
        assert doc is not None, f"{cls.__name__} missing docstring"
        assert section in doc, f"{cls.__name__} docstring missing {section} reference"


# ── Test: evaluate() returns correct output type ──────────────────

class TestStageEvaluate:
    def test_b1_returns_output(self):
        r = B1StopCheck().evaluate(current_price=7400, stop_price=7390, direction="LONG")
        assert isinstance(r, B1Output)
        assert r.action == "HOLD"

    def test_b2_returns_output(self):
        r = B2EodCheck().evaluate(current_time_et="12:00")
        assert isinstance(r, B2Output)
        assert r.action == "HOLD"

    def test_b3_returns_output(self):
        r = B3ColorFlip().evaluate(current_color="BLUE", entry_color="BLUE", direction="LONG")
        assert isinstance(r, B3Output)
        assert r.action == "HOLD"

    def test_b4_returns_output(self):
        r = B4PocMigrationQuery().evaluate()
        assert isinstance(r, B4Output)

    def test_b5_returns_output(self):
        r = B5OtfMidTradeQuery().evaluate()
        assert isinstance(r, B5Output)

    def test_b6_returns_output(self):
        r = B6NewsWindow().evaluate()
        assert isinstance(r, B6Output)

    def test_b7_returns_output(self):
        r = B7TimeStop().evaluate()
        assert isinstance(r, B7Output)

    def test_b8_returns_output(self):
        r = B8CounterPattern().evaluate()
        assert isinstance(r, B8Output)

    def test_b9_returns_output(self):
        r = B9MarketStateQuery().evaluate()
        assert isinstance(r, B9Output)

    def test_b10_returns_output(self):
        r = B10T1Milestone().evaluate(current_price=7400, t1_price=7410, direction="LONG")
        assert isinstance(r, B10Output)

    def test_b11_returns_output(self):
        r = B11T2Milestone().evaluate(current_price=7400, t2_price=7420, direction="LONG")
        assert isinstance(r, B11Output)

    def test_b12_returns_output(self):
        r = B12T3Milestone().evaluate(current_price=7400, t3_price=7440, direction="LONG")
        assert isinstance(r, B12Output)

    def test_b13_returns_output(self):
        r = B13TrailCheck().evaluate()
        assert isinstance(r, B13Output)

    def test_b14_returns_output(self):
        r = B14Hold().evaluate()
        assert isinstance(r, B14Output)
        assert r.action == "HOLD"


# ── Test: ActivePhaseEngine ───────────────────────────────────────

class TestActivePhaseEngine:
    def test_engine_instantiable(self):
        engine = ActivePhaseEngine()
        assert engine is not None

    def test_engine_has_14_stages(self):
        engine = ActivePhaseEngine()
        assert len(engine.stage_order) == 14

    def test_engine_first_stage_is_absolute_exit(self):
        engine = ActivePhaseEngine()
        first = engine.stage_order[0]
        assert first in ("B1_stop_check", "B2_eod_check", "B6_news_window"), (
            f"First stage should be ABSOLUTE_EXIT, got {first}"
        )

    def test_engine_last_stage_is_hold(self):
        engine = ActivePhaseEngine()
        assert engine.stage_order[-1] == "B14_hold"

    def test_engine_evaluate_returns_active_result(self):
        engine = ActivePhaseEngine()
        result = engine.evaluate()
        assert isinstance(result, ActiveResult)

    def test_engine_evaluate_returns_hold_stub(self):
        engine = ActivePhaseEngine()
        result = engine.evaluate()
        assert result.action == ActiveAction.HOLD
        assert result.source_stage == "B14_hold"
        assert result.reason == "STUB_NOT_IMPLEMENTED"

    def test_engine_evaluate_populates_all_stage_outputs(self):
        engine = ActivePhaseEngine()
        result = engine.evaluate()
        assert len(result.stage_outputs) == 14

    def test_engine_priority_order_respected(self):
        """ABSOLUTE_EXIT stages come before TARGET stages."""
        engine = ActivePhaseEngine()
        order = engine.stage_order
        # Find indices of known stages
        abs_indices = [order.index(s) for s in order
                       if s in ("B1_stop_check", "B2_eod_check", "B6_news_window")]
        target_indices = [order.index(s) for s in order
                          if s in ("B10_t1_milestone", "B11_t2_milestone", "B12_t3_milestone")]
        if abs_indices and target_indices:
            assert max(abs_indices) < min(target_indices)

    def test_active_action_enum_values(self):
        assert ActiveAction.CLOSE_ALL.value == "CLOSE_ALL"
        assert ActiveAction.HOLD.value == "HOLD"
        assert ActiveAction.TIGHTEN.value == "TIGHTEN"
        assert ActiveAction.PARTIAL_CLOSE.value == "PARTIAL_CLOSE"
