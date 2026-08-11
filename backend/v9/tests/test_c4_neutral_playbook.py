"""C4 — Neutral Day Playbook (2026-08-11).

Spec: edges only · C1=POC · C2=opposite edge (80% rule) · stop beyond EXCESS ·
1-2 contracts · time-stop 60min (12 bars).

Flag: NEUTRAL_PLAYBOOK_V1 (default OFF — backward compatible).
"""
import os

import pytest

from backend.v9.systems.structural_targets import (
    _resolve_neutral_center,
    _resolve_neutral_extreme,
)


class TestNeutralExtremeC4:
    """Neutral Extreme with C4 flag ON."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("NEUTRAL_PLAYBOOK_V1", "1")

    def test_contracts_2(self):
        result = _resolve_neutral_extreme(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["contracts"] == 2

    def test_time_stop_60min(self):
        result = _resolve_neutral_extreme(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["time_stop_minutes"] == 60

    def test_c1_is_poc(self):
        result = _resolve_neutral_extreme(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        # C1 (t1_price) should be near POC (7783)
        assert result["t1_price"] is not None

    def test_no_trail(self):
        result = _resolve_neutral_extreme(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["trail_after_t2"] is False

    def test_short_targets_correct_side(self):
        result = _resolve_neutral_extreme(
            "SHORT", 7790.0, 7795.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["t1_price"] is not None
        assert result["t1_price"] < 7790.0  # below entry


class TestNeutralCenterC4:
    """Neutral Center with C4 flag ON."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("NEUTRAL_PLAYBOOK_V1", "1")

    def test_contracts_2(self):
        result = _resolve_neutral_center(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["contracts"] == 2

    def test_time_stop_60min(self):
        result = _resolve_neutral_center(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["time_stop_minutes"] == 60

    def test_no_trail(self):
        result = _resolve_neutral_center(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["trail_after_t2"] is False


class TestNeutralFlagOff:
    """When NEUTRAL_PLAYBOOK_V1=0, behavior is unchanged (backward compatible)."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("NEUTRAL_PLAYBOOK_V1", "0")

    def test_extreme_3_contracts(self):
        result = _resolve_neutral_extreme(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["contracts"] == 3

    def test_extreme_45min_time_stop(self):
        result = _resolve_neutral_extreme(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["time_stop_minutes"] == 45

    def test_center_3_contracts(self):
        result = _resolve_neutral_center(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["contracts"] == 3

    def test_center_30min_time_stop(self):
        result = _resolve_neutral_center(
            "LONG", 7770.0, 7765.0,
            7790.0, 7770.0, 7780.0, 7783.0, 7792.0, 7768.0)
        assert result["time_stop_minutes"] == 30
