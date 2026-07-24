"""Phase 3 AC — OPENING_TYPE_SEEDS_S1_V1 seeds day-bias from opening type.

Replay 07-23: opened after −74 overnight below value → detector should yield
a directional open → seed = "DOWN". Must be available by 16:45 IL (09:45 ET)
and must NOT flip until IB-lock.

If reverted → RED because the first 15 min of RTH have no dir_bias (too few
bars for LSMA window) and no expansion (IB not locked yet), leaving the playbook
blind to day-direction exactly when the opening signal is strongest.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, time


# Simplified 07-23 opening bars: opened 7480, dropped hard in 3 bars
# Open at 7480, well below prior VAH 7530 → out of value, directional
BARS_0723 = [
    {"ts": "2026-07-23T16:30", "open": "7480", "high": "7486", "low": "7478", "close": "7470", "volume": "1200"},
    {"ts": "2026-07-23T16:35", "open": "7470", "high": "7473", "low": "7460", "close": "7462", "volume": "1100"},
    {"ts": "2026-07-23T16:40", "open": "7462", "high": "7465", "low": "7450", "close": "7455", "volume": "900"},
]
PREV_TPO = {"vah_price": "7530", "val_price": "7480"}


def _mock_read(sql, params):
    if "v9_bars_5min_woodies" in sql and "16:30" in sql:
        return BARS_0723
    return []


def _mock_read_one(sql, params):
    if "v9_tpo_sessions" in sql:
        return PREV_TPO
    return None


def test_seed_returns_down_on_0723_opening(monkeypatch):
    """07-23 opening: below value, dropping → seed should be DOWN."""
    monkeypatch.setenv("OPENING_TYPE_SEEDS_S1_V1", "1")

    mock_et = MagicMock()
    mock_et.time.return_value = time(9, 35)
    mock_et.date.return_value = MagicMock()
    mock_et.date.return_value.isoformat.return_value = "2026-07-23"

    with patch("backend.v9.services.market_clock.now_et", return_value=mock_et), \
         patch("backend.v9.db.read.read_all", side_effect=_mock_read), \
         patch("backend.v9.db.read.read_one", side_effect=_mock_read_one), \
         patch("backend.v9.services.market_clock.get_previous_trading_day",
               return_value=MagicMock(isoformat=lambda: "2026-07-22")):

        from backend.v9.services.trade_context import get_opening_type_seed
        seed = get_opening_type_seed()

        assert seed == "DOWN", (
            f"Expected DOWN seed for 07-23 opening (below value, dropping), got {seed}. "
            "If reverted → RED: first 15min have no dir_bias/expansion, playbook is blind"
        )


def test_seed_none_when_flag_off(monkeypatch):
    """Flag OFF → no seed."""
    monkeypatch.delenv("OPENING_TYPE_SEEDS_S1_V1", raising=False)
    from backend.v9.services.trade_context import get_opening_type_seed
    assert get_opening_type_seed() is None


def test_seed_none_outside_window(monkeypatch):
    """After 09:45 ET → no seed (window closed)."""
    monkeypatch.setenv("OPENING_TYPE_SEEDS_S1_V1", "1")

    mock_et = MagicMock()
    mock_et.time.return_value = time(10, 0)

    with patch("backend.v9.services.market_clock.now_et", return_value=mock_et):
        from backend.v9.services.trade_context import get_opening_type_seed
        assert get_opening_type_seed() is None


def test_seed_none_on_auction(monkeypatch):
    """Auction opening (rotational) → no seed."""
    monkeypatch.setenv("OPENING_TYPE_SEEDS_S1_V1", "1")

    # Auction: price rotates around the open
    auction_bars = [
        {"ts": "t", "open": "7500", "high": "7510", "low": "7490", "close": "7505", "volume": "800"},
        {"ts": "t", "open": "7505", "high": "7508", "low": "7495", "close": "7498", "volume": "700"},
        {"ts": "t", "open": "7498", "high": "7506", "low": "7494", "close": "7502", "volume": "600"},
    ]
    auction_tpo = {"vah_price": "7520", "val_price": "7480"}

    mock_et = MagicMock()
    mock_et.time.return_value = time(9, 35)
    mock_et.date.return_value = MagicMock()
    mock_et.date.return_value.isoformat.return_value = "2026-07-23"

    def _mock_read_auction(sql, params):
        if "v9_bars_5min_woodies" in sql:
            return auction_bars
        return []

    def _mock_one_auction(sql, params):
        if "v9_tpo_sessions" in sql:
            return auction_tpo
        return None

    with patch("backend.v9.services.market_clock.now_et", return_value=mock_et), \
         patch("backend.v9.db.read.read_all", side_effect=_mock_read_auction), \
         patch("backend.v9.db.read.read_one", side_effect=_mock_one_auction), \
         patch("backend.v9.services.market_clock.get_previous_trading_day",
               return_value=MagicMock(isoformat=lambda: "2026-07-22")):

        from backend.v9.services.trade_context import get_opening_type_seed
        seed = get_opening_type_seed()
        assert seed is None, (
            f"Auction opening should NOT seed a direction, got {seed}"
        )
