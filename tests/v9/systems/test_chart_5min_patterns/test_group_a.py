"""Tests for Group A patterns: Reactive + Initiative (OFA, 4 bars)."""

import pytest
from backend.v9.systems.chart_5min.models import Bar
from backend.v9.systems.chart_5min.patterns.reactive_buyer import detect_reactive_buyer
from backend.v9.systems.chart_5min.patterns.reactive_seller import detect_reactive_seller
from backend.v9.systems.chart_5min.patterns.initiative_buyer import detect_initiative_buyer
from backend.v9.systems.chart_5min.patterns.initiative_seller import detect_initiative_seller
from .conftest import make_bar, bullish_bar, bearish_bar


class TestReactiveBuyer:
    def test_too_few_bars(self):
        r = detect_reactive_buyer([make_bar()] * 3)
        assert not r.detected

    def test_no_sell_pressure(self):
        bars = [bullish_bar(100 + i) for i in range(4)]
        r = detect_reactive_buyer(bars)
        assert not r.detected

    def test_classic_pattern(self):
        bars = [
            bearish_bar(102, size=2),  # sell pressure
            bearish_bar(100, size=1),  # continued selling
            Bar(o=99, h=99.5, l=98.5, c=99.3, vol=80, belly_sellers=30, belly_buyers=50),  # exhaustion
            bullish_bar(99.3, size=1.5),  # reversal
        ]
        r = detect_reactive_buyer(bars)
        assert r.detected
        assert r.direction == "LONG"
        assert r.group == "A"
        assert r.pattern_id == "reactive_buyer"
        assert r.bar_count == 4

    def test_returns_key_levels(self):
        bars = [
            bearish_bar(102, size=2),
            bearish_bar(100, size=1),
            Bar(o=99, h=99.5, l=98.5, c=99.3, vol=80, belly_sellers=30, belly_buyers=50),
            bullish_bar(99.3, size=1.5),
        ]
        r = detect_reactive_buyer(bars)
        if r.detected:
            assert "support" in r.key_levels
            assert "entry_zone" in r.key_levels
            assert r.entry_price > 0
            assert r.stop > 0
            assert len(r.targets) == 3
            assert r.targets[0] < r.targets[1] < r.targets[2]

    def test_zero_range_rejected(self):
        bars = [Bar(o=100, h=100, l=100, c=100)] * 4
        r = detect_reactive_buyer(bars)
        assert not r.detected

    def test_method_is_ofa(self):
        bars = [
            bearish_bar(102, size=2),
            bearish_bar(100, size=1),
            Bar(o=99, h=99.5, l=98.5, c=99.3, vol=80, belly_sellers=30, belly_buyers=50),
            bullish_bar(99.3, size=1.5),
        ]
        r = detect_reactive_buyer(bars)
        if r.detected:
            assert r.method == "OFA"
            assert r.potential_r == "2-4R"

    def test_near_val_increases_completion(self):
        bars = [
            bearish_bar(102, size=2),
            bearish_bar(100, size=1),
            Bar(o=99, h=99.5, l=98.5, c=99.3, vol=80, belly_sellers=30, belly_buyers=50),
            Bar(o=99.3, h=100.8, l=99, c=100.5, vol=100, val=100.6),
        ]
        r = detect_reactive_buyer(bars)
        if r.detected:
            assert r.completion >= 0.85

    def test_no_reversal_bar_rejected(self):
        bars = [
            bearish_bar(102, size=2),
            bearish_bar(100, size=1),
            Bar(o=99, h=99.5, l=98.5, c=99.3, vol=80, belly_sellers=30, belly_buyers=50),
            bearish_bar(99, size=0.5),  # no reversal
        ]
        r = detect_reactive_buyer(bars)
        assert not r.detected

    def test_confidence_range(self):
        bars = [
            bearish_bar(102, size=2),
            bearish_bar(100, size=1),
            Bar(o=99, h=99.5, l=98.5, c=99.3, vol=80, belly_sellers=30, belly_buyers=50),
            bullish_bar(99.3, size=1.5),
        ]
        r = detect_reactive_buyer(bars)
        if r.detected:
            assert 0.0 < r.confidence <= 1.0


