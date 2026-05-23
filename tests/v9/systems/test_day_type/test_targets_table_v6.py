"""Tests for targets_table.py — EXIT_V6 + D-091.Q1 (Pkg 3a Stream 1)."""
import logging
import pytest
from backend.v9.systems.day_type.targets_table import get_targets
import backend.v9.systems.day_type.targets_table as _mod


class TestTargetsTableV6:
    """Verify all 7 day types + legacy alias + unknown."""

    def setup_method(self):
        _mod._neutral_deprecation_logged = False

    def test_trend_normal(self):
        t = get_targets("Trend_Normal")
        assert t is not None
        assert t["time_stop_minutes"] is None
        assert t["t1_r"] == 1.0
        assert t["t3_r"] == 4.0
        assert t["trail_after_t2"] is True
        assert t["no_trade"] is False

    def test_trend_dd(self):
        t = get_targets("Trend_DD")
        assert t is not None
        assert t["time_stop_minutes"] == 90
        assert t["t1_r"] == 1.0
        assert t["no_trade"] is False

    def test_variation(self):
        t = get_targets("Variation")
        assert t is not None
        assert t["time_stop_minutes"] == 60
        assert t["t2_r"] == 2.5
        assert t["no_trade"] is False

    def test_normal(self):
        t = get_targets("Normal")
        assert t is not None
        assert t["time_stop_minutes"] == 30
        assert t["t2"] == "POC"
        assert t["t3"] is None
        assert t["no_trade"] is False

    def test_neutral_extreme(self):
        t = get_targets("Neutral_Extreme")
        assert t is not None
        assert t["time_stop_minutes"] == 45
        assert t["t2"] == "extreme"
        assert t["no_trade"] is False

    def test_neutral_center(self):
        t = get_targets("Neutral_Center")
        assert t is not None
        assert t["time_stop_minutes"] == 30
        assert t["t2"] == "extreme"
        assert t["no_trade"] is False

    def test_nontrend(self):
        t = get_targets("Nontrend")
        assert t is not None
        assert t["no_trade"] is True
        assert t["contracts"] == 0
        assert t["time_stop_minutes"] is None

    def test_legacy_neutral_maps_to_neuc(self, caplog):
        """Legacy 'Neutral' → NeuC config + 1 deprecation warning."""
        with caplog.at_level(logging.WARNING):
            t = get_targets("Neutral")
        assert t is not None
        assert t["time_stop_minutes"] == 30
        assert any("DEPRECATED" in rec.message for rec in caplog.records)

    def test_unknown_returns_none(self):
        """Unknown day type → None (not silent default)."""
        t = get_targets("Banana")
        assert t is None
