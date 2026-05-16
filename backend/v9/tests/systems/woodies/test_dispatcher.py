"""Tests for Woodies Priority Hierarchy Dispatcher (PROMPT 3 · 3.1).

Acceptance: 5 conflict scenarios + tie-breaking + no-trigger default.
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest

from backend.v9.systems.woodies.dispatcher import (
    Dispatcher,
    DispatchResult,
    PriorityClass,
    StageOutput,
)


@pytest.fixture
def dispatcher():
    return Dispatcher()


def _out(stage_id, pc, action, triggered=True, yaml_order=0, reason=""):
    return StageOutput(
        stage_id=stage_id,
        priority_class=pc,
        action=action,
        triggered=triggered,
        yaml_order=yaml_order,
        reason=reason,
    )


# ── 5 Conflict Scenarios (per PROMPT 3 acceptance) ───────────────

class TestConflictScenarios:
    def test_b1_stop_beats_b11_t2(self, dispatcher):
        """B1 stop (ABSOLUTE) > B11 t2 (TARGET)."""
        outputs = [
            _out("B1_stop_check", PriorityClass.ABSOLUTE_EXIT, "CLOSE_ALL", yaml_order=0),
            _out("B11_t2_milestone", PriorityClass.TARGET, "CLOSE_C2", yaml_order=10),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B1_stop_check"
        assert result.winning_action == "CLOSE_ALL"
        assert result.winning_priority == PriorityClass.ABSOLUTE_EXIT

    def test_b3_flip_beats_b10_t1(self, dispatcher):
        """B3 color flip (STRATEGIC) > B10 t1 (TARGET)."""
        outputs = [
            _out("B3_color_flip", PriorityClass.STRATEGIC_EXIT, "CLOSE_ALL", yaml_order=2),
            _out("B10_t1_milestone", PriorityClass.TARGET, "CLOSE_C1", yaml_order=9),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B3_color_flip"
        assert result.winning_action == "CLOSE_ALL"

    def test_b6_news_beats_b4_advisory(self, dispatcher):
        """B6 news (ABSOLUTE) > B4 POC warning (ADVISORY)."""
        outputs = [
            _out("B4_poc_migration_query", PriorityClass.ADVISORY_EXIT, "TIGHTEN", yaml_order=3),
            _out("B6_news_window", PriorityClass.ABSOLUTE_EXIT, "CLOSE_ALL", yaml_order=5),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B6_news_window"
        assert result.winning_action == "CLOSE_ALL"

    def test_b8_tighten_beats_b9_partial(self, dispatcher):
        """B8 tighten (TIGHTEN) > B9 partial (PARTIAL)."""
        outputs = [
            _out("B8_counter_pattern", PriorityClass.TIGHTEN, "TIGHTEN_STOP", yaml_order=7),
            _out("B9_market_state_query", PriorityClass.PARTIAL, "PARTIAL_CLOSE", yaml_order=8),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B8_counter_pattern"
        assert result.winning_action == "TIGHTEN_STOP"

    def test_b14_hold_alone(self, dispatcher):
        """B14 hold alone → HOLD (NO_ACTION default)."""
        outputs = [
            _out("B14_hold", PriorityClass.NO_ACTION, "HOLD", yaml_order=13),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B14_hold"
        assert result.winning_action == "HOLD"
        assert result.winning_priority == PriorityClass.NO_ACTION


# ── Tie-breaking (same priority class) ───────────────────────────

class TestTieBreaking:
    def test_same_class_yaml_order_wins(self, dispatcher):
        """Within ABSOLUTE_EXIT, earlier YAML order wins."""
        outputs = [
            _out("B6_news_window", PriorityClass.ABSOLUTE_EXIT, "CLOSE_ALL", yaml_order=5),
            _out("B1_stop_check", PriorityClass.ABSOLUTE_EXIT, "CLOSE_ALL", yaml_order=0),
            _out("B2_eod_check", PriorityClass.ABSOLUTE_EXIT, "CLOSE_ALL", yaml_order=1),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B1_stop_check"

    def test_target_class_yaml_order(self, dispatcher):
        """Within TARGET, B10 (yaml_order=9) beats B11 (yaml_order=10)."""
        outputs = [
            _out("B11_t2_milestone", PriorityClass.TARGET, "CLOSE_C2", yaml_order=10),
            _out("B10_t1_milestone", PriorityClass.TARGET, "CLOSE_C1", yaml_order=9),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B10_t1_milestone"


# ── No triggers → default HOLD ───────────────────────────────────

class TestNoTriggers:
    def test_no_triggered_stages(self, dispatcher):
        """All stages have triggered=False → default HOLD."""
        outputs = [
            _out("B1_stop_check", PriorityClass.ABSOLUTE_EXIT, "CLOSE_ALL", triggered=False),
            _out("B3_color_flip", PriorityClass.STRATEGIC_EXIT, "CLOSE_ALL", triggered=False),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B14_hold"
        assert result.winning_action == "HOLD"
        assert result.all_triggered == []

    def test_empty_list(self, dispatcher):
        """Empty input → default HOLD."""
        result = dispatcher.resolve([])
        assert result.winning_stage == "B14_hold"
        assert result.winning_action == "HOLD"


# ── Multiple triggers from different classes ──────────────────────

class TestMultipleTriggers:
    def test_three_classes_highest_wins(self, dispatcher):
        """STRATEGIC + TIGHTEN + TRAIL → STRATEGIC wins."""
        outputs = [
            _out("B13_trail_check", PriorityClass.TRAIL, "CLOSE_C3", yaml_order=12),
            _out("B8_counter_pattern", PriorityClass.TIGHTEN, "TIGHTEN_STOP", yaml_order=7),
            _out("B3_color_flip", PriorityClass.STRATEGIC_EXIT, "CLOSE_ALL", yaml_order=2),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B3_color_flip"
        assert len(result.all_triggered) == 3

    def test_all_triggered_listed(self, dispatcher):
        """All triggered stages appear in all_triggered list."""
        outputs = [
            _out("B1_stop_check", PriorityClass.ABSOLUTE_EXIT, "CLOSE_ALL", yaml_order=0),
            _out("B10_t1_milestone", PriorityClass.TARGET, "CLOSE_C1", yaml_order=9),
            _out("B14_hold", PriorityClass.NO_ACTION, "HOLD", yaml_order=13),
        ]
        result = dispatcher.resolve(outputs)
        assert "B1_stop_check" in result.all_triggered
        assert "B10_t1_milestone" in result.all_triggered
        assert "B14_hold" in result.all_triggered


# ── PriorityClass IntEnum ordering ────────────────────────────────

class TestPriorityClassEnum:
    def test_absolute_is_highest(self):
        assert PriorityClass.ABSOLUTE_EXIT < PriorityClass.STRATEGIC_EXIT

    def test_no_action_is_lowest(self):
        assert PriorityClass.NO_ACTION > PriorityClass.TRAIL

    def test_9_priority_classes(self):
        assert len(PriorityClass) == 9

    def test_hierarchy_order(self):
        expected = [
            PriorityClass.ABSOLUTE_EXIT,
            PriorityClass.STRATEGIC_EXIT,
            PriorityClass.ADVISORY_EXIT,
            PriorityClass.TIME_EXIT,
            PriorityClass.TARGET,
            PriorityClass.TIGHTEN,
            PriorityClass.PARTIAL,
            PriorityClass.TRAIL,
            PriorityClass.NO_ACTION,
        ]
        for i in range(len(expected) - 1):
            assert expected[i] < expected[i + 1]