class TestReactiveSeller:
    def test_too_few_bars(self):
        r = detect_reactive_seller([make_bar()] * 3)
        assert not r.detected

    def test_classic_pattern(self):
        bars = [
            bullish_bar(98, size=2),
            bullish_bar(100, size=1),
            Bar(o=101, h=101.5, l=100.5, c=100.7, vol=80, belly_buyers=30, belly_sellers=50),
            bearish_bar(100.7, size=1.5),
        ]
        r = detect_reactive_seller(bars)
        assert r.detected
        assert r.direction == "SHORT"
        assert r.group == "A"

    def test_returns_entry_stop_targets(self):
        bars = [
            bullish_bar(98, size=2),
            bullish_bar(100, size=1),
            Bar(o=101, h=101.5, l=100.5, c=100.7, vol=80, belly_buyers=30, belly_sellers=50),
            bearish_bar(100.7, size=1.5),
        ]
        r = detect_reactive_seller(bars)
        if r.detected:
            assert r.entry_price > 0
            assert r.stop > r.entry_price  # stop above entry for SHORT
            assert len(r.targets) == 3
            assert r.targets[0] > r.targets[1] > r.targets[2]

    def test_zero_range_rejected(self):
        bars = [Bar(o=100, h=100, l=100, c=100)] * 4
        r = detect_reactive_seller(bars)
        assert not r.detected

    def test_no_buy_pressure_rejected(self):
        bars = [bearish_bar(100 - i) for i in range(4)]
        r = detect_reactive_seller(bars)
        assert not r.detected

    def test_no_reversal_rejected(self):
        bars = [
            bullish_bar(98, size=2),
            bullish_bar(100, size=1),
            Bar(o=101, h=101.5, l=100.5, c=100.7, vol=80, belly_buyers=30, belly_sellers=50),
            bullish_bar(100.7, size=0.5),  # no bearish reversal
        ]
        r = detect_reactive_seller(bars)
        assert not r.detected

    def test_near_vah_completion(self):
        bars = [
            bullish_bar(98, size=2),
            bullish_bar(100, size=1),
            Bar(o=101, h=101.5, l=100.5, c=100.7, vol=80, belly_buyers=30, belly_sellers=50),
            Bar(o=100.7, h=101.0, l=99.5, c=99.8, vol=100, vah=100.9),
        ]
        r = detect_reactive_seller(bars)
        if r.detected:
            assert r.completion >= 0.85


