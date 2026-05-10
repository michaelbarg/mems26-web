"""Tests for pattern detection helper functions."""

from backend.v9.systems.chart_5min.models import Bar
from backend.v9.systems.chart_5min.patterns._helpers import (
    find_pivots, swing_highs, swing_lows, prices_near,
    linear_regression_slope, is_converging, avg_body, avg_range,
)


class TestFindPivots:
    def test_empty_bars(self):
        assert find_pivots([], lookback=2) == []

    def test_too_few_bars(self):
        bars = [Bar(o=100, h=101, l=99, c=100)] * 3
        assert find_pivots(bars, lookback=2) == []

    def test_single_swing_high(self):
        bars = [
            Bar(o=100, h=101, l=99, c=100),
            Bar(o=100, h=102, l=99, c=101),
            Bar(o=101, h=105, l=100, c=104),  # pivot high
            Bar(o=104, h=104.5, l=102, c=103),
            Bar(o=103, h=103.5, l=101, c=102),
        ]
        pivots = find_pivots(bars, lookback=2)
        highs = swing_highs(pivots)
        assert len(highs) >= 1
        assert highs[0].price == 105

    def test_single_swing_low(self):
        bars = [
            Bar(o=105, h=106, l=104, c=105),
            Bar(o=105, h=105.5, l=103, c=103.5),
            Bar(o=103.5, h=104, l=95, c=96),  # pivot low
            Bar(o=96, h=98, l=96.5, c=97.5),
            Bar(o=97.5, h=99, l=97, c=98.5),
        ]
        pivots = find_pivots(bars, lookback=2)
        lows = swing_lows(pivots)
        assert len(lows) >= 1
        assert lows[0].price == 95

    def test_lookback_1(self):
        bars = [
            Bar(o=100, h=101, l=99, c=100),
            Bar(o=100, h=105, l=99, c=104),  # high
            Bar(o=104, h=104.5, l=102, c=103),
        ]
        pivots = find_pivots(bars, lookback=1)
        highs = swing_highs(pivots)
        assert len(highs) >= 1


class TestPricesNear:
    def test_same_price(self):
        assert prices_near(100, 100)

    def test_near_prices(self):
        assert prices_near(100, 100.1, tolerance_pct=0.15)

    def test_far_prices(self):
        assert not prices_near(100, 120, tolerance_pct=0.15)

    def test_zero_values(self):
        assert prices_near(0, 0)

    def test_one_zero(self):
        # One zero: avg is tiny, ratio is large, so not "near"
        assert not prices_near(0.0001, 0, tolerance_pct=0.15)


class TestLinearRegressionSlope:
    def test_rising(self):
        s = linear_regression_slope([1, 2, 3, 4, 5])
        assert s > 0

    def test_falling(self):
        s = linear_regression_slope([5, 4, 3, 2, 1])
        assert s < 0

    def test_flat(self):
        s = linear_regression_slope([3, 3, 3, 3])
        assert s == 0

    def test_single_value(self):
        s = linear_regression_slope([5])
        assert s == 0

    def test_two_values(self):
        s = linear_regression_slope([1, 3])
        assert s > 0


class TestIsConverging:
    def test_converging(self):
        assert is_converging([10, 9, 8], [1, 2, 3])

    def test_not_converging(self):
        assert not is_converging([8, 9, 10], [1, 2, 3])

    def test_too_few(self):
        assert not is_converging([10], [1])


class TestAvgBody:
    def test_empty(self):
        assert avg_body([]) == 0.0

    def test_single(self):
        b = Bar(o=100, h=102, l=99, c=101)
        assert avg_body([b]) == 1.0


class TestAvgRange:
    def test_empty(self):
        assert avg_range([]) == 0.0

    def test_single(self):
        b = Bar(o=100, h=102, l=99, c=101)
        assert avg_range([b]) == 3.0
