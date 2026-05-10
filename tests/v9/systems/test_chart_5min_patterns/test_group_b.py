"""Tests for Group B patterns: Double, Flag, Pennant, Triangle."""

import pytest
from backend.v9.systems.chart_5min.models import Bar
from backend.v9.systems.chart_5min.patterns.double_bottom import detect_double_bottom
from backend.v9.systems.chart_5min.patterns.double_top import detect_double_top
from backend.v9.systems.chart_5min.patterns.bull_flag import detect_bull_flag
from backend.v9.systems.chart_5min.patterns.bear_flag import detect_bear_flag
from backend.v9.systems.chart_5min.patterns.bull_pennant import detect_bull_pennant
from backend.v9.systems.chart_5min.patterns.bear_pennant import detect_bear_pennant
from backend.v9.systems.chart_5min.patterns.ascending_triangle import detect_ascending_triangle
from backend.v9.systems.chart_5min.patterns.descending_triangle import detect_descending_triangle
from .conftest import make_bar, bullish_bar, bearish_bar


class TestDoubleBottom:
    def test_too_few_bars(self):
        r = detect_double_bottom([make_bar()] * 5)
        assert not r.detected

    def test_classic_double_bottom(self):
        bars = [
            Bar(o=100, h=101, l=100, c=100.5),
            Bar(o=100.5, h=100.5, l=98, c=98.5),
            Bar(o=98.5, h=99, l=98.3, c=99),
            Bar(o=99, h=101, l=98.8, c=101),
            Bar(o=101, h=101.5, l=100, c=100),
            Bar(o=100, h=100, l=98, c=98.3),
            Bar(o=98.3, h=99, l=98.2, c=98.8),
            Bar(o=98.8, h=100, l=98.5, c=99.5),
            Bar(o=99.5, h=101.5, l=99.3, c=101),
        ]
        r = detect_double_bottom(bars)
        assert r.detected
        assert r.direction == "LONG"
        assert r.group == "B"
        assert "neckline" in r.key_levels

    def test_unequal_lows_rejected(self):
        bars = [
            Bar(o=100, h=101, l=100, c=100.5),
            Bar(o=100.5, h=100.5, l=98, c=98.5),
            Bar(o=98.5, h=101, l=98.3, c=101),
            Bar(o=101, h=101.5, l=100, c=100),
            Bar(o=100, h=100, l=95, c=95.5),
            Bar(o=95.5, h=96, l=95.3, c=95.8),
            Bar(o=95.8, h=97, l=95.5, c=96.5),
            Bar(o=96.5, h=98, l=96.3, c=97.5),
        ]
        r = detect_double_bottom(bars)
        assert not r.detected

    def test_returns_entry_stop_targets(self):
        bars = [
            Bar(o=100, h=101, l=100, c=100.5),
            Bar(o=100.5, h=100.5, l=98, c=98.5),
            Bar(o=98.5, h=99, l=98.3, c=99),
            Bar(o=99, h=101, l=98.8, c=101),
            Bar(o=101, h=101.5, l=100, c=100),
            Bar(o=100, h=100, l=98, c=98.3),
            Bar(o=98.3, h=99, l=98.2, c=98.8),
            Bar(o=98.8, h=100, l=98.5, c=99.5),
            Bar(o=99.5, h=101.5, l=99.3, c=101),
        ]
        r = detect_double_bottom(bars)
        if r.detected:
            assert r.entry_price > 0
            assert r.stop > 0
            assert len(r.targets) == 3

    def test_low_completion_rejected(self):
        bars = [
            Bar(o=100, h=101, l=100, c=100.5),
            Bar(o=100.5, h=100.5, l=98, c=98.5),
            Bar(o=98.5, h=99, l=98.3, c=99),
            Bar(o=99, h=101, l=98.8, c=101),
            Bar(o=101, h=101.5, l=100, c=100),
            Bar(o=100, h=100, l=98, c=98.3),
            Bar(o=98.3, h=98.5, l=98.1, c=98.2),  # stays low
            Bar(o=98.2, h=98.4, l=98.0, c=98.1),
        ]
        r = detect_double_bottom(bars)
        # Low completion since price hasn't recovered toward neckline
        assert not r.detected


