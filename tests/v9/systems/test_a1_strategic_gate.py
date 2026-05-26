"""Golden tests for A1 Strategic Gate (W-2).

Verifies D-092 §Trend State (4 states: BLUE/RED/YELLOW/GRAY)
and P-W5 LOCK A (YELLOW blocks ALL 9 patterns).
"""

import pytest

from backend.v9.systems.woodies.stages.a1_strategic_gate import (
    A1StrategicGate,
    StrategicGateResult,
    TrendState,
    BARS_PERSISTENCE_REQUIRED,
    STAGE1_CCI_THRESHOLD,
)


@pytest.fixture
def gate():
    return A1StrategicGate()


# ── 1. BLUE classification ──────────────────────────────────────────

def test_blue_classification(gate):
    # 9 bars above ZL, peak 110 (>+100 Stage-1)
    history = [10, 30, 60, 110, 90, 70, 80, 95, 105, 75]
    result = gate.evaluate(cci_14_value=75, cci_14_history=history)
    assert result.color == TrendState.BLUE
    assert result.direction_allowed == "LONG"
    assert result.terminal is None


# ── 2. BLUE fails — no bar >+100 (Stage-1 not met) ─────────────────

def test_blue_fails_no_plus100_touch(gate):
    # 9 bars above ZL but max 95 — no >+100
    history = [10, 30, 60, 80, 90, 70, 80, 95, 90, 75]
    result = gate.evaluate(cci_14_value=75, cci_14_history=history)
    assert result.color == TrendState.GRAY
    assert result.direction_allowed == "NONE"


# ── 3. BLUE fails — under 6 bars ───────────────────────────────────

def test_blue_fails_under_6_bars(gate):
    history = [-10, -5, 0, 30, 60, 110, 105]
    result = gate.evaluate(cci_14_value=105, cci_14_history=history)
    # Only 4 consecutive above ZL (after sign-flip at bar 3)
    assert result.color == TrendState.GRAY
    assert result.direction_allowed == "NONE"


# ── 4. RED classification ──────────────────────────────────────────

def test_red_classification(gate):
    history = [-10, -30, -60, -110, -90, -70, -80, -95, -105, -75]
    result = gate.evaluate(cci_14_value=-75, cci_14_history=history)
    assert result.color == TrendState.RED
    assert result.direction_allowed == "SHORT"
    assert result.terminal is None


# ── 5. YELLOW transition (BLUE → opposite bars) ───────────────────

def test_yellow_transition_blue_to_opposite(gate):
    # Establish prior RED (6+ bars below), then 6+ bars above = YELLOW
    # Prior RED: 6 bars below ZL with one <-100
    prior_red = [-30, -60, -110, -80, -70, -50]
    # Then BLUE run: 6+ bars above with one >+100
    blue_run = [20, 40, 60, 110, 90, 80, 70]
    history = prior_red + blue_run
    result = gate.evaluate(cci_14_value=70, cci_14_history=history)
    assert result.color == TrendState.YELLOW
    assert result.direction_allowed == "NONE"
    assert result.terminal is not None
    assert "YELLOW" in result.terminal
    assert "P-W5" in result.terminal


# ── 6. YELLOW blocks all 9 patterns (parameterized) ───────────────

@pytest.mark.parametrize("pattern_id", [
    "ZLR", "TLB", "TT", "GB100", "VEGAS", "GHOST", "FAMIR", "HTLB", "HFE",
])
def test_yellow_blocks_pattern(gate, pattern_id):
    """When A1 returns YELLOW, direction_allowed is NONE for all patterns."""
    # Setup YELLOW: prior RED then current BLUE run
    prior_red = [-30, -60, -110, -80, -70, -50]
    blue_run = [20, 40, 60, 110, 90, 80, 70]
    history = prior_red + blue_run
    result = gate.evaluate(cci_14_value=70, cci_14_history=history)
    # Regardless of pattern, A1 blocks with NONE
    assert result.direction_allowed == "NONE"
    assert result.color == TrendState.YELLOW


# ── 7. GRAY classification — choppy ───────────────────────────────

def test_gray_classification_choppy(gate):
    history = [10, -5, 8, -3, 15, -10, 12, -8, 5, -2]
    result = gate.evaluate(cci_14_value=-2, cci_14_history=history)
    assert result.color == TrendState.GRAY
    assert result.direction_allowed == "NONE"


