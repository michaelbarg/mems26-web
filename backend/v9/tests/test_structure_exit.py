"""STRUCTURE_EXIT — exit on structural failure (Michael 30.08).

Tests for the three-grade exit system:
  Grade-A: failed break in position direction → tighten/flatten
  Grade-B: CEILING/FLOOR_FAILED → FLATTEN unconditionally
  Grade-C: grade-B + S1 reversal + structural break → FLATTEN + lock

Mutation tests: each grade's function returns None when the flag would be OFF
(the caller checks the flag, but the function itself is pure and must return
None on missing/wrong inputs).
"""
from backend.v9.services.trade_manager.structure_exit import (
    should_exit_on_failbreak,
    should_exit_on_double_top,
    should_exit_on_reversal,
)


# ── Grade-A: failed break exit ──────────────────────────────────────────────

class TestGradeA:
    """Exit on failed break in the direction of the open position."""

    def _fb_upper(self):
        """Upper failed break → SHORT entry signal."""
        return {
            "type": "FB_HIGH_VA",
            "direction": "SHORT",
            "entry": 7770.0,
            "stop": 7783.0,
            "poc": 7755.5,
            "target_poc": 7755.5,
            "failed_extreme": 7782.5,
        }

    def test_long_exits_on_upper_failed_break(self):
        """LONG position + upper failed break (SHORT) → exit signal."""
        result = should_exit_on_failbreak(
            trade_direction="LONG",
            trade_entry_price=7750.0,
            trade_stop=7735.0,
            trade_t1_hit=True,
            bar_high=7775.0,
            bar_low=7765.0,
            bar_close=7768.0,
            failed_break=self._fb_upper(),
            atr=10.0,
            initial_risk_pts=15.0,
        )
        assert result is not None
        assert result["action"] in ("modify_stop", "flatten")
        assert "grade-A" in result["reason"]

    def test_short_ignores_upper_failed_break(self):
        """SHORT position + upper failed break (SHORT) → no exit (same side)."""
        result = should_exit_on_failbreak(
            trade_direction="SHORT",
            trade_entry_price=7780.0,
            trade_stop=7795.0,
            trade_t1_hit=False,
            bar_high=7775.0,
            bar_low=7765.0,
            bar_close=7768.0,
            failed_break=self._fb_upper(),
            atr=10.0,
        )
        assert result is None, "SHORT should not exit on upper FB (we're WITH the direction)"

    def test_flatten_when_profit_sufficient(self):
        """Open profit ≥ 1.0R → FLATTEN."""
        result = should_exit_on_failbreak(
            trade_direction="LONG",
            trade_entry_price=7750.0,
            trade_stop=7740.0,  # risk = 10 pts
            trade_t1_hit=True,
            bar_high=7775.0,
            bar_low=7765.0,
            bar_close=7770.0,  # profit = 20 pts > 1.0R (10)
            failed_break=self._fb_upper(),
            atr=10.0,
        )
        assert result is not None
        assert result["action"] == "flatten"
        assert result["flatten"] is True

    def test_tighten_when_profit_insufficient(self):
        """Open profit < 1.0R → modify_stop only."""
        result = should_exit_on_failbreak(
            trade_direction="LONG",
            trade_entry_price=7765.0,
            trade_stop=7750.0,  # risk = 15 pts
            trade_t1_hit=True,
            bar_high=7775.0,
            bar_low=7765.0,
            bar_close=7768.0,  # profit = 3 pts < 1.0R (15)
            failed_break=self._fb_upper(),
            atr=20.0,
        )
        assert result is not None
        assert result["action"] == "modify_stop"
        assert result["flatten"] is False

    def test_no_trigger_returns_none(self):
        """No failed break → None."""
        result = should_exit_on_failbreak(
            trade_direction="LONG",
            trade_entry_price=7750.0,
            trade_stop=7740.0,
            trade_t1_hit=True,
            bar_high=7760.0,
            bar_low=7750.0,
            bar_close=7755.0,
            failed_break=None,
        )
        assert result is None

    def test_28_08_anchor_long_exits_on_vah_break(self):
        """28.08 replay: LONG @7776.25, failed break above VAH 7771.50.
        The system held to MAE_SCRATCH at 18:20 for $0. With grade-A,
        the failed break fires earlier and the stop tightens."""
        fb = {
            "type": "FB_HIGH_VA",
            "direction": "SHORT",
            "entry": 7770.0,
            "stop": 7783.0,
            "poc": 7755.5,
            "target_poc": 7755.5,
            "failed_extreme": 7780.0,
        }
        result = should_exit_on_failbreak(
            trade_direction="LONG",
            trade_entry_price=7776.25,
            trade_stop=7759.0,  # structural stop
            trade_t1_hit=False,
            bar_high=7780.0,
            bar_low=7768.0,
            bar_close=7770.0,
            failed_break=fb,
            atr=8.5,
        )
        assert result is not None, "Grade-A should fire on the 28.08 scenario"
        # The stop should tighten to below bar_low
        assert result["new_stop"] < 7768.0


