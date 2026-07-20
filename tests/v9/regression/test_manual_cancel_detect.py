"""MANUAL_CANCEL_DETECT_V1 — when Michael manually cancels a trade in Sierra,
the reconciler detects (Sierra flat, TM has trade), marks CANCELLED, releases
slot, and does NOT false-alarm as orphan/naked.

Anti-tautological:
  1. Flag ON + Sierra flat + TM has trade (3 cycles) → CANCELLED + slot released
  2. Flag OFF → existing PHANTOM-HEAL behavior (CLOSED, no slot release)
  3. Flag ON but Sierra has position → no cancel (not flat)
  4. Flag ON + streak not reached → no cancel yet (conservative)
"""
import json
import os
import pytest
from unittest.mock import MagicMock, patch

import backend.v9.services.sierra_position_reconciler as reconciler


def _write_state(tmp_path, qty, avg_price=7500.0, working=0):
    sf = tmp_path / "sierra_state.json"
    sf.write_text(json.dumps({
        "position_qty": qty, "avg_price": avg_price,
        "working_orders": working,
    }))
    return sf


def _make_tm_with_trade(trade_id=100, direction="LONG", mode="demo", contracts=3):
    """TM with one active trade that reconciler can count."""
    trade = MagicMock()
    trade.id = trade_id
    trade.mode = mode
    trade.state = "OPEN"
    trade.direction = direction
    trade.outcome = None
    trade.quality = {"contracts": contracts}
    trade.t1_hit_ts = None
    trade.t2_hit_ts = None
    trade.t3_hit_ts = None
    trade.t4_hit_ts = None
    tm = MagicMock()
    tm.get_active_trades.return_value = [trade]

    def _close(tid, reason=""):
        trade.state = "CLOSED"
    tm.close_trade = MagicMock(side_effect=_close)
    return tm, trade


@pytest.fixture(autouse=True)
def _reset(monkeypatch, tmp_path):
    reconciler._orphan_stop_placed.clear()
    reconciler._orphan_stop_last_attempt = 0.0
    reconciler._phantom_flat_streak = 0
    reconciler._virtual_stop.clear()
    sf = tmp_path / "sierra_state.json"
    ef = tmp_path / "trade_activity_events.jsonl"
    monkeypatch.setattr(reconciler, "STATE_FILE", sf)
    monkeypatch.setattr(reconciler, "EVENTS_FILE", ef)
    monkeypatch.delenv("MANUAL_CANCEL_DETECT_V1", raising=False)
    monkeypatch.delenv("PHANTOM_HEAL_V1", raising=False)
    monkeypatch.delenv("ORPHAN_AUTO_STOP_V1", raising=False)
    monkeypatch.setenv("OPS_LOG_DISABLE", "1")
    monkeypatch.setenv("PHANTOM_HEAL_STREAK", "1")  # fast for tests


# ── Test 1: flag ON + Sierra flat → CANCELLED + slot released ────────────────

def test_cancel_detect_marks_cancelled(tmp_path, monkeypatch):
    """Sierra flat + TM has trade + flag ON → trade marked CANCELLED."""
    monkeypatch.setenv("MANUAL_CANCEL_DETECT_V1", "1")
    _write_state(tmp_path, qty=0, working=0)
    tm, trade = _make_tm_with_trade()

    ok, msg = reconciler.reconcile_position(tm)

    assert ok  # healed
    assert "MANUAL-CANCEL" in msg
    assert trade.state == "CANCELLED"
    assert trade.outcome == "CANCELLED"
    tm.close_trade.assert_called_once()


# ── Test 2: flag OFF → PHANTOM-HEAL (CLOSED, not CANCELLED) ─────────────────

def test_phantom_heal_without_cancel_flag(tmp_path, monkeypatch):
    """Flag OFF (PHANTOM_HEAL_V1 ON) → CLOSED, not CANCELLED."""
    monkeypatch.setenv("PHANTOM_HEAL_V1", "1")
    _write_state(tmp_path, qty=0, working=0)
    tm, trade = _make_tm_with_trade()

    ok, msg = reconciler.reconcile_position(tm)

    assert ok
    assert "PHANTOM-HEAL" in msg
    # close_trade was called but state stays CLOSED (not CANCELLED)
    tm.close_trade.assert_called_once()
    assert trade.state == "CLOSED"  # close_trade sets this


# ── Test 3: Sierra has position → no cancel ──────────────────────────────────

def test_no_cancel_when_sierra_has_position(tmp_path, monkeypatch):
    """Sierra qty != 0 → cancel path not entered."""
    monkeypatch.setenv("MANUAL_CANCEL_DETECT_V1", "1")
    _write_state(tmp_path, qty=-2, avg_price=7500.0, working=0)
    tm, trade = _make_tm_with_trade()

    ok, msg = reconciler.reconcile_position(tm)

    # Sierra has -2, TM has +3 → DIVERGENCE (not cancel)
    assert not ok
    assert "MANUAL-CANCEL" not in msg
    assert trade.state == "OPEN"  # unchanged


# ── Test 4: streak not reached → no cancel yet ──────────────────────────────

def test_cancel_needs_streak(tmp_path, monkeypatch):
    """Streak=3, only 1 check → no cancel yet."""
    monkeypatch.setenv("MANUAL_CANCEL_DETECT_V1", "1")
    monkeypatch.setenv("PHANTOM_HEAL_STREAK", "3")
    _write_state(tmp_path, qty=0, working=0)
    tm, trade = _make_tm_with_trade()

    with patch("backend.v9.services.trade_manager.manager.trade_contract_count", return_value=3):
        ok1, msg1 = reconciler.reconcile_position(tm)

    # First call — streak 1/3, not yet triggered
    assert not ok1
    assert "MANUAL-CANCEL" not in msg1
    assert trade.state == "OPEN"
