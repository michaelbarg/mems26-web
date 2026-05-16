"""Tests for A7 Universal Pre-Entry Checks (PROMPT 3 · 3.3).

Acceptance: all 6 checks enforced, each failure produces correct skip_reason.
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.stages.a7_universal_checks import A7UniversalChecks, A7Output


@pytest.fixture
def stage():
    return A7UniversalChecks()


class TestAllChecksPass:
    def test_all_pass_approves_entry(self, stage):
        result = stage.evaluate(
            direction="LONG",
            news_calendar=None,
            cool_down_state=False,
            daily_pnl=0.0,
            proposed_stop_pts=5.0,
            bridge_health=True,
            time_to_eod_minutes=120.0,
        )
        assert result.entry_approved is True
        assert result.skip_reason is None


class TestNewsWindow:
    def test_tier1_within_5min_blocks(self, stage):
        result = stage.evaluate(
            direction="LONG",
            news_calendar={"minutes_to_next_tier1": 3},
        )
        assert result.entry_approved is False
        assert result.skip_reason == "NEWS_WINDOW"


class TestCoolDown:
    def test_cool_down_active_blocks(self, stage):
        result = stage.evaluate(direction="LONG", cool_down_state=True)
        assert result.entry_approved is False
        assert result.skip_reason == "COOL_DOWN_ACTIVE"


class TestDailyLossCap:
    def test_loss_cap_hit_blocks(self, stage):
        result = stage.evaluate(direction="LONG", daily_pnl=-200.0)
        assert result.entry_approved is False
        assert result.skip_reason == "DAILY_LOSS_CAP"

    def test_under_cap_allows(self, stage):
        result = stage.evaluate(direction="LONG", daily_pnl=-199.0)
        assert result.entry_approved is True


class TestStopDistance:
    def test_stop_below_3pt_blocks(self, stage):
        result = stage.evaluate(direction="LONG", proposed_stop_pts=2.0)
        assert result.entry_approved is False
        assert result.skip_reason == "STOP_OUT_OF_RANGE"

    def test_stop_above_8pt_blocks(self, stage):
        result = stage.evaluate(direction="LONG", proposed_stop_pts=9.0)
        assert result.entry_approved is False
        assert result.skip_reason == "STOP_OUT_OF_RANGE"

    def test_stop_at_3pt_allows(self, stage):
        result = stage.evaluate(direction="LONG", proposed_stop_pts=3.0)
        assert result.entry_approved is True

    def test_stop_at_8pt_allows(self, stage):
        result = stage.evaluate(direction="LONG", proposed_stop_pts=8.0)
        assert result.entry_approved is True


class TestBridgeHealth:
    def test_bridge_unhealthy_blocks(self, stage):
        result = stage.evaluate(direction="LONG", bridge_health=False)
        assert result.entry_approved is False
        assert result.skip_reason == "BRIDGE_UNHEALTHY"


class TestEodDistance:
    def test_less_than_60min_blocks(self, stage):
        result = stage.evaluate(direction="LONG", time_to_eod_minutes=30.0)
        assert result.entry_approved is False
        assert result.skip_reason == "TOO_CLOSE_TO_EOD"

    def test_exactly_60min_allows(self, stage):
        result = stage.evaluate(direction="LONG", time_to_eod_minutes=60.0)
        assert result.entry_approved is True
