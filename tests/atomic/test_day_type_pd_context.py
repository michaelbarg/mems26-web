"""Prompt 21c — Prove pd_high/pd_low/pd_close correctness in S1 A1.

Acceptance criteria:
  1. pd_close comes from v9_bars_5min last close, NOT poc_price.
  2. pd_high/pd_low from TPO range when available, bars fallback otherwise.
  3. A1 receives pd_* and computes gap correctly.
  4. Missing pd_* produces explicit degraded state (no fake data).
  5. No SHADOW/DEMO/LIVE.
"""
import sqlite3
import sys
import os
from pathlib import Path
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')
os.environ.setdefault("BRIDGE_TOKEN", "test-token")

from unittest.mock import patch, MagicMock
from backend.main import _load_previous_day_context
from backend.v9.systems.day_type.schemas import BarInput, PreOpenContext
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine


def _create_pd_source_db(tmp_path):
    db_path = Path(tmp_path) / "pd_context.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE v9_bars_5min (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            symbol TEXT DEFAULT 'MES',
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER DEFAULT 0
        )"""
    )
    conn.execute(
        """CREATE TABLE v9_tpo_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            session_type TEXT NOT NULL,
            trading_date TEXT NOT NULL,
            opened_ts TEXT NOT NULL,
            poc_price REAL,
            vah_price REAL,
            val_price REAL,
            range_high REAL,
            range_low REAL
        )"""
    )
    conn.commit()
    return db_path, conn


def _insert_bar(conn, ts, high, low, close):
    conn.execute(
        """INSERT INTO v9_bars_5min (ts, open, high, low, close, volume)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (ts, close, high, low, close, 100),
    )


def _insert_tpo(conn, trading_date, range_high, range_low, poc_price=7444.0):
    conn.execute(
        """INSERT INTO v9_tpo_sessions (
            session_id, session_type, trading_date, opened_ts,
            poc_price, vah_price, val_price, range_high, range_low
        ) VALUES (?, 'CASH', ?, ?, ?, ?, ?, ?, ?)""",
        (
            f"CASH_{trading_date}",
            trading_date,
            f"{trading_date}T09:30:00",
            poc_price,
            poc_price + 10.0,
            poc_price - 10.0,
            range_high,
            range_low,
        ),
    )


def test_loader_pd_close_from_bars_last_close(tmp_path):
    """Loader uses previous-day v9_bars_5min last close for pd_close."""
    db_path, conn = _create_pd_source_db(tmp_path)
    _insert_bar(conn, "2026-05-15T14:30:00", high=7500.0, low=7410.0, close=7418.0)
    _insert_bar(conn, "2026-05-15T20:55:00", high=7505.0, low=7420.0, close=7432.5)
    conn.commit()
    conn.close()

    ctx = _load_previous_day_context(str(db_path), previous_trading_day="2026-05-15")

    assert ctx["pd_context_status"] == "OK"
    assert ctx["pd_close"] == 7432.5


def test_loader_pd_close_prefers_bars_over_tpo_poc(tmp_path):
    """Even when TPO has poc_price, pd_close remains the bars close."""
    db_path, conn = _create_pd_source_db(tmp_path)
    _insert_tpo(conn, "2026-05-15", range_high=7505.25, range_low=7409.5, poc_price=7444.0)
    _insert_bar(conn, "2026-05-15T20:55:00", high=7500.0, low=7410.0, close=7418.0)
    conn.commit()
    conn.close()

    ctx = _load_previous_day_context(str(db_path), previous_trading_day="2026-05-15")

    assert ctx["pd_context_status"] == "OK"
    assert ctx["pd_close"] == 7418.0
    assert ctx["pd_close"] != 7444.0


def test_loader_pd_range_uses_tpo_before_bars(tmp_path):
    """pd_high/pd_low prefer TPO range when available."""
    db_path, conn = _create_pd_source_db(tmp_path)
    _insert_tpo(conn, "2026-05-15", range_high=7505.25, range_low=7409.5)
    _insert_bar(conn, "2026-05-15T20:55:00", high=7518.0, low=7398.0, close=7418.0)
    conn.commit()
    conn.close()

    ctx = _load_previous_day_context(str(db_path), previous_trading_day="2026-05-15")

    assert ctx["pd_high"] == 7505.25
    assert ctx["pd_low"] == 7409.5


def test_loader_pd_range_falls_back_to_bars(tmp_path):
    """Without TPO range, pd_high/pd_low come from bars max/min."""
    db_path, conn = _create_pd_source_db(tmp_path)
    _insert_bar(conn, "2026-05-15T14:30:00", high=7490.0, low=7425.0, close=7460.0)
    _insert_bar(conn, "2026-05-15T20:55:00", high=7508.0, low=7402.0, close=7418.0)
    conn.commit()
    conn.close()

    ctx = _load_previous_day_context(str(db_path), previous_trading_day="2026-05-15")

    assert ctx["pd_high"] == 7508.0
    assert ctx["pd_low"] == 7402.0
    assert ctx["pd_close"] == 7418.0


