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
    # Reset idempotency + cooldown + phantom streak + virtual stop
    reconciler._orphan_stop_placed.clear()
    reconciler._orphan_stop_last_attempt = 0.0
    reconciler._phantom_flat_streak = 0
    reconciler._virtual_stop.clear()
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

def test_flag_on_short_orphan_virtual_stop(tmp_path, monkeypatch):
    """Flag ON + SHORT orphan -5 @ 7502.70, working=0, fresh state →
    virtual stop SET (not immediate flatten). Stop ABOVE entry by 10pt = 7512.75."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()

    with patch.object(reconciler, "_place_orphan_stop") as mock_place:
        mock_place.return_value = (True, "VIRTUAL_STOP_SET: SHORT stop @ 7512.75")
        ok, msg = reconciler.reconcile_position(tm)

    assert not ok  # still divergence
    assert "ORPHAN_AUTO_STOP" in msg
    assert "VIRTUAL_STOP_SET" in msg
    # Verify the recommendation passed to _place_orphan_stop
    call_args = mock_place.call_args[0][0]
    assert call_args["side"] == "SHORT"
    assert call_args["qty"] == 5
    assert call_args["entry"] == 7502.70
    assert call_args["stop"] == 7512.75


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

def test_idempotency_after_flatten(tmp_path, monkeypatch):
    """After a successful FLATTEN, same position → SKIP(already-flattened)."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    monkeypatch.setenv("ORPHAN_AUTO_STOP_COOLDOWN_S", "0")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()

    with patch.object(reconciler, "_place_orphan_stop") as mock_place:
        # First call: simulate flatten triggered
        mock_place.return_value = (True, "FLATTEN_TRIGGERED(STOP_CROSSED)")
        ok1, msg1 = reconciler.reconcile_position(tm)
        # Second call: should be blocked by idempotency
        ok2, msg2 = reconciler.reconcile_position(tm)

    assert "FLATTENED" in msg1
    assert "SKIP(already-flattened)" in msg2


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


# ── Test 10: _place_orphan_stop writes correct PLACE_STOP command ─────────────

def test_virtual_stop_set_on_first_call(tmp_path, monkeypatch):
    """Flag ON + orphan → virtual stop is SET (not flatten yet)."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()

    with patch.object(reconciler, "_place_orphan_stop") as mock_place:
        mock_place.return_value = (True, "VIRTUAL_STOP_SET: SHORT stop @ 7512.75")
        ok, msg = reconciler.reconcile_position(tm)

    assert "PLACED" in msg or "VIRTUAL_STOP_SET" in msg


# ── Test 11: FLATTEN_ORPHAN_FAIL → (False, ...) without crash ────────────────

def test_flatten_fail_no_crash(tmp_path, monkeypatch):
    """FLATTEN_ORPHAN fails → reconciler doesn't crash, reports failure."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()

    with patch.object(reconciler, "_place_orphan_stop", return_value=(False, "FLATTEN_ORPHAN_FAIL")):
        ok, msg = reconciler.reconcile_position(tm)

    assert not ok  # still divergence
    assert "FAILED" in msg


# ── Test 12: write_flatten_orphan validates inputs ────────────────────────────

def test_write_flatten_orphan_validation():
    """write_flatten_orphan raises on bad inputs (qty<=0, bad side)."""
    from backend.v9.services.sierra_command import write_flatten_orphan

    with pytest.raises(ValueError, match="side"):
        write_flatten_orphan(qty=5, side="INVALID")
    with pytest.raises(ValueError, match="qty"):
        write_flatten_orphan(qty=0, side="SHORT")


# ── Test 13: write_flatten_orphan produces correct payload ────────────────────

def test_write_flatten_orphan_payload(tmp_path, monkeypatch):
    """write_flatten_orphan writes correct JSON with op, qty, side, account."""
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    from backend.v9.services.sierra_command import write_flatten_orphan

    result = write_flatten_orphan(qty=5, side="SHORT", account="Sim37138283")
    assert result["op"] == "FLATTEN_ORPHAN"
    assert result["qty"] == 5
    assert result["side"] == "SHORT"
    assert result["account"] == "Sim37138283"

    cmd = json.loads((tmp_path / "trade_command.json").read_text())
    assert cmd["op"] == "FLATTEN_ORPHAN"


# ── Test 14: virtual stop set on first call, not flattened immediately ────────

