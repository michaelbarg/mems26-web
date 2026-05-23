"""V9 enhancement tests for DayTypeStateMachine.

Tests the NEW V9 methods (on_trigger, to_classification, update_cvd_state,
update_max_tpo_row_width) and new types (DayTypeClassification, DAY_TYPE_LOOKUP).

Does NOT test legacy process_bar() -- that's covered by existing test_day_type.py.

LOCKED 15/5 (option D, Hybrid): backward compat preserved, V9 methods added.
"""
import pytest
from datetime import datetime, timezone

from backend.v9.systems.day_type.state_machine import (
    DayTypeStateMachine,
    DayTypeClassification,
    DAY_TYPE_LOOKUP,
)
from backend.v9.systems.day_type.decision_matrix import DecisionMatrix
from backend.v9.systems.day_type.zohar_rules import ZoharRulesEngine
from backend.v9.systems.day_type.extensions import ExtensionTracker
from backend.v9.systems.day_type.triggers import TriggerEvent, TriggerType
from backend.v9.systems.day_type.schemas import DayType, OpeningType, IBWidth


def _trigger(ts_epoch: float) -> TriggerEvent:
    """Create a BAR_CLOSE trigger at given epoch timestamp."""
    return TriggerEvent(trigger_type=TriggerType.BAR_CLOSE, ts=ts_epoch)


def _make_v9_state_machine() -> DayTypeStateMachine:
    """Create state machine with all V9 collaborators."""
    return DayTypeStateMachine(
        zohar_engine=ZoharRulesEngine(),
        extension_tracker=ExtensionTracker(),
        decision_matrix=DecisionMatrix(),
    )


# -- BACKWARD COMPAT TESTS ------------------------------------------------

def test_backward_compat_no_optional_args():
    """Old API: DayTypeStateMachine() still works."""
    sm = DayTypeStateMachine()
    assert sm is not None
    assert hasattr(sm, 'config')


def test_backward_compat_process_bar_signature():
    """process_bar(bar) still callable."""
    sm = DayTypeStateMachine()
    assert hasattr(sm, 'process_bar')
    assert callable(sm.process_bar)


# -- V9 ENHANCEMENT TESTS -------------------------------------------------

def test_on_trigger_returns_none_before_state():
    """on_trigger before process_bar -> None."""
    sm = _make_v9_state_machine()
    result = sm.on_trigger(_trigger(1747310400.0))
    assert result is None


def test_to_classification_returns_none_before_state():
    """to_classification before process_bar -> None."""
    sm = _make_v9_state_machine()
    result = sm.to_classification()
    assert result is None


def test_update_cvd_state_stores():
    """update_cvd_state stores the latest state."""
    sm = _make_v9_state_machine()
    sm.update_cvd_state("confirmation_bull")
    assert sm._latest_cvd_state == "confirmation_bull"


def test_update_max_tpo_row_width_stores():
    """update_max_tpo_row_width stores the count."""
    sm = _make_v9_state_machine()
    sm.update_max_tpo_row_width(7)
    assert sm._max_tpo_row_width == 7


def test_day_type_lookup_complete():
    """DAY_TYPE_LOOKUP covers all 6 day types per Zohar."""
    assert DAY_TYPE_LOOKUP[DayType.Trend_Normal]["directional"] == "HIGH"
    assert DAY_TYPE_LOOKUP[DayType.Trend_Normal]["trading"] == "LOW"
    assert DAY_TYPE_LOOKUP[DayType.Variation]["trading"] == "HIGH"
    assert DAY_TYPE_LOOKUP[DayType.Nontrend]["trading"] == "MEDIUM"


def test_decision_matrix_get_probabilities_returns_dict():
    """DecisionMatrix.get_probabilities returns dict with 6 day types."""
    dm = DecisionMatrix()
    probs = dm.get_probabilities(opening_type="od", width_class="NARROW")
    assert isinstance(probs, dict)
    assert len(probs) == 7
    assert sum(probs.values()) == pytest.approx(1.0, abs=0.01)


def test_decision_matrix_od_narrow_favors_trend_normal():
    """OD + NARROW -> trend_normal highest probability."""
    dm = DecisionMatrix()
    probs = dm.get_probabilities(opening_type="od", width_class="NARROW")
    winner = max(probs, key=lambda k: probs[k])
    assert winner == "trend_normal"


def test_decision_matrix_oa_in_narrow_favors_nontrend():
    """OA_IN + NARROW -> nontrend highest probability."""
    dm = DecisionMatrix()
    probs = dm.get_probabilities(opening_type="oa_in", width_class="NARROW")
    winner = max(probs, key=lambda k: probs[k])
    assert winner == "nontrend"


def test_day_type_classification_dataclass_fields():
    """DayTypeClassification has all 13 fields from spec."""
    fields_expected = {
        "timestamp", "day_type", "probability",
        "directional_certainty", "trading_confidence",
        "ib_h", "ib_l", "ib_width", "ib_width_class",
        "opening_type", "last_updated_at", "reasoning_notes",
        "active_zohar_rules",
    }
    actual_fields = set(DayTypeClassification.__dataclass_fields__.keys())
    assert fields_expected == actual_fields, (
        f"Missing: {fields_expected - actual_fields}, "
        f"Extra: {actual_fields - fields_expected}"
    )


def test_no_locked_at_field_in_classification():
    """LOCKED 15/5: NO locked_at, only last_updated_at."""
    fields = set(DayTypeClassification.__dataclass_fields__.keys())
    assert "locked_at" not in fields
    assert "last_updated_at" in fields


def test_no_status_enum_in_classification():
    """LOCKED 15/5: DayTypeClassification has NO status field."""
    fields = set(DayTypeClassification.__dataclass_fields__.keys())
    assert "status" not in fields
    assert "lock_state" not in fields
