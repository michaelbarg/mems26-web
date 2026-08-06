"""Tests for balance_imbalance_toggle — unified regime assessment."""

import pytest
from backend.v9.systems.balance_imbalance_toggle import assess_regime


class TestRegimeAssessment:
    def test_trend_with_leg_is_imbalance(self):
        """Trend day + active leg → IMBALANCE."""
        state = assess_regime(day_type="Trend_Normal", leg="UP")
        assert state.regime == "IMBALANCE"
        assert state.confidence >= 0.5

    def test_balance_no_leg_is_balance(self):
        """Balance day + no leg + high overlap → BALANCE."""
        state = assess_regime(day_type="Balance", leg=None, va_overlap_pct=75)
        assert state.regime == "BALANCE"

    def test_mixed_signals_transitional(self):
        """Trend day but no leg and high overlap → TRANSITIONAL."""
        state = assess_regime(day_type="Trend_Normal", leg=None, va_overlap_pct=80)
        assert state.regime == "TRANSITIONAL"

    def test_all_missing_transitional(self):
        """No data at all → TRANSITIONAL (Rule-1)."""
        state = assess_regime()
        assert state.regime == "TRANSITIONAL"
        assert state.confidence <= 0.4

    def test_drive_boosts_imbalance(self):
        """OPEN_DRIVE adds an imbalance vote."""
        state = assess_regime(
            day_type="Variation", leg="DOWN", opening_type="OPEN_DRIVE"
        )
        assert state.regime == "IMBALANCE"
        assert state.confidence >= 0.65  # 3 imbalance votes

    def test_neutral_high_overlap_is_balance(self):
        """Neutral + high VA overlap → BALANCE."""
        state = assess_regime(
            day_type="Neutral_Center", va_overlap_pct=70
        )
        assert state.regime == "BALANCE"

    def test_low_overlap_pushes_imbalance(self):
        """Low VA overlap (<30%) signals imbalance."""
        state = assess_regime(
            day_type="Trend_Normal", leg="UP", va_overlap_pct=20
        )
        assert state.regime == "IMBALANCE"
        assert state.confidence >= 0.65

    def test_confidence_increases_with_agreement(self):
        """More agreeing signals → higher confidence."""
        weak = assess_regime(day_type="Trend_Normal")
        strong = assess_regime(day_type="Trend_Normal", leg="UP",
                                va_overlap_pct=15, opening_type="OPEN_DRIVE")
        assert strong.confidence > weak.confidence

    def test_detail_contains_signals(self):
        """Detail string shows all signal contributions."""
        state = assess_regime(day_type="Balance", leg="UP", va_overlap_pct=50)
        assert "day_type=" in state.detail
        assert "leg=" in state.detail
        assert "overlap=" in state.detail
