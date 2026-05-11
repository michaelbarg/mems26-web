"""Tests for Day Type detection functions and IB classification."""

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/mems26_test.db")
os.environ.setdefault("BRIDGE_TOKEN", "test")

from backend.v9.systems.day_type.schemas import (
    BarInput, DayType, OpeningType, IBWidth, Behavior,
    FailedExtensionType, RangeCategory,
)
from backend.v9.systems.day_type.detector import (
    classify_ib_width, detect_opening_type, detect_behavior,
    detect_failed_extension, classify_range, calculate_confidence,
)


class TestIBWidthClassification:
    def test_narrow(self):
        assert classify_ib_width(10.0) == IBWidth.NARROW
        assert classify_ib_width(14.9) == IBWidth.NARROW

    def test_medium(self):
        assert classify_ib_width(15.0) == IBWidth.MEDIUM
        assert classify_ib_width(25.0) == IBWidth.MEDIUM

    def test_wide(self):
        assert classify_ib_width(25.1) == IBWidth.WIDE
        assert classify_ib_width(40.0) == IBWidth.WIDE

    def test_zero(self):
        assert classify_ib_width(0.0) == IBWidth.NARROW

    def test_custom_thresholds(self):
        assert classify_ib_width(12.0, narrow_max=10.0) == IBWidth.MEDIUM


class TestOpeningTypeDetection:
    def _bar(self, o, h, l, c, **kw):
        return BarInput(ts=0, session_min=0, open=o, high=h, low=l, close=c, **kw)

    def test_empty_bars(self):
        ot, dir, conf = detect_opening_type([])
        assert ot == OpeningType.UNKNOWN

    def test_single_bar(self):
        ot, dir, conf = detect_opening_type([self._bar(100, 105, 99, 104)])
        assert ot == OpeningType.UNKNOWN  # needs >= 2 bars

    def test_open_drive_up(self):
        bars = [
            self._bar(100, 103, 100, 103),
            self._bar(103, 106, 103, 106),
            self._bar(106, 109, 106, 109),
        ]
        ot, dir, conf = detect_opening_type(bars)
        assert ot == OpeningType.OPEN_DRIVE
        assert dir == "UP"

    def test_open_drive_down(self):
        bars = [
            self._bar(100, 100, 97, 97),
            self._bar(97, 97, 94, 94),
            self._bar(94, 94, 91, 91),
        ]
        ot, dir, conf = detect_opening_type(bars)
        assert ot == OpeningType.OPEN_DRIVE
        assert dir == "DOWN"

    def test_auction_inside(self):
        bars = [
            self._bar(100, 101, 99, 100.5),
            self._bar(100.5, 101.2, 99.5, 100),
        ]
        ot, dir, conf = detect_opening_type(bars)
        assert ot == OpeningType.OPEN_AUCTION_IN


class TestBehaviorDetection:
    def test_trending_up(self):
        assert detect_behavior(2, 0, False, 1.0) == Behavior.TRENDING_UP

    def test_trending_down(self):
        assert detect_behavior(0, 3, False, 1.0) == Behavior.TRENDING_DOWN

    def test_failed_extension(self):
        assert detect_behavior(1, 0, True, 1.0) == Behavior.FAILED_EXTENSION

    def test_compressed(self):
        assert detect_behavior(0, 0, False, 0.5) == Behavior.COMPRESSED

    def test_developing(self):
        assert detect_behavior(0, 0, False, 1.0) == Behavior.DEVELOPING


class TestRangeClassification:
    def test_compressed(self):
        assert classify_range(5.0, 10.0) == RangeCategory.COMPRESSED

    def test_normal(self):
        assert classify_range(10.0, 10.0) == RangeCategory.NORMAL

    def test_expanded(self):
        assert classify_range(15.0, 10.0) == RangeCategory.EXPANDED

    def test_extreme(self):
        assert classify_range(25.0, 10.0) == RangeCategory.EXTREME

    def test_zero_atr(self):
        assert classify_range(10.0, 0) == RangeCategory.NORMAL


class TestConfidenceCalculation:
    def test_empty_history(self):
        assert calculate_confidence([], False, False) == 0.1

    def test_single_vote(self):
        conf = calculate_confidence([DayType.Variation], False, False)
        assert 0.1 < conf < 0.3

    def test_consecutive_votes_boost(self):
        votes = [DayType.Variation] * 5
        conf = calculate_confidence(votes, False, False)
        assert conf > 0.4

    def test_behavior_agrees_boost(self):
        conf = calculate_confidence([DayType.Variation], True, False)
        assert conf > 0.3

    def test_all_aligned(self):
        votes = [DayType.Variation] * 5
        conf = calculate_confidence(votes, True, True)
        assert conf >= 0.9


class TestDayTypeEnums:
    def test_all_six_types(self):
        types = [e.value for e in DayType if e != DayType.UNKNOWN]
        assert len(types) == 6
        assert "Trend_Normal" in types
        assert "Variation" in types

    def test_opening_types(self):
        types = [e.value for e in OpeningType if e != OpeningType.UNKNOWN]
        assert len(types) == 5