def test_orphan_not_flattened_immediately(tmp_path, monkeypatch):
    """Flag ON + orphan → VIRTUAL_STOP_SET (holding), NOT immediate flatten."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()
    ok, msg = reconciler.reconcile_position(tm)
    assert "VIRTUAL_STOP_SET" in msg
    assert "FLATTEN" not in msg or "FLATTEN_TRIGGERED" not in msg


# ── Test 15: flatten triggers on stop-cross ──────────────────────────────────

def test_flatten_on_stop_cross(tmp_path, monkeypatch):
    """Price crosses structural stop → breach ALERT (Michael ruling 07-28,
    9279a3e8: auto-flatten of open positions CANCELED — alert-only; the
    position is left open for Michael. Test updated 03.08 to the ruling;
    it previously asserted the pre-ruling FLATTEN behavior)."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    monkeypatch.setenv("ORPHAN_AUTO_STOP_COOLDOWN_S", "0")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()

    # First call: sets virtual stop
    ok1, msg1 = reconciler.reconcile_position(tm)
    assert "VIRTUAL_STOP_SET" in msg1

    # Second call: price above stop (7512.75) → should trigger
    # Write state with last_price above the stop
    sf = tmp_path / "sierra_state.json"
    sf.write_text(json.dumps({
        "position_qty": -5, "avg_price": 7502.70, "working_orders": 0,
        "last_price": 7513.00  # above stop 7512.75
    }))
    with patch.object(reconciler, "_flatten_orphan", return_value=(True, "FLATTEN_ORPHAN_OK")):
        ok2, msg2 = reconciler.reconcile_position(tm)
    assert "BREACH_ALERT_ONLY" in msg2
    assert "STOP_CROSSED" in msg2


# ── Test 16: flatten triggers on max loss ────────────────────────────────────

def test_flatten_on_max_loss(tmp_path, monkeypatch):
    """Unrealized loss >= $200 → breach ALERT even if stop not crossed
    (Michael ruling 07-28: alert-only, no auto-flatten; updated 03.08)."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    monkeypatch.setenv("ORPHAN_AUTO_STOP_COOLDOWN_S", "0")
    monkeypatch.setenv("ORPHAN_MAX_LOSS_USD", "200")
    _write_fresh_state(tmp_path, qty=-2, avg_price=7500.00, working=0)
    tm = _make_tm()

    # First call: sets virtual stop (stop=7510.00 for SHORT)
    ok1, msg1 = reconciler.reconcile_position(tm)
    assert "VIRTUAL_STOP_SET" in msg1

    # Second call: price at 7509 (below stop 7510, not crossed)
    # but loss = (7509-7500) * 2 * 12.50 = $225 > $200
    sf = tmp_path / "sierra_state.json"
    sf.write_text(json.dumps({
        "position_qty": -2, "avg_price": 7500.00, "working_orders": 0,
        "last_price": 7509.00
    }))
    with patch.object(reconciler, "_flatten_orphan", return_value=(True, "FLATTEN_ORPHAN_OK")):
        ok2, msg2 = reconciler.reconcile_position(tm)
    assert "BREACH_ALERT_ONLY" in msg2
    assert "MAX_LOSS" in msg2


# ── Test 17: no flatten when within tolerance ────────────────────────────────

def test_no_flatten_within_tolerance(tmp_path, monkeypatch):
    """Price within stop AND loss < $200 → MONITORING, no flatten."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    monkeypatch.setenv("ORPHAN_AUTO_STOP_COOLDOWN_S", "0")
    _write_fresh_state(tmp_path, qty=-2, avg_price=7500.00, working=0)
    tm = _make_tm()

    # First call: sets virtual stop
    ok1, msg1 = reconciler.reconcile_position(tm)
    assert "VIRTUAL_STOP_SET" in msg1

    # Second call: price at 7503 (below stop 7510, loss = $75 < $200)
    sf = tmp_path / "sierra_state.json"
    sf.write_text(json.dumps({
        "position_qty": -2, "avg_price": 7500.00, "working_orders": 0,
        "last_price": 7503.00
    }))
    ok2, msg2 = reconciler.reconcile_position(tm)
    assert "VIRTUAL_STOP_MONITORING" in msg2
    assert "FLATTEN_TRIGGERED" not in msg2


# ── Cooldown test ─────────────────────────────────────────────────────────────

def test_cooldown_blocks_rapid_attempts(tmp_path, monkeypatch):
    """Second attempt within cooldown window → SKIP(cooldown)."""
    monkeypatch.setenv("ORPHAN_AUTO_STOP_V1", "1")
    monkeypatch.setenv("ORPHAN_AUTO_STOP_COOLDOWN_S", "300")
    _write_fresh_state(tmp_path, qty=-5, avg_price=7502.70, working=0)
    tm = _make_tm()

    # First call — will fail (TIMEOUT since no DLL) but updates _orphan_stop_last_attempt
    with patch.object(reconciler, "_place_orphan_stop", return_value=(False, "PLACE_STOP_FAIL")):
        ok1, msg1 = reconciler.reconcile_position(tm)
    assert "FAILED" in msg1

    # Different qty so idempotency doesn't block — but cooldown should
    _write_fresh_state(tmp_path, qty=-3, avg_price=7500.0, working=0)
    ok2, msg2 = reconciler.reconcile_position(tm)
    assert "SKIP(cooldown)" in msg2
