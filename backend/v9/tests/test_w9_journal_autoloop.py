"""W9 — SYSTEM6_JOURNAL_AUTOLOOP_V1: per-bar exit signal journaling (2026-07-27).

The v9_exit_decisions table was empty (0 rows) because writes only happened when
a user opened the S6 panel. The autoloop writes all 8 exit/hold signals per bar
per open trade, so hit-rates accumulate from real sessions.

Tests:
1. Flag OFF → 0 writes (byte-identical)
2. Flag ON → calls record() for each signal + hold signals
3. Dedup: same trade×bar_ts → only one set of writes
4. Advisory: zero calls to write_exit / _emit_modify_stop
5. No active trade → safe (no crash)
"""
import os
import types
from unittest.mock import patch, MagicMock

import pytest


def _mk_trade(*, tid=600, direction="LONG", entry_price=7460.0, stop=7444.0,
              t1=7476.0, state="FILLED", mode="live"):
    t = types.SimpleNamespace()
    t.id = tid
    t.direction = direction
    t.entry_price = entry_price
    t.stop = stop
    t.t1 = t1
    t.t2 = 7492.0
    t.t3 = None
    t.state = state
    t.mode = mode
    t.t1_hit_ts = None
    t.contracts = 2
    t.quality = {"contracts": 2}
    return t


def _mk_detector():
    """Construct a minimal BarLevelDetector for testing the journal method."""
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    det = BarLevelDetector.__new__(BarLevelDetector)
    det._tm = MagicMock()
    det._gateway = None
    det._bars_processed = 0
    det._last_bar_ts_processed = ""
    return det


# ── Test 1: flag OFF → no writes ─────────────────────────────────────────────

def test_flag_off_no_writes(monkeypatch):
    """SYSTEM6_JOURNAL_AUTOLOOP_V1 unset → zero journal writes."""
    monkeypatch.delenv("SYSTEM6_JOURNAL_AUTOLOOP_V1", raising=False)
    det = _mk_detector()
    trade = _mk_trade()

    with patch("backend.v9.systems.system6_journal.record") as mock_rec:
        det._system6_journal_autoloop(trade, "2026-07-27T16:30")
        mock_rec.assert_not_called()


# ── Test 2: flag ON → writes signals ─────────────────────────────────────────

def test_flag_on_writes_signals(monkeypatch):
    """With flag ON + SYSTEM6_EXIT_JOURNAL=1, record() is called for each signal."""
    monkeypatch.setenv("SYSTEM6_JOURNAL_AUTOLOOP_V1", "1")
    monkeypatch.setenv("SYSTEM6_EXIT_JOURNAL", "1")
    det = _mk_detector()
    trade = _mk_trade()

    # Mock DB reads to return minimal bars
    bars_data = [
        {"high": 7465, "low": 7455, "close": 7462},
        {"high": 7468, "low": 7458, "close": 7466},
        {"high": 7470, "low": 7460, "close": 7468},
        {"high": 7472, "low": 7462, "close": 7470},
    ]

    def fake_read_all(sql, params):
        if "v9_bars_5min_woodies" in sql:
            return bars_data
        if "v9_trades" in sql:
            return []
        if "v9_bars_cumulative_delta" in sql:
            return []
        return []

    with patch("backend.v9.systems.system6_journal.record") as mock_rec, \
         patch("backend.v9.db.read.read_all", side_effect=fake_read_all):
        det._system6_journal_autoloop(trade, "2026-07-27T16:35")

    # Should have called record multiple times (exit signals + hold signals)
    assert mock_rec.call_count >= 5, f"Expected ≥5 record calls, got {mock_rec.call_count}"
    # Check the records are for the right trade
    for call in mock_rec.call_args_list:
        rec = call[0][0]
        assert rec["trade_id"] == 600
        assert rec["decided_by"] == "auto_loop"
        assert rec["decision"] == "OBSERVED"


# ── Test 3: dedup — same bar_ts → no second write ────────────────────────────

def test_dedup_same_bar(monkeypatch):
    """Same trade×bar_ts_key → second call skips (dedup)."""
    monkeypatch.setenv("SYSTEM6_JOURNAL_AUTOLOOP_V1", "1")
    monkeypatch.setenv("SYSTEM6_EXIT_JOURNAL", "1")
    det = _mk_detector()
    trade = _mk_trade()

    bars_data = [
        {"high": 7465, "low": 7455, "close": 7462},
        {"high": 7468, "low": 7458, "close": 7466},
        {"high": 7470, "low": 7460, "close": 7468},
    ]

    def fake_read_all(sql, params):
        if "v9_bars_5min_woodies" in sql:
            return bars_data
        return []

    with patch("backend.v9.systems.system6_journal.record") as mock_rec, \
         patch("backend.v9.db.read.read_all", side_effect=fake_read_all):
        det._system6_journal_autoloop(trade, "2026-07-27T16:35")
        first_count = mock_rec.call_count

        det._system6_journal_autoloop(trade, "2026-07-27T16:35")
        assert mock_rec.call_count == first_count, "Dedup failed: second call wrote more rows"


# ── Test 4: advisory only — no trading calls ─────────────────────────────────

def test_advisory_no_trading_calls(monkeypatch):
    """The autoloop NEVER calls write_exit, _emit_modify_stop, or any trade op."""
    monkeypatch.setenv("SYSTEM6_JOURNAL_AUTOLOOP_V1", "1")
    monkeypatch.setenv("SYSTEM6_EXIT_JOURNAL", "1")
    det = _mk_detector()
    trade = _mk_trade()

    bars_data = [{"high": 7465, "low": 7455, "close": 7462}] * 4

    def fake_read_all(sql, params):
        if "v9_bars_5min_woodies" in sql:
            return bars_data
        return []

    with patch("backend.v9.systems.system6_journal.record"), \
         patch("backend.v9.db.read.read_all", side_effect=fake_read_all):
        det._system6_journal_autoloop(trade, "2026-07-27T16:40")

    # The TM should never have been called for trading operations
    det._tm._emit_modify_stop.assert_not_called()
    det._tm.close_trade.assert_not_called()


# ── Test 5: no crash without SYSTEM6_EXIT_JOURNAL ────────────────────────────

def test_journal_disabled_no_crash(monkeypatch):
    """SYSTEM6_JOURNAL_AUTOLOOP_V1=1 but SYSTEM6_EXIT_JOURNAL unset → record() returns None, no crash."""
    monkeypatch.setenv("SYSTEM6_JOURNAL_AUTOLOOP_V1", "1")
    monkeypatch.delenv("SYSTEM6_EXIT_JOURNAL", raising=False)
    det = _mk_detector()
    trade = _mk_trade()

    # Should not crash even without the journal flag
    det._system6_journal_autoloop(trade, "2026-07-27T16:45")