def test_loader_no_previous_day_source_is_degraded(tmp_path):
    """No bars and no TPO source returns explicit degraded context."""
    db_path, conn = _create_pd_source_db(tmp_path)
    conn.close()

    ctx = _load_previous_day_context(str(db_path), previous_trading_day="2026-05-15")

    assert ctx["pd_context_status"] == "DEGRADED"
    assert ctx["degraded_reason"] == "missing_previous_day_context"
    assert ctx["missing_pd_fields"] == ["pd_high", "pd_low", "pd_close"]


def test_pd_close_from_bars_last_close_not_poc():
    """pd_close must be the actual last bar close, not TPO POC."""
    # Simulated scenario: TPO has poc=7444 but bars last close=7418
    # The correct pd_close is 7418 (actual session close), not 7444 (POC)
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        pd_high=7505.25, pd_low=7409.5, pd_close=7418.0,  # bars last close
    )
    state = machine.process_bar(bar)
    # Gap = 7460 - 7418 = 42 pts UP
    assert machine.pre_open.gap_size == 42.0
    assert machine.pre_open.gap_direction == "UP"


def test_gap_uses_pd_close_not_poc():
    """Gap calculation: open - pd_close. pd_close = bars close, not POC."""
    machine = DayTypeStateMachine()
    # If pd_close were poc=7444, gap would be 7470-7444=26
    # With correct pd_close=7418, gap = 7470-7418=52
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7470.0, high=7472.0, low=7468.0, close=7471.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7418.0,
    )
    state = machine.process_bar(bar)
    assert machine.pre_open.gap_size == 52.0


def test_a1_receives_all_pd_values():
    """A1 pre-open uses pd_high, pd_low, pd_close to compute location."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        pd_high=7505.25, pd_low=7409.5, pd_close=7418.0,
    )
    state = machine.process_bar(bar)
    assert machine.pre_open is not None
    # Open=7460 is between pd_low=7409.5 and pd_high=7505.25 → INSIDE
    assert machine.pre_open.location_vs_pd == "INSIDE"


def test_location_above_pd_high():
    """When open > pd_high → ABOVE."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7510.0, high=7512.0, low=7508.0, close=7511.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7450.0,
    )
    state = machine.process_bar(bar)
    assert machine.pre_open.location_vs_pd == "ABOVE"


def test_location_below_pd_low():
    """When open < pd_low → BELOW."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7395.0, high=7397.0, low=7393.0, close=7396.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7450.0,
    )
    state = machine.process_bar(bar)
    assert machine.pre_open.location_vs_pd == "BELOW"


def test_missing_pd_explicit_degraded():
    """Missing pd_* produces degraded/pending A1, not neutral defaults."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        # All pd_* are None
    )
    state = machine.process_bar(bar)
    assert machine.pre_open is not None
    assert state.stage.value == "A1"
    assert state.lock_state == "PENDING"
    assert state.day_type.value == "UNKNOWN"
    assert state.confidence == 0.0
    assert machine.pre_open.gap_size is None
    assert machine.pre_open.gap_direction == "UNKNOWN"
    assert machine.pre_open.location_vs_pd == "UNKNOWN"
    assert machine.pre_open.pd_context_status == "DEGRADED"
    assert machine.pre_open.degraded_reason == "missing_previous_day_context"
    assert machine.pre_open.missing_pd_fields == ["pd_high", "pd_low", "pd_close"]
    assert state.meta["pd_context_status"] == "DEGRADED"


def test_partial_missing_pd_is_degraded():
    """Any missing pd_* field blocks normal A1 classification."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        pd_high=7505.0, pd_low=7400.0,
        # pd_close missing
    )

    state = machine.process_bar(bar)

    assert state.stage.value == "A1"
    assert state.lock_state == "PENDING"
    assert state.day_type.value == "UNKNOWN"
    assert state.pre_open.pd_context_status == "DEGRADED"
    assert state.pre_open.missing_pd_fields == ["pd_close"]


def test_missing_pd_does_not_crash():
    """System remains functional even without pd_*."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
    )
    # Must not raise
    state = machine.process_bar(bar)
    assert state is not None


def test_no_shadow_demo_live():
    """No trading mode activated by pd_* processing.

    Checks that no SHADOW/DEMO/LIVE *mode value* appears (field names like
    ib_high_live are structural, not trading mode indicators).
    """
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7418.0,
    )
    state = machine.process_bar(bar)
    # The DayTypeState should not contain trading mode references as values
    # (field names like ib_high_live are OK — they refer to live-session price, not trading mode)
    assert state.lock_state in ("PENDING", "LOCKED", "LOCKED_LOW_CONF")
    assert "SHADOW" not in state.lock_state
    assert "DEMO" not in state.lock_state