class TestInitiativeBuyer:
    def test_too_few_bars(self):
        r = detect_initiative_buyer([make_bar()] * 3)
        assert not r.detected

    def test_rising_poc(self):
        bars = [
            Bar(o=100, h=101, l=99.5, c=100.5, vol=100, poc_price=100.0, cumulative_delta=10, belly_buyers=60, belly_sellers=20),
            Bar(o=100.5, h=101.5, l=100, c=101, vol=100, poc_price=100.5, cumulative_delta=20, belly_buyers=65, belly_sellers=15),
            Bar(o=101, h=102, l=100.5, c=101.5, vol=100, poc_price=101.0, cumulative_delta=35, belly_buyers=70, belly_sellers=10),
            Bar(o=101.5, h=102.5, l=101, c=102, vol=100, poc_price=101.5, cumulative_delta=50, belly_buyers=75, belly_sellers=10),
        ]
        r = detect_initiative_buyer(bars)
        assert r.detected
        assert r.direction == "LONG"
        assert r.potential_r == "4-8R"

    def test_negative_delta_rejects(self):
        bars = [
            Bar(o=100, h=101, l=99.5, c=100.5, vol=100, poc_price=100.0, cumulative_delta=-10),
            Bar(o=100.5, h=101.5, l=100, c=101, vol=100, poc_price=100.5, cumulative_delta=-20),
            Bar(o=101, h=102, l=100.5, c=101.5, vol=100, poc_price=101.0, cumulative_delta=-5),
            Bar(o=101.5, h=102.5, l=101, c=102, vol=100, poc_price=101.5, cumulative_delta=-1),
        ]
        r = detect_initiative_buyer(bars)
        assert not r.detected

    def test_returns_entry_stop_targets(self):
        bars = [
            Bar(o=100, h=101, l=99.5, c=100.5, vol=100, poc_price=100.0, cumulative_delta=10, belly_buyers=60, belly_sellers=20),
            Bar(o=100.5, h=101.5, l=100, c=101, vol=100, poc_price=100.5, cumulative_delta=20, belly_buyers=65, belly_sellers=15),
            Bar(o=101, h=102, l=100.5, c=101.5, vol=100, poc_price=101.0, cumulative_delta=35, belly_buyers=70, belly_sellers=10),
            Bar(o=101.5, h=102.5, l=101, c=102, vol=100, poc_price=101.5, cumulative_delta=50, belly_buyers=75, belly_sellers=10),
        ]
        r = detect_initiative_buyer(bars)
        assert r.detected
        assert r.entry_price == 102.0
        assert r.stop == 99.5
        assert len(r.targets) == 3
        assert r.targets[0] < r.targets[1] < r.targets[2]

    def test_insufficient_poc_migration_rejected(self):
        bars = [
            Bar(o=100, h=101, l=99.5, c=100.5, vol=100, poc_price=100.0, cumulative_delta=10, belly_buyers=60, belly_sellers=20),
            Bar(o=100.5, h=101, l=100, c=100.5, vol=100, poc_price=100.1, cumulative_delta=12, belly_buyers=60, belly_sellers=20),
            Bar(o=100.5, h=101.2, l=100.3, c=100.8, vol=100, poc_price=100.2, cumulative_delta=15, belly_buyers=60, belly_sellers=20),
            Bar(o=100.8, h=101.3, l=100.5, c=101, vol=100, poc_price=100.3, cumulative_delta=18, belly_buyers=60, belly_sellers=20),
        ]
        r = detect_initiative_buyer(bars)
        # POC migration = 0.3, needs at least 4 ticks (1.0 pt)
        assert not r.detected

    def test_sellers_dominating_rejected(self):
        bars = [
            Bar(o=100, h=101, l=99.5, c=100.5, vol=100, poc_price=100.0, cumulative_delta=10, belly_buyers=20, belly_sellers=60),
            Bar(o=100.5, h=101.5, l=100, c=101, vol=100, poc_price=100.5, cumulative_delta=20, belly_buyers=20, belly_sellers=65),
            Bar(o=101, h=102, l=100.5, c=101.5, vol=100, poc_price=101.0, cumulative_delta=35, belly_buyers=20, belly_sellers=70),
            Bar(o=101.5, h=102.5, l=101, c=102, vol=100, poc_price=101.5, cumulative_delta=50, belly_buyers=20, belly_sellers=75),
        ]
        r = detect_initiative_buyer(bars)
        assert not r.detected

    def test_no_poc_uses_close_prices(self):
        bars = [
            Bar(o=100, h=101, l=99.5, c=100.5, vol=100, poc_price=0, cumulative_delta=10, belly_buyers=60, belly_sellers=20),
            Bar(o=100.5, h=101.5, l=100, c=101, vol=100, poc_price=0, cumulative_delta=20, belly_buyers=65, belly_sellers=15),
            Bar(o=101, h=102, l=100.5, c=101.5, vol=100, poc_price=0, cumulative_delta=35, belly_buyers=70, belly_sellers=10),
            Bar(o=101.5, h=102.5, l=101, c=102, vol=100, poc_price=0, cumulative_delta=50, belly_buyers=75, belly_sellers=10),
        ]
        r = detect_initiative_buyer(bars)
        assert r.detected


