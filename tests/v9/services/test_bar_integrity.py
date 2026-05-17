"""Pure-function tests for bar_integrity.bar_is_valid() — no DB required."""

import pytest
from backend.v9.services.bar_integrity import bar_is_valid


class TestBarIsValid:
    """Mirror of frontend looksOk() heuristic."""

    def test_normal_bar_passes(self):
        ok, reason = bar_is_valid(open=7450.0, high=7460.0, low=7445.0, close=7455.0)
        assert ok is True
        assert reason is None

    def test_null_ohlc_rejected(self):
        ok, reason = bar_is_valid(open=None, high=7460.0, low=7445.0, close=7455.0)
        assert ok is False
        assert reason == "null_ohlc"

    def test_zero_price_rejected(self):
        ok, reason = bar_is_valid(open=0, high=7460.0, low=7445.0, close=7455.0)
        assert ok is False
        assert reason == "non_positive_ohlc"

    def test_negative_price_rejected(self):
        ok, reason = bar_is_valid(open=-1.0, high=7460.0, low=7445.0, close=7455.0)
        assert ok is False
        assert reason == "non_positive_ohlc"

    def test_low_gt_high_rejected(self):
        ok, reason = bar_is_valid(open=7450.0, high=7440.0, low=7460.0, close=7455.0)
        assert ok is False
        assert reason == "low_gt_high"

    def test_low_wick_body_cliff_rejected(self):
        """The known bad-bar trio: low=7172.5 with body around 7430-7461."""
        ok, reason = bar_is_valid(open=7430.75, high=7463.0, low=7172.5, close=7461.0)
        assert ok is False
        assert reason == "low_wick_exceeds_2pct"

    def test_high_wick_body_cliff_rejected(self):
        """High wick > 2% of body top."""
        ok, reason = bar_is_valid(open=7200.0, high=7500.0, low=7195.0, close=7210.0)
        assert ok is False
        assert reason == "high_wick_exceeds_2pct"

    def test_bad_bar_id_1197(self):
        """id=1197: O=7462.25 H=7463 L=7180.25 C=7180.25 — huge body, tiny wicks.
        The server validator catches this via the explicit bar-range check.
        """
        ok, reason = bar_is_valid(open=7462.25, high=7463.0, low=7180.25, close=7180.25)
        assert ok is False
        assert reason == "bar_range_exceeds_2pct"

    def test_bad_bar_id_1207(self):
        """Exact reproduction of id=1207."""
        ok, reason = bar_is_valid(open=7430.75, high=7463.0, low=7172.5, close=7461.0)
        assert ok is False
        assert reason == "low_wick_exceeds_2pct"

    def test_bad_bar_id_1208(self):
        """id=1208: O=7264.75 H=7462.75 L=7172.5 C=7460.0 — wide body, small wick.
        body=min(7264.75,7460)=7264.75; (7264.75-7172.5)/7264.75=0.0127 < 0.02.
        The server validator catches this via the explicit bar-range check.
        """
        ok, reason = bar_is_valid(open=7264.75, high=7462.75, low=7172.5, close=7460.0)
        assert ok is False
        assert reason == "bar_range_exceeds_2pct"

    def test_tight_bar_passes(self):
        """A bar with very small wicks (within 2% tolerance) passes."""
        # body = min(7450, 7455) = 7450; low = 7440; (7450-7440)/7450 = 0.00134 < 0.02
        ok, reason = bar_is_valid(open=7450.0, high=7460.0, low=7440.0, close=7455.0)
        assert ok is True

    def test_exactly_at_2pct_boundary_rejected(self):
        """A bar at exactly the 2% boundary is rejected (> 0.02, not >=)."""
        # body = 100.0; low must cause (100 - low)/100 > 0.02 => low < 98
        # At low=97.99: (100-97.99)/100 = 0.0201 > 0.02 => rejected
        ok, reason = bar_is_valid(open=100.0, high=102.0, low=97.99, close=101.0)
        assert ok is False
        assert reason == "low_wick_exceeds_2pct"

    def test_just_under_2pct_boundary_passes(self):
        """A bar just under the 2% boundary passes."""
        # body = 100.0; low=98.01: (100-98.01)/100 = 0.0199 < 0.02 => passes
        ok, reason = bar_is_valid(open=100.0, high=102.0, low=98.01, close=101.0)
        assert ok is True
