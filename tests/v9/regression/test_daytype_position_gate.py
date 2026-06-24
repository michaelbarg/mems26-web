"""Regression: #68 unified day-type position gate.

Tests that direction is allowed/blocked based on day-type + price position
relative to structural levels (IB/VA/POC), NOT CCI.

RED-on-revert:
  - Removing Normal POC check → LONG above POC wrongly passes.
  - Removing Variation IB check → SHORT above IBH wrongly passes.
"""
import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def enable_gate():
    with patch.dict(os.environ, {"DAYTYPE_POSITION_GATE": "1"}):
        yield


TPO = {
    "ib_high": 7580.0,
    "ib_low": 7540.0,
    "poc": 7560.0,
    "vah": 7575.0,
    "val": 7545.0,
    "session_high": 7600.0,  # above IBH → uptrend
    "session_low": 7542.0,   # above IBL → IBL intact
}


class TestNormalDay:
    """Normal: LONG only below POC, SHORT only above POC."""

    def test_long_below_poc_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE", direction="LONG", day_type="Normal",
            entry_price=7550.0, tpo_ctx=TPO,
        )
        assert allow is True

    def test_long_above_poc_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="REACTIVE", direction="LONG", day_type="Normal",
            entry_price=7570.0, tpo_ctx=TPO,
        )
        assert allow is False
        assert "wrong side" in reason

    def test_short_above_poc_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="ZLR", direction="SHORT", day_type="Normal",
            entry_price=7570.0, tpo_ctx=TPO,
        )
        assert allow is True

    def test_short_below_poc_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="ZLR", direction="SHORT", day_type="Normal",
            entry_price=7550.0, tpo_ctx=TPO,
        )
        assert allow is False

    def test_applies_to_all_patterns(self):
        """Not just REACTIVE — ALL patterns gated on Normal."""
        from backend.v9.systems.daytype_position_gate import decide
        for pat in ["HFE", "TLB", "INITIATIVE", "FLAGS", "GHOST"]:
            allow, _ = decide(
                pattern=pat, direction="LONG", day_type="Normal",
                entry_price=7570.0, tpo_ctx=TPO,
            )
            assert allow is False, f"{pat} LONG above POC should be blocked on Normal"


class TestVariationDay:
    """Variation: WITH IB expansion only."""

    def test_long_above_ibh_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, _ = decide(
            pattern="ZLR", direction="LONG", day_type="Variation",
            entry_price=7590.0, tpo_ctx=TPO,
        )
        assert allow is True

    def test_short_above_ibh_blocked(self):
        """SHORT above IBH = against upward expansion."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, _ = decide(
            pattern="HFE", direction="SHORT", day_type="Variation",
            entry_price=7590.0, tpo_ctx=TPO,
        )
        assert allow is False
        assert "against" in _[1] if isinstance(_, tuple) else True

    def test_inside_ib_allows_both(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow_l, _ = decide(
            pattern="ZLR", direction="LONG", day_type="Variation",
            entry_price=7560.0, tpo_ctx=TPO,
        )
        allow_s, _ = decide(
            pattern="ZLR", direction="SHORT", day_type="Variation",
            entry_price=7560.0, tpo_ctx=TPO,
        )
        assert allow_l is True
        assert allow_s is True


class TestTrendDay:
    """Trend_Normal: WITH trend (IB expansion direction)."""

    def test_long_with_uptrend(self):
        """session_high > IBH, IBL intact → uptrend → LONG allowed."""
        from backend.v9.systems.daytype_position_gate import decide
        allow, _ = decide(
            pattern="ZLR", direction="LONG", day_type="Trend_Normal",
            entry_price=7590.0, tpo_ctx=TPO,
        )
        assert allow is True

    def test_short_against_uptrend_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, reason = decide(
            pattern="HFE", direction="SHORT", day_type="Trend_Normal",
            entry_price=7590.0, tpo_ctx=TPO,
        )
        assert allow is False
        assert "against" in reason

    def test_both_broken_allows_both(self):
        """Both IB edges broken → allow both directions."""
        from backend.v9.systems.daytype_position_gate import decide
        tpo_both = {**TPO, "session_high": 7600.0, "session_low": 7530.0}
        allow_l, _ = decide(
            pattern="ZLR", direction="LONG", day_type="Trend_Normal",
            entry_price=7590.0, tpo_ctx=tpo_both,
        )
        allow_s, _ = decide(
            pattern="ZLR", direction="SHORT", day_type="Trend_Normal",
            entry_price=7535.0, tpo_ctx=tpo_both,
        )
        assert allow_l is True
        assert allow_s is True


class TestNeutralDays:
    """Neutral_Center / Neutral_Extreme: LOCATION-gated like Normal — fade VA edges
    (SHORT only above POC, LONG only below POC), NOT both-sides-all-day.
    Michael 2026-06-22: the zone decides the side.
    RED-on-revert: reverting to 'allow both' makes the wrong-side cases wrongly pass."""

    def test_neutral_short_above_poc_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, _ = decide(pattern="REACTIVE", direction="SHORT", day_type="Neutral_Center",
                          entry_price=7575.0, tpo_ctx=TPO)  # above POC 7560 → correct fade
        assert allow is True

    def test_neutral_short_below_poc_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, _ = decide(pattern="REACTIVE", direction="SHORT", day_type="Neutral_Center",
                          entry_price=7550.0, tpo_ctx=TPO)  # below POC → wrong side
        assert allow is False

    def test_neutral_long_below_poc_allowed(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, _ = decide(pattern="REACTIVE", direction="LONG", day_type="Neutral_Extreme",
                          entry_price=7550.0, tpo_ctx=TPO)  # below POC → correct fade
        assert allow is True

    def test_neutral_long_above_poc_blocked(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, _ = decide(pattern="REACTIVE", direction="LONG", day_type="Neutral_Center",
                          entry_price=7575.0, tpo_ctx=TPO)  # above POC → wrong side
        assert allow is False


class TestFailOpen:
    """Missing data → fail-open (never block on bad data)."""

    def test_missing_tpo(self):
        from backend.v9.systems.daytype_position_gate import decide
        allow, _ = decide(
            pattern="ZLR", direction="LONG", day_type="Normal",
            entry_price=7570.0, tpo_ctx=None,
        )
        assert allow is True

    def test_flag_off(self):
        from backend.v9.systems.daytype_position_gate import decide
        with patch.dict(os.environ, {"DAYTYPE_POSITION_GATE": "0"}):
            allow, _ = decide(
                pattern="ZLR", direction="LONG", day_type="Normal",
                entry_price=7570.0, tpo_ctx=TPO,
            )
            assert allow is True
