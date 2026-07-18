"""ORPHAN_AUTO_STOP_V1 — anti-tautological tests per CC_HANDOFF_CONTRACT.

Michael ruling 2026-07-17: a naked orphan position must get a protective stop
when the flag is ON and all safety conditions hold. These tests verify:
  1. Flag OFF → no auto-stop, alert identical to pre-V1
  2. Flag ON + short orphan → stop placed above at correct price
  3. Flag ON + long orphan → stop placed below
  4. Working orders > 0 → no auto-stop (already protected)
  5. Stale state source → no auto-stop
  6. Qty > MAX_QTY → no auto-stop
  7. Idempotency: two calls same position → only one attempt
  8. Placement failure → reconciler doesn't crash, alert still sent
  9. No regression: TM and Sierra agree → no orphan logic triggered

DLL investigation (2026-07-18): no PLACE_STOP op exists — _place_orphan_stop()
always returns (False, reason). Tests verify the gating logic; actual placement
is blocked until a DLL op is built.
"""
import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

import backend.v9.services.sierra_position_reconciler as reconciler


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_fresh_state(tmp_path, qty, avg_price=7502.70, working=0):
    """Write a fresh sierra_state.json with the given position."""
    state = {
        "position_qty": qty,
        "avg_price": avg_price,
        "working_orders": working,
    }
    sf = tmp_path / "sierra_state.json"
    sf.write_text(json.dumps(state))
    return sf


def _make_tm(active_trades=None):
    """Minimal TM stub — returns no active trades by default (TM=0)."""
    tm = MagicMock()
    tm.get_active_trades.return_value = active_trades or []
    return tm


@pytest.fixture(autouse=True)
def _reset_module_state(monkeypatch, tmp_path):
    """Reset module-level state and point to tmp state file each test."""
    # Reset idempotency + cooldown + phantom streak
    reconciler._orphan_stop_placed.clear()
    reconciler._orphan_stop_last_attempt = 0.0
    reconciler._phantom_flat_streak = 0
    # Point state/events files to tmp
    sf = tmp_path / "sierra_state.json"
    ef = tmp_path / "trade_activity_events.jsonl"
    monkeypatch.setattr(reconciler, "STATE_FILE", sf)
    monkeypatch.setattr(reconciler, "EVENTS_FILE", ef)
    # Clean env — flag OFF by default
    monkeypatch.delenv("ORPHAN_AUTO_STOP_V1", raising=False)
    monkeypatch.delenv("ORPHAN_AUTO_STOP_MAX_QTY", raising=False)
    monkeypatch.delenv("ORPHAN_AUTO_STOP_COOLDOWN_S", raising=False)
    monkeypatch.delenv("ORPHAN_STOP_POINTS", raising=False)
    monkeypatch.delenv("PHANTOM_HEAL_V1", raising=False)
    # Suppress phone alerts in tests
    monkeypatch.setenv("OPS_LOG_DISABLE", "1")


# ── Test 1: flag OFF + orphan → NO auto-stop, alert like today ────────────────

def test_flag_off_orphan_alert_only(tmp_path):
    """Flag OFF + naked orphan → existing alert-only path, no auto-stop attempted.
    Pin: the exact pre-V1 message substring must appear."""
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()
    ok, msg = reconciler.reconcile_position(tm)
    assert not ok, "divergence should report not-ok"
    assert "NAKED ORPHAN SHORT 5c @ 7502.7" in msg
    assert "PLACE PROTECTIVE STOP @ 7512.75 (10pt)" in msg
    # Must NOT contain auto-stop markers
    assert "ORPHAN_AUTO_STOP" not in msg


# ── Test 2: flag ON + short orphan → stop above at correct price ──────────────

def test_flag_on_short_orphan_stop_above(tmp_path, monkeypatch):
    """Flag ON + SHORT orphan -5 @ 7502.70, working=0, fresh state →
    auto-stop attempted. Stop should be ABOVE entry by 10pt = 7512.75, qty=5."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()

    with patch.object(reconciler, "_place_orphan_stop") as mock_place:
        mock_place.return_value = (True, "placed")
        ok, msg = reconciler.reconcile_position(tm)

    assert not ok  # still divergence
    assert "ORPHAN_AUTO_STOP" in msg
    assert "PLACED" in msg
    # Verify the recommendation passed to _place_orphan_stop
    call_args = mock_place.call_args[0][0]
    assert call_args["side"] == "SHORT"
    assert call_args["qty"] == 5
    assert call_args["entry"] == 7502.70
    assert call_args["stop"] == 7512.75
    assert call_args["points"] == 10.0


# ── Test 3: flag ON + long orphan → stop below ───────────────────────────────

def test_flag_on_long_orphan_stop_below(tmp_path, monkeypatch):
    """LONG orphan +3 @ 7600.0 → stop BELOW at 7590.0."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    _write_fresh_state(tmp_path, qty=3, avg_price=7600.0, working=0)
    tm = _make_tm()

    with patch.object(reconciler, "_place_orphan_stop") as mock_place:
        mock_place.return_value = (True, "placed")
        ok, msg = reconciler.reconcile_position(tm)

    call_args = mock_place.call_args[0][0]
    assert call_args["side"] == "LONG"
    assert call_args["qty"] == 3
    assert call_args["stop"] == 7590.0