# ── Grade-B: double top/bottom exit ────────────────────────────────────────

class TestGradeB:
    """CEILING/FLOOR_FAILED → FLATTEN unconditionally."""

    def test_long_exits_on_ceiling_failed(self):
        result = should_exit_on_double_top(
            trade_direction="LONG",
            ceiling_floor_state={"state": "CEILING_FAILED", "p1": 7780.0, "p2": 7779.5},
            grade_a_fired=False,
        )
        assert result is not None
        assert result["action"] == "flatten"

    def test_short_ignores_ceiling_failed(self):
        result = should_exit_on_double_top(
            trade_direction="SHORT",
            ceiling_floor_state={"state": "CEILING_FAILED", "p1": 7780.0, "p2": 7779.5},
            grade_a_fired=False,
        )
        assert result is None

    def test_skipped_when_grade_a_fired(self):
        result = should_exit_on_double_top(
            trade_direction="LONG",
            ceiling_floor_state={"state": "CEILING_FAILED"},
            grade_a_fired=True,
        )
        assert result is None, "Grade-B should not fire if grade-A already handled it"

    def test_short_exits_on_floor_failed(self):
        result = should_exit_on_double_top(
            trade_direction="SHORT",
            ceiling_floor_state={"state": "FLOOR_FAILED", "p1": 7720.0, "p2": 7721.0},
            grade_a_fired=False,
        )
        assert result is not None
        assert result["action"] == "flatten"


# ── Grade-C: reversal exit ──────────────────────────────────────────────────

class TestGradeC:
    """Grade-B + S1 reversal + structural break → FLATTEN + lock."""

    def test_all_conditions_met(self):
        result = should_exit_on_reversal(
            trade_direction="LONG",
            ceiling_floor_state={"state": "CEILING_FAILED"},
            s1_direction="DOWN",
            lower_high_broken=True,
        )
        assert result is not None
        assert result["action"] == "flatten_and_lock"
        assert result["lock_edge"] is True

    def test_missing_s1_direction(self):
        result = should_exit_on_reversal(
            trade_direction="LONG",
            ceiling_floor_state={"state": "CEILING_FAILED"},
            s1_direction=None,
            lower_high_broken=True,
        )
        assert result is None, "Both conditions required — missing S1 → None"

    def test_no_structural_break(self):
        result = should_exit_on_reversal(
            trade_direction="LONG",
            ceiling_floor_state={"state": "CEILING_FAILED"},
            s1_direction="DOWN",
            lower_high_broken=False,
        )
        assert result is None, "Both conditions required — no lower-high break → None"

    def test_s1_same_direction_no_exit(self):
        result = should_exit_on_reversal(
            trade_direction="LONG",
            ceiling_floor_state={"state": "CEILING_FAILED"},
            s1_direction="UP",  # same direction → no reversal
            lower_high_broken=True,
        )
        assert result is None
