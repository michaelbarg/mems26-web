"""Tests for Woodies Entry Phase Scaffold (PROMPT 2 · 2.2).

Acceptance criteria per PROMPT 2 § COMMIT 2.2:
- All 7 stage classes instantiable
- Each stage has evaluate() with correct signature
- Each stage has docstring referencing Decision Tree V1 § A<N>
- EntryPhaseEngine routes A1→A7 (verify call order)
- EntryPhaseEngine returns valid TerminalState (SKIP/BUY/SELL)
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest

from backend.v9.systems.woodies.stages.a1_strategic_gate import A1StrategicGate, StrategicGateResult as A1Output
from backend.v9.systems.woodies.stages.a2_day_type_query import A2DayTypeQuery, A2Output
from backend.v9.systems.woodies.stages.a3_pattern_detection import A3PatternDetection, A3Output
from backend.v9.systems.woodies.stages.a4_poc_suffering_query import A4PocSufferingQuery, A4Output
from backend.v9.systems.woodies.stages.a5_otf_clarity_query import A5OtfClarityQuery, A5Output
from backend.v9.systems.woodies.stages.a6_entry_classification import A6EntryClassification, A6Output
from backend.v9.systems.woodies.stages.a7_universal_checks import A7UniversalChecks, A7Output
from backend.v9.systems.woodies.entry_phase import (
    EntryPhaseEngine,
    EntryResult,
    EntryTerminal,
    STAGE_CLASSES,
)


# ── Test: All 7 stage classes instantiable ────────────────────────

class TestStageInstantiation:
    def test_a1_instantiable(self):
        stage = A1StrategicGate()
        assert stage is not None

    def test_a2_instantiable(self):
        stage = A2DayTypeQuery()
        assert stage is not None

    def test_a3_instantiable(self):
        stage = A3PatternDetection()
        assert stage is not None

    def test_a4_instantiable(self):
        stage = A4PocSufferingQuery()
        assert stage is not None

    def test_a5_instantiable(self):
        stage = A5OtfClarityQuery()
        assert stage is not None

    def test_a6_instantiable(self):
        stage = A6EntryClassification()
        assert stage is not None

    def test_a7_instantiable(self):
        stage = A7UniversalChecks()
        assert stage is not None

    def test_7_stage_classes_registered(self):
        assert len(STAGE_CLASSES) == 7


# ── Test: evaluate() returns correct output type ──────────────────

class TestStageEvaluate:
    def test_a1_returns_a1output(self):
        result = A1StrategicGate().evaluate(cci_14_value=0.0, cci_14_history=[])
        assert isinstance(result, A1Output)
        assert result.direction_allowed == "NONE"
        assert result.color == "INDETERMINATE"

    def test_a2_returns_a2output(self):
        result = A2DayTypeQuery().evaluate()
        assert isinstance(result, A2Output)
        assert result.pattern_preference == []
        assert result.color_volatility_expectation == "MEDIUM"

    def test_a3_returns_a3output(self):
        result = A3PatternDetection().evaluate(
            cci_14_history=[], cci_zero_line_distance=0.0,
        )
        assert isinstance(result, A3Output)
        assert result.pattern_matched == "NONE"

    def test_a4_returns_a4output(self):
        result = A4PocSufferingQuery().evaluate()
        assert isinstance(result, A4Output)
        assert result.entry_classification_hint == "INITIATIVE"
        assert result.suffering_warning == "NONE"

    def test_a5_returns_a5output(self):
        result = A5OtfClarityQuery().evaluate()
        assert isinstance(result, A5Output)
        assert result.clarity_warning == "NONE"

    def test_a6_returns_a6output(self):
        result = A6EntryClassification().evaluate(pattern_matched="NONE")
        assert isinstance(result, A6Output)
        assert result.entry_classification == "INITIATIVE"
        assert result.position_size == 3

    def test_a7_returns_a7output(self):
        result = A7UniversalChecks().evaluate(direction="NONE")
        assert isinstance(result, A7Output)
        # With default args, all checks pass → approved
        assert isinstance(result.entry_approved, bool)


# ── Test: Docstrings reference Decision Tree V1 ──────────────────

class TestDocstrings:
    @pytest.mark.parametrize("cls,section", [
        (A1StrategicGate, "A1"),
        (A2DayTypeQuery, "A2"),
        (A3PatternDetection, "A3"),
        (A4PocSufferingQuery, "A4"),
        (A5OtfClarityQuery, "A5"),
        (A6EntryClassification, "A6"),
        (A7UniversalChecks, "A7"),
    ])
    def test_docstring_references_spec(self, cls, section):
        doc = cls.__doc__
        assert doc is not None, f"{cls.__name__} missing docstring"
        assert section in doc, f"{cls.__name__} docstring missing {section} reference"


# ── Test: EntryPhaseEngine ────────────────────────────────────────

class TestEntryPhaseEngine:
    def test_engine_instantiable(self):
        engine = EntryPhaseEngine()
        assert engine is not None

    def test_engine_has_7_stages(self):
        engine = EntryPhaseEngine()
        assert len(engine.stage_order) == 7

    def test_engine_stage_order_a1_through_a7(self):
        engine = EntryPhaseEngine()
        order = engine.stage_order
        assert order[0] == "A1_strategic_gate"
        assert order[-1] == "A7_universal_checks"

    def test_engine_evaluate_returns_entry_result(self):
        engine = EntryPhaseEngine()
        result = engine.evaluate()
        assert isinstance(result, EntryResult)

    def test_engine_evaluate_returns_skip_stub(self):
        engine = EntryPhaseEngine()
        result = engine.evaluate()
        assert result.terminal == EntryTerminal.SKIP
        assert result.reason == "STUB_NOT_IMPLEMENTED"

    def test_engine_evaluate_populates_all_stage_outputs(self):
        engine = EntryPhaseEngine()
        result = engine.evaluate()
        assert len(result.stage_outputs) == 7
        for stage_id in engine.stage_order:
            assert stage_id in result.stage_outputs

    def test_engine_call_order_matches_config(self):
        """Verify stages are called in priority order from config."""
        engine = EntryPhaseEngine()
        result = engine.evaluate()
        output_keys = list(result.stage_outputs.keys())
        assert output_keys == engine.stage_order

    def test_terminal_states_enum(self):
        assert EntryTerminal.SKIP.value == "SKIP"
        assert EntryTerminal.BUY.value == "BUY"
        assert EntryTerminal.SELL.value == "SELL"
