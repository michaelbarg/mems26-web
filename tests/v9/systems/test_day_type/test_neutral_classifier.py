"""Tests for neutral_classifier.py — NeuE/NeuC per D-091.Q1 (Pkg 3a Stream 1)."""
import logging
import pytest
from backend.v9.systems.day_type.neutral_classifier import (
    classify_neutral_subtype,
    _fallback_logged_for_date,
)
from backend.v9.systems.day_type.schemas import DayType
import backend.v9.systems.day_type.neutral_classifier as _mod


class TestNeuEClassification:
    """NeuE = open at or outside VA edge (within ±1 tick tolerance)."""

    def test_open_at_vah_exact(self):
        r = classify_neutral_subtype(session_open_price=4500, prev_vah=4500, prev_val=4480)
        assert r == DayType.Neutral_Extreme

    def test_open_at_val_exact(self):
        r = classify_neutral_subtype(session_open_price=4480, prev_vah=4500, prev_val=4480)
        assert r == DayType.Neutral_Extreme

    def test_open_above_vah(self):
        r = classify_neutral_subtype(session_open_price=4505, prev_vah=4500, prev_val=4480)
        assert r == DayType.Neutral_Extreme

    def test_open_below_val(self):
        r = classify_neutral_subtype(session_open_price=4475, prev_vah=4500, prev_val=4480)
        assert r == DayType.Neutral_Extreme

    def test_open_within_tolerance_below_vah(self):
        """4499.75 is within 0.25pt (1 tick) of VAH 4500 → NeuE."""
        r = classify_neutral_subtype(session_open_price=4499.75, prev_vah=4500, prev_val=4480)
        assert r == DayType.Neutral_Extreme

    def test_open_within_tolerance_above_val(self):
        """4480.25 is within 0.25pt (1 tick) of VAL 4480 → NeuE."""
        r = classify_neutral_subtype(session_open_price=4480.25, prev_vah=4500, prev_val=4480)
        assert r == DayType.Neutral_Extreme


class TestNeuCClassification:
    """NeuC = open strictly inside VA, closer to POC."""

    def test_open_strictly_inside_va(self):
        r = classify_neutral_subtype(session_open_price=4490, prev_vah=4500, prev_val=4480)
        assert r == DayType.Neutral_Center

    def test_open_near_poc_assume_inside(self):
        r = classify_neutral_subtype(session_open_price=4490, prev_vah=4500, prev_val=4480)
        assert r == DayType.Neutral_Center


class TestFallbacks:
    """Fallback to NeuC when data missing + rate-limited logging."""

    def setup_method(self):
        # Reset module-level rate limiter before each test
        _mod._fallback_logged_for_date = None

    def test_fallback_session_open_missing(self, caplog):
        with caplog.at_level(logging.INFO):
            r = classify_neutral_subtype(session_open_price=None, prev_vah=4500, prev_val=4480,
                                         session_date="test-open-missing")
        assert r == DayType.Neutral_Center
        assert any("session_open" in rec.message for rec in caplog.records)

    def test_fallback_vah_missing(self, caplog):
        with caplog.at_level(logging.INFO):
            r = classify_neutral_subtype(session_open_price=4490, prev_vah=None, prev_val=4480,
                                         session_date="test-vah-missing")
        assert r == DayType.Neutral_Center
        assert any("prev_vah" in rec.message for rec in caplog.records)

    def test_fallback_val_missing(self, caplog):
        with caplog.at_level(logging.INFO):
            r = classify_neutral_subtype(session_open_price=4490, prev_vah=4500, prev_val=None,
                                         session_date="test-val-missing")
        assert r == DayType.Neutral_Center
        assert any("prev_val" in rec.message for rec in caplog.records)

    def test_fallback_all_missing(self, caplog):
        with caplog.at_level(logging.INFO):
            r = classify_neutral_subtype(session_open_price=None, prev_vah=None, prev_val=None,
                                         session_date="test-all-missing")
        assert r == DayType.Neutral_Center
        assert len([rec for rec in caplog.records if "fallback" in rec.message]) >= 1

    def test_fallback_rate_limited_per_session(self, caplog):
        """Two calls same date → exactly 1 log."""
        with caplog.at_level(logging.INFO):
            r1 = classify_neutral_subtype(session_open_price=None, prev_vah=None, prev_val=4480,
                                          session_date="2026-05-23")
            r2 = classify_neutral_subtype(session_open_price=None, prev_vah=None, prev_val=4480,
                                          session_date="2026-05-23")
        assert r1 == DayType.Neutral_Center
        assert r2 == DayType.Neutral_Center
        fallback_logs = [rec for rec in caplog.records if "fallback" in rec.message]
        assert len(fallback_logs) == 1

    def test_fallback_logged_again_new_session(self, caplog):
        """Different dates → 2 logs."""
        with caplog.at_level(logging.INFO):
            classify_neutral_subtype(session_open_price=None, prev_vah=None, prev_val=4480,
                                     session_date="2026-05-23")
            classify_neutral_subtype(session_open_price=None, prev_vah=None, prev_val=4480,
                                     session_date="2026-05-24")
        fallback_logs = [rec for rec in caplog.records if "fallback" in rec.message]
        assert len(fallback_logs) == 2

    def test_degenerate_va(self, caplog):
        """VAH == VAL (zero-width VA) → NeuC + log."""
        with caplog.at_level(logging.INFO):
            r = classify_neutral_subtype(session_open_price=4490, prev_vah=4490, prev_val=4490,
                                         session_date="test-degenerate")
        assert r == DayType.Neutral_Center
        assert any("degenerate_va" in rec.message for rec in caplog.records)