# ── 8. GRAY — empty history ──────────────────────────────────────

def test_gray_empty_history(gate):
    result = gate.evaluate(cci_14_value=0, cci_14_history=[])
    assert result.color == TrendState.GRAY
    assert result.direction_allowed == "NONE"
    assert result.terminal is not None


# ── 9. RED → BLUE via YELLOW ─────────────────────────────────────

def test_red_to_blue_via_yellow(gate):
    # Prior BLUE (6+ bars above with one >+100), then RED run
    prior_blue = [30, 60, 110, 80, 70, 50]
    red_run = [-20, -40, -60, -110, -90, -80, -70]
    history = prior_blue + red_run
    result = gate.evaluate(cci_14_value=-70, cci_14_history=history)
    assert result.color == TrendState.YELLOW
    assert result.direction_allowed == "NONE"


# ── 10. No INDETERMINATE in TrendState ────────────────────────────

def test_indeterminate_collapses_to_gray():
    assert not hasattr(TrendState, "INDETERMINATE")
    assert set(TrendState) == {TrendState.BLUE, TrendState.RED, TrendState.YELLOW, TrendState.GRAY}


# ── 11. GREY spelling normalized to GRAY ─────────────────────────

def test_grey_spelling_normalized_to_gray():
    assert TrendState.GRAY.value == "GRAY"
    assert not hasattr(TrendState, "GREY")


# ── 12. YELLOW terminal message cites P-W5 ───────────────────────

def test_yellow_terminal_message_cites_pw5(gate):
    prior_red = [-30, -60, -110, -80, -70, -50]
    blue_run = [20, 40, 60, 110, 90, 80, 70]
    history = prior_red + blue_run
    result = gate.evaluate(cci_14_value=70, cci_14_history=history)
    assert "YELLOW" in result.terminal
    assert "P-W5" in result.terminal or "color veto" in result.terminal


# ── 13. BLUE requires current above zero ─────────────────────────

def test_blue_consecutive_from_most_recent(gate):
    # 6 bars above ZL with >+100 but current bar is negative
    history = [30, 60, 110, 80, 70, 50, -10]
    result = gate.evaluate(cci_14_value=-10, cci_14_history=history)
    # Most recent bar breaks the consecutive run
    assert result.color != TrendState.BLUE


# ── 14. Stage-1 threshold boundary ──────────────────────────────

def test_stage1_boundary_exactly_100_not_enough(gate):
    # 7 bars above ZL, peak exactly 100 (not >100)
    history = [10, 30, 60, 100, 90, 70, 80]
    result = gate.evaluate(cci_14_value=80, cci_14_history=history)
    assert result.color == TrendState.GRAY


def test_stage1_boundary_101_enough(gate):
    # 7 bars above ZL, peak 101 (>100)
    history = [10, 30, 60, 101, 90, 70, 80]
    result = gate.evaluate(cci_14_value=80, cci_14_history=history)
    assert result.color == TrendState.BLUE
    assert result.direction_allowed == "LONG"


# ── 15. Decision tree YELLOW block ────────────────────────────────

def test_decision_tree_a1_blocks_yellow():
    """Verify _a1_trend_gate in decision_tree.py blocks YELLOW."""
    from backend.v9.systems.woodies.decision_tree import _a1_trend_gate
    from unittest.mock import MagicMock

    ctx = MagicMock()
    ctx.studies = {"trend_state": "YELLOW"}
    ctx.patterns = [MagicMock(confidence=0.8)]

    result = _a1_trend_gate(ctx)
    assert result.status.value == "FAIL"
    assert "YELLOW" in result.message
    assert "P-W5" in result.message


def test_decision_tree_a1_normalizes_grey():
    """Verify _a1_trend_gate normalizes GREY to GRAY."""
    from backend.v9.systems.woodies.decision_tree import _a1_trend_gate
    from unittest.mock import MagicMock

    ctx = MagicMock()
    ctx.studies = {"trend_state": "GREY"}
    ctx.patterns = [MagicMock(confidence=0.4)]

    result = _a1_trend_gate(ctx)
    # GREY → GRAY, low confidence → FAIL
    assert result.status.value == "FAIL"
    assert "GRAY" in result.message
