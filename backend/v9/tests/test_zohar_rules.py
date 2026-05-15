"""ZoharRulesEngine tests — 6 scenarios per rule evaluation method."""

from datetime import time

from backend.v9.systems.day_type.zohar_rules import (
    ZoharRulesEngine, RuleVerdict,
)
from backend.v9.systems.day_type.schemas import DayType


engine = ZoharRulesEngine()


def test_alpha_invalidates_trend_dd_inside_ib():
    """Alpha: TREND_DD with price inside IB → INVALIDATE."""
    result = engine.evaluate_alpha(
        current_type=DayType.Trend_DD,
        price=7500.0,
        ib_high=7510.0,
        ib_low=7490.0,
    )
    assert result == RuleVerdict.INVALIDATE


def test_beta_invalidates_failed_open_drive():
    """Beta: Open Drive UP but price below open → INVALIDATE."""
    result = engine.evaluate_beta(
        opening_is_drive=True,
        drive_direction_up=True,
        current_price=7495.0,
        open_price=7500.0,
    )
    assert result == RuleVerdict.INVALIDATE


def test_gamma_invalidates_failed_test_drive():
    """Gamma: Test Drive reversal did not hold → INVALIDATE."""
    result = engine.evaluate_gamma(
        opening_is_test_drive=True,
        reversal_held=False,
    )
    assert result == RuleVerdict.INVALIDATE


def test_delta_both_side_extension_downgrades():
    """Delta: extensions both UP and DOWN → DOWNGRADE (Neutral)."""
    result = engine.evaluate_delta(extensions_up=2, extensions_down=1)
    assert result == RuleVerdict.DOWNGRADE


def test_width_exceeds_max_letters_downgrades():
    """Width: TPO row > 5 letters → DOWNGRADE (Normal day)."""
    result = engine.evaluate_width(max_tpo_count=7)
    assert result == RuleVerdict.DOWNGRADE
    # At or below threshold → no opinion
    result2 = engine.evaluate_width(max_tpo_count=5)
    assert result2 == RuleVerdict.NO_OPINION


def test_timing_bias_variation_before_midday():
    """Timing: reversal before 12:30 → Variation; trend after → Trend_DD."""
    # Reversal at 11:00 → Variation
    suggestion = engine.evaluate_timing_bias(
        current_time=time(11, 0),
        has_reversal=True,
        has_trend_continuation=False,
    )
    assert suggestion == DayType.Variation

    # Trend continuation at 13:00 → Trend_DD
    suggestion2 = engine.evaluate_timing_bias(
        current_time=time(13, 0),
        has_reversal=False,
        has_trend_continuation=True,
    )
    assert suggestion2 == DayType.Trend_DD
