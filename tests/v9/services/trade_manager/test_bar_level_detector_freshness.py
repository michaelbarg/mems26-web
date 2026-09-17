"""F10 / T-390c: BAR-level logging only for fresh bars, not hydration/replay.

The bar_level_detector's BAR logging hook must skip bars older than 600 seconds
(10 minutes). This is the same anti-phantom pattern used in five_min_system.py.
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

import asyncio
import pytest

from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector


def run(coro):
    """Run a coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_event(bar_ts_iso, bar_high=7600.0, bar_low=7590.0):
    return {
        "ts": bar_ts_iso,
        "high": bar_high,
        "h": bar_high,
        "low": bar_low,
        "l": bar_low,
        "close": 7595.0,
        "c": 7595.0,
        "mode": "LIVE",
    }


class TestBarFreshnessFilter:
    """F10: only log kind='BAR' for bars younger than 600 seconds."""

    def test_old_bar_not_logged(self):
        """Bar from 1 hour ago should NOT be logged as BAR."""
        tm = MagicMock()
        tm.get_active_trades = MagicMock(return_value=[])
        tm._db = MagicMock()

        detector = BarLevelDetector(trade_manager=tm)

        # Bar timestamp from 1 hour ago
        old_ts = datetime.now(timezone.utc) - timedelta(hours=1)
        event = _make_event(old_ts.isoformat())

        mock_log = MagicMock()
        with patch(
            "backend.v9.services.situation_vector.log_decision_vector",
            mock_log
        ), patch(
            "backend.v9.services.situation_vector.compute_situation_vector",
            return_value=MagicMock()
        ):
            run(detector.on_bar(event))

        # log_decision_vector should NOT have been called with kind='BAR'
        for c in mock_log.call_args_list:
            if c.kwargs.get("kind") == "BAR" or (c.args and len(c.args) > 1 and c.args[1] == "BAR"):
                pytest.fail("BAR log should not be written for a 1-hour-old bar")

    def test_fresh_bar_logged(self):
        """Bar from 3 minutes ago should be logged as BAR."""
        tm = MagicMock()
        tm.get_active_trades = MagicMock(return_value=[])
        tm._db = MagicMock()

        detector = BarLevelDetector(trade_manager=tm)

        # Bar timestamp from 3 minutes ago
        fresh_ts = datetime.now(timezone.utc) - timedelta(minutes=3)
        event = _make_event(fresh_ts.isoformat())

        mock_log = MagicMock()
        mock_sv = MagicMock()
        with patch(
            "backend.v9.services.situation_vector.log_decision_vector",
            mock_log
        ), patch(
            "backend.v9.services.situation_vector.compute_situation_vector",
            return_value=mock_sv
        ), patch("dataclasses.asdict", return_value={"test": True}):
            run(detector.on_bar(event))

        # log_decision_vector SHOULD have been called with kind='BAR'
        mock_log.assert_called_once()
        assert mock_log.call_args.kwargs.get("kind") == "BAR"
