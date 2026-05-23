"""Tests for trade excursion from 5m bar highs/lows."""

import os
from datetime import datetime, timezone
from types import SimpleNamespace

os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")

from backend.v9.services.trade_excursion import compute_trade_excursion


def _trade(**kwargs):
    defaults = dict(
        entry_price=7435.25,
        entry_ts=datetime(2026, 5, 21, 2, 0, tzinfo=timezone.utc),
        exit_ts=None,
        direction="SHORT",
        t1=7431.25,
        t1_hit_ts="2026-05-21T02:15:00",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_short_excursion_mfe_mae_t1():
    # Bars span 7438 high down to 7427 low — SHORT entry 7435.25, T1 7431.25
    bars = [
        (7438.0, 7434.0),
        (7436.0, 7431.0),
        (7432.0, 7427.0),
    ]
    ex = compute_trade_excursion(_trade(), bars=bars)
    assert ex["price_high"] == 7438.0
    assert ex["price_low"] == 7427.0
    assert ex["mfe_pts"] == 8.25  # entry - low
    assert ex["mae_pts"] == 2.75  # high - entry
    assert ex["t1_closest_pts"] == 0.0
    assert ex["t1_reached"] is True
    assert ex["t1_at_mfe_pts"] == 0.0


def test_window_uses_hit_ts_when_entry_logged_late():
    entry_logged = datetime(2026, 5, 21, 7, 4, tzinfo=timezone.utc)
    hit = datetime(2026, 5, 21, 2, 15, tzinfo=timezone.utc)
    bars = [(7438.0, 7431.0)]
    ex = compute_trade_excursion(
        _trade(entry_ts=entry_logged, t1_hit_ts=hit, t2_hit_ts=hit),
        bars=bars,
    )
    assert ex["bars_count"] == 1
    assert ex["mfe_pts"] == 4.25


def test_long_t1_not_reached_closest():
    bars = [(7436.0, 7434.0), (7437.5, 7435.0)]
    ex = compute_trade_excursion(
        _trade(direction="LONG", entry_price=7434.0, t1=7440.0, t1_hit_ts=None),
        bars=bars,
    )
    assert ex["mfe_pts"] == 3.5
    assert ex["t1_closest_pts"] == 2.5  # 7440 - 7437.5
    assert ex["t1_reached"] is False
    assert ex["t1_at_mfe_pts"] == 2.5
