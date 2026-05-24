"""Tests for atr_caps module (Pkg 3b-1 · D-094)."""
import pytest
from types import SimpleNamespace
from backend.v9.systems.five_min.atr_caps import (
    ATR_MULTIPLIERS,
    TRAIL_OVERRIDE_BY_PATTERN,
    PATTERN_TIME_STOPS,
    _pattern_to_family,
    compute_time_stop_minutes,
    compute_continuous_atr14,
)


class TestATRMultipliers:
    def test_atr_multipliers_has_legacy_keys(self):
        assert ATR_MULTIPLIERS["Reactive"] == 1.0
        assert ATR_MULTIPLIERS["OFA"] == 1.5
        assert ATR_MULTIPLIERS["Flag"] == 1.5
        assert ATR_MULTIPLIERS["Double_BT"] == 2.0
        assert ATR_MULTIPLIERS["HnS"] == 2.0

    def test_atr_multipliers_has_xlsx_keys(self):
        assert ATR_MULTIPLIERS["OFA_Reactive"] == 1.5
        assert ATR_MULTIPLIERS["OFA_Initiative"] == 2.0
        assert ATR_MULTIPLIERS["Pennant"] == 1.5
        assert ATR_MULTIPLIERS["Wedge"] == 2.0
        assert ATR_MULTIPLIERS["Triangle"] == 2.0


class TestPatternToFamily:
    def test_pattern_to_family_reactive_lowercase(self):
        assert _pattern_to_family("reactive") == "OFA_Reactive"

    def test_pattern_to_family_reactive_uppercase(self):
        assert _pattern_to_family("REACTIVE") == "OFA_Reactive"

    def test_pattern_to_family_initiative_lowercase(self):
        assert _pattern_to_family("initiative") == "OFA_Initiative"

    def test_pattern_to_family_initiative_uppercase(self):
        assert _pattern_to_family("INITIATIVE") == "OFA_Initiative"

    def test_pattern_to_family_unknown_returns_none(self):
        assert _pattern_to_family("BANANA") is None

    def test_pattern_to_family_legacy_kind_REACTIVE(self):
        assert _pattern_to_family("REACTIVE") == "OFA_Reactive"

    def test_pattern_to_family_legacy_kind_INITIATIVE(self):
        assert _pattern_to_family("INITIATIVE") == "OFA_Initiative"


class TestTrailOverride:
    def test_trail_override_ofa_init_tdd_returns_6r_trail(self):
        entry = TRAIL_OVERRIDE_BY_PATTERN[("Trend_DD", "OFA_Initiative")]
        assert entry["t3"] == "6R+trail"
        assert entry["trail_after_t2"] is True

    def test_trail_override_other_combos_return_none(self):
        assert TRAIL_OVERRIDE_BY_PATTERN.get(("Variation", "OFA_Initiative")) is None


class TestComputeTimeStop:
    def test_compute_time_stop_min_of_both(self):
        targets = {"TestDay": {"time_stop_minutes": 60}}
        r = compute_time_stop_minutes("TestDay", "OFA_Reactive", targets_table=targets)
        assert r == 30  # min(60, 30)

    def test_compute_time_stop_day_only_when_pattern_none(self):
        targets = {"TestDay": {"time_stop_minutes": 60}}
        r = compute_time_stop_minutes("TestDay", None, targets_table=targets)
        assert r == 60

    def test_compute_time_stop_pattern_only_when_day_none(self):
        targets = {}
        r = compute_time_stop_minutes("Unknown", "OFA_Initiative", targets_table=targets)
        assert r == 20

    def test_compute_time_stop_both_none_returns_none(self):
        targets = {"TestDay": {"time_stop_minutes": None}}
        r = compute_time_stop_minutes("TestDay", "BANANA", targets_table=targets)
        assert r is None


def _bar(h, l, c):
    return SimpleNamespace(high=h, low=l, close=c)


class TestContinuousATR14:
    def test_continuous_atr14_basic_14_bars(self):
        bars = [_bar(101, 100, 100.5)] * 14
        result = compute_continuous_atr14(bars, [])
        assert result is not None
        assert isinstance(result, float)
        assert result == pytest.approx(1.0, abs=0.01)

    def test_continuous_atr14_yesterday_only_at_session_open(self):
        bars = [_bar(101, 100, 100.5)] * 14
        result = compute_continuous_atr14(bars, [])
        assert result is not None

    def test_continuous_atr14_includes_overnight_gap(self):
        yesterday = [_bar(101, 100, 100.5)] * 13 + [_bar(4501, 4500, 4500)]
        today = [_bar(4520, 4515, 4518)]
        result = compute_continuous_atr14(yesterday, today)
        assert result is not None
        # TR for today bar = max(4520-4515, |4520-4500|, |4515-4500|) = max(5, 20, 15) = 20
        # Wilder smoothing: (prev_atr * 13 + 20) / 14 > prev_atr
        # This documents intentional Wilder overnight gap behavior

    def test_continuous_atr14_insufficient_returns_none(self):
        bars = [_bar(101, 100, 100.5)] * 13
        result = compute_continuous_atr14(bars, [])
        assert result is None
