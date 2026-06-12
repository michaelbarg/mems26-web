"""Regression — Pkg 5a/5c day-type gate + S2_CHART_ALL_DAYTYPES flag (2026-06-12).

Anti-tautological: calls the REAL chart_patterns_allowed() used by process_bar.
RED-on-revert: removing the flag branch or changing the default lists fails these.
"""
import os
import pytest

from backend.v9.systems.five_min.five_min_system import chart_patterns_allowed


@pytest.fixture(autouse=True)
def _clean_flag(monkeypatch):
    monkeypatch.delenv("S2_CHART_ALL_DAYTYPES", raising=False)


class TestFlagOff:
    """Default = pre-2026-06-12 behavior exactly (anti-regression)."""

    def test_5a_trend_normal_blocked(self):
        assert chart_patterns_allowed("Trend_Normal", "5a") is False

    def test_5a_variation_allowed(self):
        assert chart_patterns_allowed("Variation", "5a") is True

    def test_5c_trend_normal_allowed(self):
        assert chart_patterns_allowed("Trend_Normal", "5c") is True

    def test_5c_neutral_center_blocked(self):
        assert chart_patterns_allowed("Neutral_Center", "5c") is False


class TestFlagOn:
    def test_5a_trend_normal_opens(self, monkeypatch):
        monkeypatch.setenv("S2_CHART_ALL_DAYTYPES", "1")
        assert chart_patterns_allowed("Trend_Normal", "5a") is True

    def test_5c_neutral_center_opens(self, monkeypatch):
        monkeypatch.setenv("S2_CHART_ALL_DAYTYPES", "1")
        assert chart_patterns_allowed("Neutral_Center", "5c") is True

    def test_nontrend_never_opens(self, monkeypatch):
        monkeypatch.setenv("S2_CHART_ALL_DAYTYPES", "1")
        assert chart_patterns_allowed("Nontrend", "5a") is False
        assert chart_patterns_allowed("Nontrend", "5c") is False

    def test_unknown_never_opens(self, monkeypatch):
        monkeypatch.setenv("S2_CHART_ALL_DAYTYPES", "1")
        assert chart_patterns_allowed("UNKNOWN", "5a") is False
        assert chart_patterns_allowed(None, "5c") is False