# ── Test 4: working_orders > 0 → no auto-stop (already protected) ────────────

def test_working_orders_skip(tmp_path, monkeypatch):
    """Orphan with working orders > 0 → SKIP(protected), no placement."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=2)
    tm = _make_tm()
    ok, msg = reconciler.reconcile_position(tm)
    assert "SKIP(protected)" in msg
    assert "2 working orders" in msg


# ── Test 5: stale state (events source) → no auto-stop ───────────────────────

def test_stale_source_skip(tmp_path, monkeypatch):
    """State file stale (>10s) → src="events", auto-stop refuses."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    # Write state file but make it old
    sf = _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    old_time = time.time() - 30  # 30 seconds ago
    os.utime(sf, (old_time, old_time))
    # Also write an events file so sierra_qty is still found
    ef = tmp_path / "trade_activity_events.jsonl"
    ef.write_text(json.dumps({"type": "POSITION_CHANGE", "new_qty": -5}) + "\n")
    tm = _make_tm()
    ok, msg = reconciler.reconcile_position(tm)
    assert "SKIP(stale-source)" in msg


# ── Test 6: qty > MAX_QTY → no auto-stop ─────────────────────────────────────

def test_qty_exceeds_max(tmp_path, monkeypatch):
    """qty=50 > default MAX_QTY=10 → SKIP(qty-too-large)."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    _write_fresh_state(tmp_path, qty=-50, avg_price=7502.70, working=0)
    tm = _make_tm()
    ok, msg = reconciler.reconcile_position(tm)
    assert "SKIP(qty-too-large)" in msg


# ── Test 7: idempotency — two calls same position → one attempt ──────────────

def test_idempotency_second_call_skipped(tmp_path, monkeypatch):
    """Two consecutive calls with same (qty, entry) → second is SKIP(already-placed)."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    monkeypatch.setenv("ORPHAN_AUTO_STOP_COOLDOWN_S", "0")  # disable cooldown for this test
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()

    with patch.object(reconciler, "_place_orphan_stop") as mock_place:
        mock_place.return_value = (True, "placed")
        ok1, msg1 = reconciler.reconcile_position(tm)
        ok2, msg2 = reconciler.reconcile_position(tm)

    assert "PLACED" in msg1
    assert "SKIP(already-placed)" in msg2
    assert mock_place.call_count == 1  # only called once


# ── Test 8: placement failure → reconciler doesn't crash, alert still sent ────

def test_placement_exception_no_crash(tmp_path, monkeypatch):
    """_place_orphan_stop raises → reconciler catches, alert still sent."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()

    with patch.object(reconciler, "_place_orphan_stop", side_effect=RuntimeError("DLL crash")):
        ok, msg = reconciler.reconcile_position(tm)

    # Must not crash
    assert not ok  # divergence still reported
    assert "ERROR(placement-exception)" in msg
    assert "DLL crash" in msg


# ── Test 9: no regression — TM and Sierra match → no orphan logic ─────────────

def test_match_no_orphan_logic(tmp_path, monkeypatch):
    """When TM and Sierra agree (both flat), no orphan/auto-stop logic fires."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")  # even with flag ON
    _write_fresh_state(tmp_path, qty=0, avg_price=0, working=0)
    tm = _make_tm()
    ok, msg = reconciler.reconcile_position(tm)
    assert ok
    assert "MATCH" in msg
    assert "ORPHAN" not in msg


# ── Additional: real _place_orphan_stop returns NO_DLL_PATH ──────────────────

def test_real_place_returns_no_dll_path(tmp_path, monkeypatch):
    """Without mocking, the real _place_orphan_stop returns NO_DLL_PATH —
    verifying the stub is honest about the missing DLL op."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()
    ok, msg = reconciler.reconcile_position(tm)
    assert "NO_DLL_PATH" in msg
    assert "PLACE_STOP" in msg  # mentions what's needed


# ── Cooldown test ─────────────────────────────────────────────────────────────

def test_cooldown_blocks_rapid_attempts(tmp_path, monkeypatch):
    """Second attempt within cooldown window → SKIP(cooldown)."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    monkeypatch.setenv("ORPHAN_AUTO_STOP_COOLDOWN_S", "300")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()

    # First call — will fail (NO_DLL_PATH) but updates _orphan_stop_last_attempt
    ok1, msg1 = reconciler.reconcile_position(tm)
    assert "NO_DLL_PATH" in msg1 or "FAILED" in msg1

    # Different qty so idempotency doesn't block — but cooldown should
    _write_fresh_state(tmp_path, qty=-3, avg_price=7500.0, working=0)
    ok2, msg2 = reconciler.reconcile_position(tm)
    assert "SKIP(cooldown)" in msg2