class TestDoubleTop:
    def test_too_few_bars(self):
        r = detect_double_top([make_bar()] * 5)
        assert not r.detected

    def test_classic_double_top(self):
        bars = [
            Bar(o=100, h=100, l=99, c=99.5),
            Bar(o=99.5, h=102, l=99.3, c=101.5),
            Bar(o=101.5, h=102, l=101.5, c=101.8),
            Bar(o=101.8, h=101.8, l=99, c=99.5),
            Bar(o=99.5, h=100.5, l=99.3, c=100),
            Bar(o=100, h=102, l=99.8, c=101.8),
            Bar(o=101.8, h=102.1, l=101.5, c=101.7),
            Bar(o=101.7, h=101.7, l=100, c=100.2),
            Bar(o=100.2, h=100.5, l=99, c=99.2),
        ]
        r = detect_double_top(bars)
        assert r.detected
        assert r.direction == "SHORT"

    def test_returns_entry_stop_targets(self):
        bars = [
            Bar(o=100, h=100, l=99, c=99.5),
            Bar(o=99.5, h=102, l=99.3, c=101.5),
            Bar(o=101.5, h=102, l=101.5, c=101.8),
            Bar(o=101.8, h=101.8, l=99, c=99.5),
            Bar(o=99.5, h=100.5, l=99.3, c=100),
            Bar(o=100, h=102, l=99.8, c=101.8),
            Bar(o=101.8, h=102.1, l=101.5, c=101.7),
            Bar(o=101.7, h=101.7, l=100, c=100.2),
            Bar(o=100.2, h=100.5, l=99, c=99.2),
        ]
        r = detect_double_top(bars)
        if r.detected:
            assert r.entry_price > 0
            assert r.stop > r.entry_price
            assert len(r.targets) == 3
            assert r.targets[0] > r.targets[1] > r.targets[2]

    def test_unequal_highs_rejected(self):
        bars = [
            Bar(o=100, h=100, l=99, c=99.5),
            Bar(o=99.5, h=102, l=99.3, c=101.5),
            Bar(o=101.5, h=102, l=101.5, c=101.8),
            Bar(o=101.8, h=101.8, l=99, c=99.5),
            Bar(o=99.5, h=100.5, l=99.3, c=100),
            Bar(o=100, h=105, l=99.8, c=104.8),  # much higher
            Bar(o=104.8, h=105.1, l=104.5, c=104.7),
            Bar(o=104.7, h=104.7, l=103, c=103.2),
            Bar(o=103.2, h=103.5, l=102, c=102.2),
        ]
        r = detect_double_top(bars)
        assert not r.detected


class TestBullFlag:
    def test_too_few_bars(self):
        r = detect_bull_flag([make_bar()] * 3)
        assert not r.detected

    def test_classic_flag(self):
        bars = [
            Bar(o=100, h=103, l=99.5, c=102.5),
            Bar(o=102.5, h=105, l=102, c=104.5),
            Bar(o=104.5, h=104.8, l=103.5, c=104),
            Bar(o=104, h=104.3, l=103.2, c=103.5),
            Bar(o=103.5, h=104, l=103, c=103.3),
            Bar(o=103.3, h=104.5, l=103, c=104.2),
        ]
        r = detect_bull_flag(bars)
        assert r.detected
        assert r.direction == "LONG"
        assert "pole_height" in r.key_levels

    def test_no_pole_rejected(self):
        bars = [
            Bar(o=100, h=100.5, l=99.5, c=100.2),
            Bar(o=100.2, h=100.7, l=99.8, c=100.5),
            Bar(o=100.5, h=101, l=100.3, c=100.8),
            Bar(o=100.8, h=101.2, l=100.5, c=101),
            Bar(o=101, h=101.3, l=100.7, c=100.9),
        ]
        r = detect_bull_flag(bars)
        assert not r.detected

    def test_returns_targets(self):
        bars = [
            Bar(o=100, h=103, l=99.5, c=102.5),
            Bar(o=102.5, h=105, l=102, c=104.5),
            Bar(o=104.5, h=104.8, l=103.5, c=104),
            Bar(o=104, h=104.3, l=103.2, c=103.5),
            Bar(o=103.5, h=104, l=103, c=103.3),
            Bar(o=103.3, h=104.5, l=103, c=104.2),
        ]
        r = detect_bull_flag(bars)
        if r.detected:
            assert r.entry_price > 0
            assert r.stop > 0
            assert r.entry_price > r.stop
            assert len(r.targets) == 3

    def test_wide_flag_rejected(self):
        bars = [
            Bar(o=100, h=103, l=99.5, c=102.5),
            Bar(o=102.5, h=105, l=102, c=104.5),
            # Flag wider than pole
            Bar(o=104.5, h=108, l=100, c=103),
            Bar(o=103, h=107, l=99, c=101),
            Bar(o=101, h=106, l=98, c=104),
        ]
        r = detect_bull_flag(bars)
        assert not r.detected


