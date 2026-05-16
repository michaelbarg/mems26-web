"""Tests for B4+B5+B9+B10+B11+B12+B14 (PROMPT 3 · 3.6).

RULE 14: B4/B5/B9 are advisory — warnings, NEVER auto-exit.
B10: NO BE on T1 (D-002). B11: Smart BE on T2 Initiative (D-055).
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.stages.b4_poc_migration_query import B4PocMigrationQuery, B4Output
from backend.v9.systems.woodies.stages.b5_otf_mid_trade_query import B5OtfMidTradeQuery, B5Output
from backend.v9.systems.woodies.stages.b9_market_state_query import B9MarketStateQuery, B9Output
from backend.v9.systems.woodies.stages.b10_t1_milestone import B10T1Milestone, B10Output
from backend.v9.systems.woodies.stages.b11_t2_milestone import B11T2Milestone, B11Output
from backend.v9.systems.woodies.stages.b12_t3_milestone import B12T3Milestone, B12Output
from backend.v9.systems.woodies.stages.b14_hold import B14Hold, B14Output


# ── B4 POC Migration (Advisory) ──────────────────────────────────

class TestB4PocMigration:
    def test_long_below_poc_warns(self):
        result = B4PocMigrationQuery().evaluate(
            direction="LONG", current_price=7390, poc_location=7400,
        )
        assert result.suffering_flip_warning == "SUFFERING_FLIP"
        assert result.action == "TIGHTEN"  # NOT CLOSE_ALL (RULE 14)

    def test_short_above_poc_warns(self):
        result = B4PocMigrationQuery().evaluate(
            direction="SHORT", current_price=7410, poc_location=7400,
        )
        assert result.suffering_flip_warning == "SUFFERING_FLIP"
        assert result.action == "TIGHTEN"

    def test_long_above_poc_ok(self):
        result = B4PocMigrationQuery().evaluate(
            direction="LONG", current_price=7410, poc_location=7400,
        )
        assert result.suffering_flip_warning == "NONE"

    def test_ufl_bypasses_long(self):
        """LONG + price<POC + in UFL → bypass (no warning)."""
        result = B4PocMigrationQuery().evaluate(
            direction="LONG", current_price=7170, poc_location=7400,
            ufl_ufh={"ufl": 7172, "ufh": 7475},
        )
        assert result.suffering_flip_warning == "NONE"
        assert result.action == "HOLD"

    def test_ufh_bypasses_short(self):
        """SHORT + price>POC + in UFH → bypass (no warning)."""
        result = B4PocMigrationQuery().evaluate(
            direction="SHORT", current_price=7476, poc_location=7400,
            ufl_ufh={"ufl": 7172, "ufh": 7475},
        )
        assert result.suffering_flip_warning == "NONE"
        assert result.action == "HOLD"

    def test_long_below_poc_not_in_ufl_warns(self):
        """LONG + price<POC + NOT in UFL → SUFFERING_FLIP + TIGHTEN."""
        result = B4PocMigrationQuery().evaluate(
            direction="LONG", current_price=7300, poc_location=7400,
            ufl_ufh={"ufl": 7172, "ufh": 7475},
        )
        assert result.suffering_flip_warning == "SUFFERING_FLIP"
        assert result.action == "TIGHTEN"

    def test_short_above_poc_not_in_ufh_warns(self):
        """SHORT + price>POC + NOT in UFH → SUFFERING_FLIP + TIGHTEN."""
        result = B4PocMigrationQuery().evaluate(
            direction="SHORT", current_price=7410, poc_location=7400,
            ufl_ufh={"ufl": 7172, "ufh": 7475},
        )
        assert result.suffering_flip_warning == "SUFFERING_FLIP"
        assert result.action == "TIGHTEN"

    def test_degraded_mode(self):
        result = B4PocMigrationQuery().evaluate()
        assert result.action == "HOLD"

    def test_advisory_no_close_all(self):
        """RULE 14: B4 NEVER returns CLOSE_ALL."""
        result = B4PocMigrationQuery().evaluate(
            direction="LONG", current_price=7390, poc_location=7400,
        )
        assert result.action != "CLOSE_ALL"

    def test_priority_class(self):
        assert B4PocMigrationQuery().priority_class == "ADVISORY_EXIT"


# ── B5 OTF Mid-Trade (Advisory) ──────────────────────────────────

class TestB5OtfMidTrade:
    def test_unclear_warns(self):
        result = B5OtfMidTradeQuery().evaluate(otf_clarity="UNCLEAR")
        assert result.clarity_warning == "NO_CLARITY_MID_TRADE"
        assert result.action == "TIGHTEN"  # NOT CLOSE_ALL (RULE 14)

    def test_clear_ok(self):
        result = B5OtfMidTradeQuery().evaluate(otf_clarity="BOTH_CLEAR")
        assert result.clarity_warning == "NONE"
        assert result.action == "HOLD"

    def test_degraded_mode(self):
        result = B5OtfMidTradeQuery().evaluate(otf_clarity=None)
        assert result.action == "HOLD"

    def test_advisory_no_close_all(self):
        """RULE 14: B5 NEVER returns CLOSE_ALL."""
        result = B5OtfMidTradeQuery().evaluate(otf_clarity="UNCLEAR")
        assert result.action != "CLOSE_ALL"

    def test_priority_class(self):
        assert B5OtfMidTradeQuery().priority_class == "ADVISORY_EXIT"


# ── B9 Market State (Advisory) ───────────────────────────────────

class TestB9MarketState:
    def test_expanding_to_searching_warns(self):
        result = B9MarketStateQuery().evaluate(
            market_state="SEARCHING", prev_market_state="EXPANDING", t1_hit=True,
        )
        assert result.momentum_warning == "LOST"
        assert result.action == "PARTIAL_CLOSE"

    def test_transition_no_t1_holds(self):
        result = B9MarketStateQuery().evaluate(
            market_state="SEARCHING", prev_market_state="EXPANDING", t1_hit=False,
        )
        assert result.momentum_warning == "LOST"
        assert result.action == "HOLD"  # No partial if T1 not yet hit

    def test_no_transition_holds(self):
        result = B9MarketStateQuery().evaluate(
            market_state="EXPANDING", prev_market_state="EXPANDING",
        )
        assert result.momentum_warning == "NONE"

    def test_degraded_mode(self):
        result = B9MarketStateQuery().evaluate()
        assert result.action == "HOLD"

    def test_advisory_no_close_all(self):
        """RULE 14: B9 NEVER returns CLOSE_ALL."""
        result = B9MarketStateQuery().evaluate(
            market_state="SEARCHING", prev_market_state="EXPANDING", t1_hit=True,
        )
        assert result.action != "CLOSE_ALL"

    def test_priority_class(self):
        assert B9MarketStateQuery().priority_class == "PARTIAL"


# ── B10 T1 Milestone ─────────────────────────────────────────────

class TestB10T1:
    def test_long_t1_hit(self):
        result = B10T1Milestone().evaluate(
            current_price=7410, t1_price=7405, direction="LONG",
        )
        assert result.t1_hit is True
        assert result.action == "CLOSE_C1"

    def test_short_t1_hit(self):
        result = B10T1Milestone().evaluate(
            current_price=7390, t1_price=7395, direction="SHORT",
        )
        assert result.t1_hit is True
        assert result.action == "CLOSE_C1"

    def test_no_be_on_t1(self):
        """D-002: DO NOT move BE on T1 (stop-hunt zone)."""
        result = B10T1Milestone().evaluate(
            current_price=7410, t1_price=7405, direction="LONG",
        )
        assert result.be_moved is False  # Critical D-002 check

    def test_already_hit_skips(self):
        result = B10T1Milestone().evaluate(
            current_price=7410, t1_price=7405, direction="LONG",
            t1_already_hit=True,
        )
        assert result.t1_hit is False
        assert result.action == "HOLD"

    def test_priority_class(self):
        assert B10T1Milestone().priority_class == "TARGET"


# ── B11 T2 Milestone ─────────────────────────────────────────────

class TestB11T2:
    def test_reactive_closes_all(self):
        result = B11T2Milestone().evaluate(
            current_price=7420, t2_price=7415, direction="LONG",
            entry_classification="REACTIVE",
        )
        assert result.t2_hit is True
        assert result.action == "CLOSE_ALL"
        assert result.be_moved is False

    def test_initiative_closes_c2_smart_be(self):
        """D-055: Smart BE to entry on T2 for INITIATIVE."""
        result = B11T2Milestone().evaluate(
            current_price=7420, t2_price=7415, direction="LONG",
            entry_classification="INITIATIVE",
        )
        assert result.t2_hit is True
        assert result.action == "CLOSE_C2"
        assert result.be_moved is True  # D-055 Smart BE

    def test_already_hit_skips(self):
        result = B11T2Milestone().evaluate(
            current_price=7420, t2_price=7415, direction="LONG",
            t2_already_hit=True,
        )
        assert result.t2_hit is False

    def test_priority_class(self):
        assert B11T2Milestone().priority_class == "TARGET"


# ── B12 T3 Milestone ─────────────────────────────────────────────

class TestB12T3:
    def test_t3_hit(self):
        result = B12T3Milestone().evaluate(
            current_price=7440, t3_price=7435, direction="LONG",
        )
        assert result.t3_hit is True
        assert result.action == "CLOSE_C3"

    def test_no_hit(self):
        result = B12T3Milestone().evaluate(
            current_price=7430, t3_price=7435, direction="LONG",
        )
        assert result.t3_hit is False

    def test_priority_class(self):
        assert B12T3Milestone().priority_class == "TARGET"


# ── B14 Hold ──────────────────────────────────────────────────────

class TestB14Hold:
    def test_always_hold(self):
        result = B14Hold().evaluate()
        assert result.action == "HOLD"

    def test_priority_class(self):
        assert B14Hold().priority_class == "NO_ACTION"


# ── Cross-cutting: Degraded mode for all 3 TPs ───────────────────

class TestDegradedModeAll:
    def test_b4_degraded(self):
        assert B4PocMigrationQuery().evaluate().action == "HOLD"

    def test_b5_degraded(self):
        assert B5OtfMidTradeQuery().evaluate().action == "HOLD"

    def test_b9_degraded(self):
        assert B9MarketStateQuery().evaluate().action == "HOLD"
