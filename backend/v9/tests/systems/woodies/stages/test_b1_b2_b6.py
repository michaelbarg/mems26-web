"""Tests for B1+B2+B6 Absolute Exits (PROMPT 3 · 3.4).

Acceptance:
- B1: stop-hit LONG and SHORT (4 scenarios)
- B2: triggers at 15:59 ET
- B6: Tier 1 within ±5min → CLOSE ALL, Tier 2 reduces
- All emit ABSOLUTE_EXIT priority class
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.stages.b1_stop_check import B1StopCheck, B1Output
from backend.v9.systems.woodies.stages.b2_eod_check import B2EodCheck, B2Output
from backend.v9.systems.woodies.stages.b6_news_window import B6NewsWindow, B6Output


# ── B1 Stop Check ────────────────────────────────────────────────

class TestB1StopCheck:
    def test_long_stop_hit(self):
        result = B1StopCheck().evaluate(current_price=7390, stop_price=7395, direction="LONG")
        assert result.stop_hit is True
        assert result.action == "CLOSE_ALL"

    def test_long_stop_exact(self):
        result = B1StopCheck().evaluate(current_price=7395, stop_price=7395, direction="LONG")
        assert result.stop_hit is True

    def test_long_no_stop(self):
        result = B1StopCheck().evaluate(current_price=7400, stop_price=7395, direction="LONG")
        assert result.stop_hit is False
        assert result.action == "HOLD"

    def test_short_stop_hit(self):
        result = B1StopCheck().evaluate(current_price=7410, stop_price=7405, direction="SHORT")
        assert result.stop_hit is True
        assert result.action == "CLOSE_ALL"

    def test_short_no_stop(self):
        result = B1StopCheck().evaluate(current_price=7400, stop_price=7405, direction="SHORT")
        assert result.stop_hit is False

    def test_priority_class(self):
        assert B1StopCheck().priority_class == "ABSOLUTE_EXIT"


# ── B2 EOD Check ─────────────────────────────────────────────────

class TestB2EodCheck:
    def test_triggers_at_1559(self):
        result = B2EodCheck().evaluate(current_time_et="15:59")
        assert result.eod_force is True
        assert result.action == "CLOSE_ALL"

    def test_triggers_at_1600(self):
        result = B2EodCheck().evaluate(current_time_et="16:00")
        assert result.eod_force is True

    def test_no_trigger_at_1558(self):
        result = B2EodCheck().evaluate(current_time_et="15:58")
        assert result.eod_force is False
        assert result.action == "HOLD"

    def test_no_trigger_midday(self):
        result = B2EodCheck().evaluate(current_time_et="12:00")
        assert result.eod_force is False

    def test_invalid_time_no_force(self):
        result = B2EodCheck().evaluate(current_time_et="invalid")
        assert result.eod_force is False

    def test_priority_class(self):
        assert B2EodCheck().priority_class == "ABSOLUTE_EXIT"


# ── B6 News Window ───────────────────────────────────────────────

class TestB6NewsWindow:
    def test_tier1_within_5min_closes_all(self):
        result = B6NewsWindow().evaluate(
            news_calendar={"minutes_to_next_tier1": 3},
            position_size=2,
        )
        assert result.news_exit is True
        assert result.action == "CLOSE_ALL"

    def test_tier1_negative_within_5min_closes(self):
        """Within ±5min means absolute value."""
        result = B6NewsWindow().evaluate(
            news_calendar={"minutes_to_next_tier1": -2},
        )
        assert result.news_exit is True

    def test_tier2_within_5min_reduces(self):
        result = B6NewsWindow().evaluate(
            news_calendar={"minutes_to_next_tier2": 4},
            position_size=3,
        )
        assert result.action == "REDUCE"

    def test_tier2_single_contract_holds(self):
        result = B6NewsWindow().evaluate(
            news_calendar={"minutes_to_next_tier2": 4},
            position_size=1,
        )
        assert result.action == "HOLD"

    def test_no_news_holds(self):
        result = B6NewsWindow().evaluate(news_calendar=None)
        assert result.action == "HOLD"

    def test_tier1_far_away_holds(self):
        result = B6NewsWindow().evaluate(
            news_calendar={"minutes_to_next_tier1": 30},
        )
        assert result.action == "HOLD"

    def test_priority_class(self):
        assert B6NewsWindow().priority_class == "ABSOLUTE_EXIT"