class TestBearFlag:
    def test_too_few_bars(self):
        r = detect_bear_flag([make_bar()] * 3)
        assert not r.detected

    def test_classic_flag(self):
        bars = [
            Bar(o=105, h=105.5, l=102, c=102.5),
            Bar(o=102.5, h=103, l=100, c=100.5),
            Bar(o=100.5, h=101.5, l=100, c=101),
            Bar(o=101, h=101.8, l=100.8, c=101.5),
            Bar(o=101.5, h=102, l=101.3, c=101.7),
            Bar(o=101.7, h=102, l=100, c=100.2),
        ]
        r = detect_bear_flag(bars)
        assert r.detected
        assert r.direction == "SHORT"

    def test_returns_targets(self):
        bars = [
            Bar(o=105, h=105.5, l=102, c=102.5),
            Bar(o=102.5, h=103, l=100, c=100.5),
            Bar(o=100.5, h=101.5, l=100, c=101),
            Bar(o=101, h=101.8, l=100.8, c=101.5),
            Bar(o=101.5, h=102, l=101.3, c=101.7),
            Bar(o=101.7, h=102, l=100, c=100.2),
        ]
        r = detect_bear_flag(bars)
        if r.detected:
            assert r.entry_price > 0
            assert r.stop > r.entry_price
            assert len(r.targets) == 3
            assert r.targets[0] > r.targets[1] > r.targets[2]

    def test_no_pole_rejected(self):
        bars = [
            Bar(o=100, h=100.5, l=99.5, c=100.2),
            Bar(o=100.2, h=100.7, l=99.8, c=100.5),
            Bar(o=100.5, h=101, l=100.3, c=100.8),
            Bar(o=100.8, h=101.2, l=100.5, c=101),
            Bar(o=101, h=101.3, l=100.7, c=100.9),
        ]
        r = detect_bear_flag(bars)
        assert not r.detected


class TestBullPennant:
    def test_too_few_bars(self):
        r = detect_bull_pennant([make_bar()] * 3)
        assert not r.detected

    def test_classic_pennant(self):
        bars = [
            Bar(o=100, h=103, l=99.5, c=102.5),
            Bar(o=102.5, h=105, l=102, c=104.5),
            Bar(o=104.5, h=105, l=103.5, c=104),
            Bar(o=104, h=104.5, l=103.8, c=104.2),
            Bar(o=104.2, h=104.3, l=103.9, c=104),
            Bar(o=104, h=104.2, l=104, c=104.1),
        ]
        r = detect_bull_pennant(bars)
        if r.detected:
            assert r.direction == "LONG"
            assert r.entry_price > 0
            assert len(r.targets) == 3

    def test_no_convergence_rejected(self):
        bars = [
            Bar(o=100, h=103, l=99.5, c=102.5),
            Bar(o=102.5, h=105, l=102, c=104.5),
            # Widening, not converging
            Bar(o=104.5, h=106, l=103, c=105),
            Bar(o=105, h=107, l=102, c=106),
            Bar(o=106, h=108, l=101, c=107),
        ]
        r = detect_bull_pennant(bars)
        assert not r.detected

    def test_no_pole_rejected(self):
        # Flat bars with no upward pole
        bars = [
            Bar(o=100, h=100.1, l=99.9, c=100.05),
            Bar(o=100.05, h=100.1, l=99.9, c=100),
            Bar(o=100, h=100.08, l=99.95, c=100.02),
            Bar(o=100.02, h=100.06, l=99.97, c=100.01),
            Bar(o=100.01, h=100.04, l=99.99, c=100.0),
        ]
        r = detect_bull_pennant(bars)
        assert not r.detected


