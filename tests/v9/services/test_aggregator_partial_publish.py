"""Tests for FiveMinAggregator partial bar publish (P27.5e) and bar close dispatch (P27.5c)."""
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytz
import pytest

ET = pytz.timezone("America/New_York")


def _make_aggregator():
    """Build a FiveMinAggregator with a mock on_bar_close."""
    from backend.v9.services.bar_aggregator_5min import FiveMinAggregator, TickEvent
    close_mock = MagicMock()
    agg = FiveMinAggregator(on_bar_close=close_mock)
    return agg, close_mock, TickEvent


def test_partial_publish_throttled_to_1hz():
    """Partial bar publishes at most once per second during intra-bar ticks."""
    agg, _, TickEvent = _make_aggregator()

    mock_router = MagicMock()
    mock_router.publish_threadsafe = MagicMock()

    # Ticks within the same 5-min window
    base_ts = ET.localize(datetime(2026, 5, 17, 10, 0, 30))

    with patch("backend.v9.api.v9.bars._bar_router", mock_router):
        # First tick opens the bar
        agg.on_tick(TickEvent(ts=base_ts, price=7500, size=1))
        first_partial_calls = mock_router.publish_threadsafe.call_count

        # Second tick within <1s — should not trigger another partial
        agg._last_partial_publish_ts = time.time()  # simulate just published
        agg.on_tick(TickEvent(ts=base_ts, price=7501, size=1))
        assert mock_router.publish_threadsafe.call_count == first_partial_calls

        # Simulate 1.1s passing
        agg._last_partial_publish_ts = time.time() - 1.1
        agg.on_tick(TickEvent(ts=base_ts, price=7502, size=1))

        # Should have published a partial
        partial_calls = [
            c for c in mock_router.publish_threadsafe.call_args_list
            if c[0][0] == "5min.partial"
        ]
        assert len(partial_calls) >= 1
        # Verify is_partial flag
        assert partial_calls[-1][0][1]["is_partial"] is True


def test_bar_close_publishes_5min():
    """When a bar closes (boundary cross), publish_threadsafe('5min', ...) is called."""
    agg, close_mock, TickEvent = _make_aggregator()

    mock_router = MagicMock()
    mock_router.publish_threadsafe = MagicMock()

    # First tick at 10:00:30 — opens bar for 10:00
    ts1 = ET.localize(datetime(2026, 5, 17, 10, 0, 30))
    # Second tick at 10:05:01 — crosses boundary, closes previous bar
    ts2 = ET.localize(datetime(2026, 5, 17, 10, 5, 1))

    with patch("backend.v9.api.v9.bars._bar_router", mock_router):
        agg.on_tick(TickEvent(ts=ts1, price=7500, size=10))
        agg.on_tick(TickEvent(ts=ts2, price=7510, size=5))

    # on_bar_close callback should have been called
    assert close_mock.called
    closed_bar = close_mock.call_args[0][0]
    assert closed_bar.open == 7500
    assert closed_bar.close == 7500  # only one tick in that bar
    assert closed_bar.volume == 10