class TestInitiativeSeller:
    def test_too_few_bars(self):
        r = detect_initiative_seller([make_bar()] * 3)
        assert not r.detected

    def test_falling_poc(self):
        bars = [
            Bar(o=102, h=102.5, l=101, c=101.5, vol=100, poc_price=102.0, cumulative_delta=-10, belly_sellers=60, belly_buyers=20),
            Bar(o=101.5, h=102, l=100.5, c=101, vol=100, poc_price=101.5, cumulative_delta=-20, belly_sellers=65, belly_buyers=15),
            Bar(o=101, h=101.5, l=100, c=100.5, vol=100, poc_price=101.0, cumulative_delta=-35, belly_sellers=70, belly_buyers=10),
            Bar(o=100.5, h=101, l=99.5, c=100, vol=100, poc_price=100.5, cumulative_delta=-50, belly_sellers=75, belly_buyers=10),
        ]
        r = detect_initiative_seller(bars)
        assert r.detected
        assert r.direction == "SHORT"

    def test_returns_entry_stop_targets(self):
        bars = [
            Bar(o=102, h=102.5, l=101, c=101.5, vol=100, poc_price=102.0, cumulative_delta=-10, belly_sellers=60, belly_buyers=20),
            Bar(o=101.5, h=102, l=100.5, c=101, vol=100, poc_price=101.5, cumulative_delta=-20, belly_sellers=65, belly_buyers=15),
            Bar(o=101, h=101.5, l=100, c=100.5, vol=100, poc_price=101.0, cumulative_delta=-35, belly_sellers=70, belly_buyers=10),
            Bar(o=100.5, h=101, l=99.5, c=100, vol=100, poc_price=100.5, cumulative_delta=-50, belly_sellers=75, belly_buyers=10),
        ]
        r = detect_initiative_seller(bars)
        assert r.detected
        assert r.entry_price == 100.0
        assert r.stop == 102.5
        assert len(r.targets) == 3
        assert r.targets[0] > r.targets[1] > r.targets[2]

    def test_positive_delta_rejected(self):
        bars = [
            Bar(o=102, h=102.5, l=101, c=101.5, vol=100, poc_price=102.0, cumulative_delta=10, belly_sellers=60, belly_buyers=20),
            Bar(o=101.5, h=102, l=100.5, c=101, vol=100, poc_price=101.5, cumulative_delta=5, belly_sellers=65, belly_buyers=15),
            Bar(o=101, h=101.5, l=100, c=100.5, vol=100, poc_price=101.0, cumulative_delta=2, belly_sellers=70, belly_buyers=10),
            Bar(o=100.5, h=101, l=99.5, c=100, vol=100, poc_price=100.5, cumulative_delta=1, belly_sellers=75, belly_buyers=10),
        ]
        r = detect_initiative_seller(bars)
        assert not r.detected

    def test_insufficient_poc_migration_rejected(self):
        bars = [
            Bar(o=102, h=102.5, l=101, c=101.5, vol=100, poc_price=102.0, cumulative_delta=-10, belly_sellers=60, belly_buyers=20),
            Bar(o=101.5, h=102, l=100.5, c=101, vol=100, poc_price=101.9, cumulative_delta=-20, belly_sellers=65, belly_buyers=15),
            Bar(o=101, h=101.5, l=100, c=100.5, vol=100, poc_price=101.8, cumulative_delta=-35, belly_sellers=70, belly_buyers=10),
            Bar(o=100.5, h=101, l=99.5, c=100, vol=100, poc_price=101.7, cumulative_delta=-50, belly_sellers=75, belly_buyers=10),
        ]
        r = detect_initiative_seller(bars)
        # POC migration = 0.3, needs 4 ticks (1.0 pt)
        assert not r.detected

    def test_buyers_dominating_rejected(self):
        bars = [
            Bar(o=102, h=102.5, l=101, c=101.5, vol=100, poc_price=102.0, cumulative_delta=-10, belly_sellers=20, belly_buyers=60),
            Bar(o=101.5, h=102, l=100.5, c=101, vol=100, poc_price=101.5, cumulative_delta=-20, belly_sellers=15, belly_buyers=65),
            Bar(o=101, h=101.5, l=100, c=100.5, vol=100, poc_price=101.0, cumulative_delta=-35, belly_sellers=10, belly_buyers=70),
            Bar(o=100.5, h=101, l=99.5, c=100, vol=100, poc_price=100.5, cumulative_delta=-50, belly_sellers=10, belly_buyers=75),
        ]
        r = detect_initiative_seller(bars)
        assert not r.detected