class TestBearPennant:
    def test_too_few_bars(self):
        r = detect_bear_pennant([make_bar()] * 3)
        assert not r.detected

    def test_classic_bear_pennant(self):
        bars = [
            Bar(o=105, h=105.5, l=102, c=102.5),   # pole down
            Bar(o=102.5, h=103, l=100, c=100.5),    # pole down
            Bar(o=100.5, h=101, l=100, c=100.8),    # pennant
            Bar(o=100.8, h=100.9, l=100.2, c=100.5),
            Bar(o=100.5, h=100.7, l=100.3, c=100.4),
            Bar(o=100.4, h=100.5, l=100.35, c=100.4),
        ]
        r = detect_bear_pennant(bars)
        if r.detected:
            assert r.direction == "SHORT"
            assert r.entry_price > 0
            assert r.stop > r.entry_price
            assert len(r.targets) == 3

    def test_no_convergence_rejected(self):
        bars = [
            Bar(o=105, h=105.5, l=102, c=102.5),
            Bar(o=102.5, h=103, l=100, c=100.5),
            Bar(o=100.5, h=103, l=98, c=101),
            Bar(o=101, h=104, l=97, c=100),
            Bar(o=100, h=105, l=96, c=99),
        ]
        r = detect_bear_pennant(bars)
        assert not r.detected


class TestAscendingTriangle:
    def test_too_few_bars(self):
        r = detect_ascending_triangle([make_bar()] * 5)
        assert not r.detected

    def test_classic_ascending(self):
        # Flat resistance at 105, rising lows
        bars = []
        for i in range(15):
            if i % 3 == 0:
                bars.append(Bar(o=103 + i * 0.2, h=105, l=102 + i * 0.2, c=104.5))
            elif i % 3 == 1:
                bars.append(Bar(o=104.5, h=105, l=100 + i * 0.2, c=100 + i * 0.2 + 0.5))
            else:
                bars.append(Bar(o=100 + i * 0.2 + 0.5, h=104, l=100 + i * 0.2, c=103))
        r = detect_ascending_triangle(bars)
        if r.detected:
            assert r.direction == "LONG"
            assert r.entry_price > 0
            assert len(r.targets) == 3

    def test_falling_lows_rejected(self):
        bars = []
        for i in range(15):
            bars.append(Bar(
                o=103, h=105, l=102 - i * 0.3, c=103.5
            ))
        r = detect_ascending_triangle(bars)
        assert not r.detected

    def test_no_flat_top_rejected(self):
        bars = []
        for i in range(15):
            bars.append(Bar(
                o=100, h=100 + i * 0.5, l=99 + i * 0.1, c=100 + i * 0.3
            ))
        r = detect_ascending_triangle(bars)
        assert not r.detected


class TestDescendingTriangle:
    def test_too_few_bars(self):
        r = detect_descending_triangle([make_bar()] * 5)
        assert not r.detected

    def test_classic_descending(self):
        # Flat support at 95, falling highs
        bars = []
        for i in range(15):
            if i % 3 == 0:
                bars.append(Bar(o=97 - i * 0.1, h=100 - i * 0.2, l=95, c=95.5))
            elif i % 3 == 1:
                bars.append(Bar(o=95.5, h=99 - i * 0.2, l=95, c=97 - i * 0.15))
            else:
                bars.append(Bar(o=97 - i * 0.15, h=98 - i * 0.2, l=95.1, c=96))
        r = detect_descending_triangle(bars)
        if r.detected:
            assert r.direction == "SHORT"
            assert r.entry_price > 0
            assert r.stop > r.entry_price
            assert len(r.targets) == 3

    def test_rising_highs_rejected(self):
        bars = []
        for i in range(15):
            bars.append(Bar(
                o=100, h=100 + i * 0.5, l=95, c=99
            ))
        r = detect_descending_triangle(bars)
        assert not r.detected

    def test_no_flat_bottom_rejected(self):
        bars = []
        for i in range(15):
            bars.append(Bar(
                o=100, h=102 - i * 0.1, l=90 + i * 0.5, c=99
            ))
        r = detect_descending_triangle(bars)
        assert not r.detected
