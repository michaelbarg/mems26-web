"""Tests for 5-min Bar Aggregator (Principle 10: data-driven)."""

from datetime import datetime
import pytz
from backend.v9.services.bar_aggregator_5min import FiveMinAggregator, TickEvent, Bar5Min

ET = pytz.timezone('America/New_York')


def _tick(h, m, s, price, size=1):
    ts = ET.localize(datetime(2026, 5, 12, h, m, s))
    return TickEvent(ts=ts, price=price, size=size)


class TestBarAggregation:
    def test_first_tick_starts_bar(self):
        closed_bars = []
        agg = FiveMinAggregator(on_bar_close=lambda b: closed_bars.append(b))
        agg.on_tick(_tick(10, 0, 0, 7400.0))
        assert agg.current_bar is not None
        assert agg.current_bar.open == 7400.0
        assert len(closed_bars) == 0

    def test_multiple_ticks_update_bar(self):
        agg = FiveMinAggregator(on_bar_close=lambda b: None)
        agg.on_tick(_tick(10, 0, 0, 7400.0))
        agg.on_tick(_tick(10, 1, 0, 7405.0))
        agg.on_tick(_tick(10, 2, 0, 7395.0))
        agg.on_tick(_tick(10, 3, 0, 7402.0))
        assert agg.current_bar.open == 7400.0
        assert agg.current_bar.high == 7405.0
        assert agg.current_bar.low == 7395.0
        assert agg.current_bar.close == 7402.0
        assert agg.current_bar.tick_count == 4

    def test_boundary_crossing_closes_bar(self):
        closed_bars = []
        agg = FiveMinAggregator(on_bar_close=lambda b: closed_bars.append(b))
        agg.on_tick(_tick(10, 3, 0, 7400.0))
        agg.on_tick(_tick(10, 4, 59, 7410.0))
        # Cross into next 5-min window
        agg.on_tick(_tick(10, 5, 0, 7412.0))
        assert len(closed_bars) == 1
        assert closed_bars[0].open == 7400.0
        assert closed_bars[0].close == 7410.0
        assert agg.current_bar.open == 7412.0

    def test_session_tagged_on_bar(self):
        closed_bars = []
        agg = FiveMinAggregator(on_bar_close=lambda b: closed_bars.append(b))
        # 3 AM ET = OVERNIGHT
        agg.on_tick(_tick(3, 0, 0, 7400.0))
        agg.on_tick(_tick(3, 5, 0, 7405.0))  # crosses boundary
        assert len(closed_bars) == 1
        assert closed_bars[0].session == "OVERNIGHT"

    def test_overnight_bar_processes_normally(self):
        """Principle 10: bars build during overnight — no gating."""
        agg = FiveMinAggregator(on_bar_close=lambda b: None)
        agg.on_tick(_tick(2, 30, 0, 7400.0))  # 2:30 AM ET
        assert agg.current_bar is not None
        assert agg.current_bar.session == "OVERNIGHT"

    def test_pre_market_bar_processes_normally(self):
        agg = FiveMinAggregator(on_bar_close=lambda b: None)
        agg.on_tick(_tick(8, 15, 0, 7400.0))  # 8:15 AM ET
        assert agg.current_bar is not None
        assert agg.current_bar.session == "PRE_MARKET"

    def test_cash_hours_bar(self):
        agg = FiveMinAggregator(on_bar_close=lambda b: None)
        agg.on_tick(_tick(11, 0, 0, 7400.0))  # 11:00 AM ET
        assert agg.current_bar.session == "CASH_HOURS"

    def test_stale_bar_force_close(self):
        closed_bars = []
        agg = FiveMinAggregator(on_bar_close=lambda b: closed_bars.append(b))
        agg.on_tick(_tick(10, 0, 0, 7400.0))
        # Force close 7 minutes later
        future = ET.localize(datetime(2026, 5, 12, 10, 7, 0))
        agg.force_close_if_stale(now=future)
        assert len(closed_bars) == 1
        assert closed_bars[0].close == 7400.0
        assert agg.current_bar is None

    def test_volume_accumulates(self):
        agg = FiveMinAggregator(on_bar_close=lambda b: None)
        agg.on_tick(_tick(10, 0, 0, 7400.0, size=5))
        agg.on_tick(_tick(10, 1, 0, 7401.0, size=3))
        assert agg.current_bar.volume == 8

    def test_status(self):
        agg = FiveMinAggregator(on_bar_close=lambda b: None)
        agg.on_tick(_tick(10, 0, 0, 7400.0))
        s = agg.get_status()
        assert s["ticks_processed"] == 1
        assert s["current_bar_open"] is True
        assert s["current_bar_ticks"] == 1
