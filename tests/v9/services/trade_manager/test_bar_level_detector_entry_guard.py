"""Regression: BarLevelDetector must not apply a bar to a trade that opened
after the bar started (Bug E — stop_hit_ts precedes entry_ts).

Root cause: the detector processes every active trade on every incoming bar
without checking whether the bar's timestamp predates the trade's entry.
A bar pushed after its close-time could retroactively hit the stop of a trade
that was opened during or after that bar, recording fill_ts < entry_ts.
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import asyncio

import pytest

from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector


def run(coro):
    """Run a coroutine synchronously (no pytest-asyncio dependency)."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_trade(trade_id, direction, entry_price, stop, entry_ts, state="FILLED"):
    t = MagicMock()
    t.id = trade_id
    t.state = state
    t.direction = direction
    t.entry_price = entry_price
    t.stop = stop
    t.t1 = None
    t.t2 = None
    t.t3 = None
    t.t1_hit_ts = None
    t.t2_hit_ts = None
    t.t3_hit_ts = None
    t.entry_ts = entry_ts
    return t


def _make_event(bar_ts_iso, bar_high, bar_low):
    return {
        "ts": bar_ts_iso,
        "high": bar_high,
        "h": bar_high,
        "low": bar_low,
        "l": bar_low,
        "mode": "LIVE",
    }


def test_bar_before_entry_skipped():
    """Bar that started BEFORE trade entry must NOT trigger a stop hit."""
    tm = MagicMock()
    tm.get_active_trades = MagicMock()
    tm._db = MagicMock()

    bar_ts = datetime(2026, 5, 29, 12, 30, 0, tzinfo=timezone.utc)   # bar at 12:30
    entry_ts = datetime(2026, 5, 29, 12, 34, 3, tzinfo=timezone.utc)  # trade at 12:34

    trade = _make_trade(
        trade_id=1,
        direction="LONG",
        entry_price=7580.0,
        stop=7570.0,
        entry_ts=entry_ts,
    )
    tm.get_active_trades.return_value = [trade]

    detector = BarLevelDetector(trade_manager=tm)

    # Bar's low dips below stop — would trigger hit if not guarded
    event = _make_event(bar_ts.isoformat(), bar_high=7590.0, bar_low=7568.0)
    run(detector.on_bar(event))

    tm.on_stop_hit.assert_not_called()


def test_bar_after_entry_triggers_stop():
    """Bar that started AFTER trade entry MUST trigger a stop hit."""
    tm = MagicMock()
    tm.get_active_trades = MagicMock()
    tm._db = MagicMock()

    entry_ts = datetime(2026, 5, 29, 12, 30, 0, tzinfo=timezone.utc)
    bar_ts = datetime(2026, 5, 29, 12, 35, 0, tzinfo=timezone.utc)   # bar after entry

    trade = _make_trade(
        trade_id=2,
        direction="LONG",
        entry_price=7580.0,
        stop=7570.0,
        entry_ts=entry_ts,
    )
    tm.get_active_trades.return_value = [trade]

    detector = BarLevelDetector(trade_manager=tm)

    event = _make_event(bar_ts.isoformat(), bar_high=7590.0, bar_low=7568.0)
    run(detector.on_bar(event))

    tm.on_stop_hit.assert_called_once_with(2, fill_ts=bar_ts)


def test_bar_same_second_as_entry_not_skipped():
    """Bar with ts == entry_ts is NOT skipped (trade could have been filled
    on the bar open; borderline bars must be processed)."""
    tm = MagicMock()
    tm.get_active_trades = MagicMock()
    tm._db = MagicMock()

    ts = datetime(2026, 5, 29, 12, 35, 0, tzinfo=timezone.utc)

    trade = _make_trade(
        trade_id=3,
        direction="LONG",
        entry_price=7580.0,
        stop=7570.0,
        entry_ts=ts,
    )
    tm.get_active_trades.return_value = [trade]

    detector = BarLevelDetector(trade_manager=tm)

    event = _make_event(ts.isoformat(), bar_high=7590.0, bar_low=7568.0)
    run(detector.on_bar(event))

    tm.on_stop_hit.assert_called_once()
