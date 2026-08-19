"""W3 — NAKED_STOP_SUSPECT false-alarm fix (2026-08-19).

Real incident (08-19 evening, Michael): trades #738/#741/#744/#746 ALL carried
working stops (attached OCO brackets, entry ACK ORDER_SUBMITTED with stop_id),
yet the log filled with thousands of
    [Reconcile] NAKED_STOP_SUSPECT — in position but stop not confirmed
        (last_result=None, age=Nones)                       ← class A
    [Reconcile] ... (last_result='FLATTEN_ACCOUNT_OK', age=1.88s)  ← class B

Roots:
  A. reconcile._read_last_result discarded trade_result.json older than 900s.
     A resting OCO stop produces NO new ACKs, so any quiet position >15 min
     degraded to (None, None) → guaranteed false NAKED on every bar.
  B. FLATTEN_ACCOUNT_OK (intentional MAE-scratch close in progress) is not a
     "stop ok" status → alarm during the scratch-flatten race window.
  C. bar_level_detector._reconcile_live alarmed (CRITICAL + phone) on a single
     check — no 2-consecutive discipline like PROTECTED_QTY_GUARD_V1.

Fixes under test:
  1. _read_last_result(min_ts=entry_epoch) accepts a stale ACK that belongs to
     the CURRENT position's lifetime; still discards pre-entry artifacts (07-15).
  2. reconcile_positions: fresh FLATTEN_ACCOUNT_OK (≤120s) → suppressed.
  3. _reconcile_live: 2 consecutive naked verdicts required before phone push.
"""
import json
import time
import types

import backend.v9.services.reconcile as rc
from backend.v9.services.reconcile import reconcile_positions, _read_last_result


# ── Class B: flatten race ────────────────────────────────────────────────────

def test_fresh_flatten_is_not_naked():
    v = reconcile_positions(
        slot_occupied=True, db_open_ids=[741], tm_in_position=True,
        last_result_status="FLATTEN_ACCOUNT_OK", last_result_age_s=2.0)
    assert v.verdict == rc.IN_POSITION_OK
    assert v.naked_stop_suspect is False
    assert "flatten in progress" in v.detail


def test_stale_flatten_still_alarms():
    """Grace is 120s — an old FLATTEN must not silence a real naked stop."""
    v = reconcile_positions(
        slot_occupied=True, db_open_ids=[741], tm_in_position=True,
        last_result_status="FLATTEN_ACCOUNT_OK", last_result_age_s=600.0)
    assert v.naked_stop_suspect is True


# ── Class A: lifetime-bound staleness ────────────────────────────────────────

def _write_result(tmp_path, ts):
    p = tmp_path / "trade_result.json"
    p.write_text(json.dumps({"status": "ORDER_SUBMITTED", "ts": ts,
                             "parent_id": 1, "stop_id": 2}))
    return p


def test_stale_ack_within_position_lifetime_accepted(tmp_path, monkeypatch):
    now = time.time()
    monkeypatch.setattr(rc, "RESULT_PATH", _write_result(tmp_path, now - 3600))
    status, age = _read_last_result(min_ts=now - 4000)  # entry before ACK
    assert status == "ORDER_SUBMITTED"
    assert age is not None and age > rc._STOP_STALE_S


def test_stale_ack_older_than_entry_discarded(tmp_path, monkeypatch):
    """07-15 protection preserved: yesterday's artifact stays discarded."""
    now = time.time()
    monkeypatch.setattr(rc, "RESULT_PATH", _write_result(tmp_path, now - 3600))
    assert _read_last_result(min_ts=now - 1800) == (None, None)


def test_stale_ack_without_min_ts_discarded(tmp_path, monkeypatch):
    now = time.time()
    monkeypatch.setattr(rc, "RESULT_PATH", _write_result(tmp_path, now - 3600))
    assert _read_last_result() == (None, None)


def test_fresh_ack_unaffected(tmp_path, monkeypatch):
    now = time.time()
    monkeypatch.setattr(rc, "RESULT_PATH", _write_result(tmp_path, now - 5))
    status, _age = _read_last_result()
    assert status == "ORDER_SUBMITTED"


# ── Class C: 2-consecutive before phone ──────────────────────────────────────

def _naked_verdict():
    return rc.ReconcileVerdict(
        verdict=rc.NAKED_STOP_SUSPECT, in_position_belief=True,
        slot_occupied=True, naked_stop_suspect=True, detail="test naked")


def _ok_verdict():
    return rc.ReconcileVerdict(
        verdict=rc.IN_POSITION_OK, in_position_belief=True,
        slot_occupied=True, detail="ok")


def test_reconcile_live_requires_two_consecutive(monkeypatch):
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    import backend.v9.services.phone_alert as pa

    monkeypatch.setenv("RECONCILE_LIVE_V1", "1")
    pushes = []
    monkeypatch.setattr(pa, "push",
                        lambda *a, **k: pushes.append(a) or True)

    fake = types.SimpleNamespace(
        _gateway=types.SimpleNamespace(demo_slot=None, live_slot=object()))

    monkeypatch.setattr(rc, "gather_and_reconcile", lambda gateway=None: _naked_verdict())
    BarLevelDetector._reconcile_live(fake)          # check 1 → no phone yet
    assert pushes == [] and fake._naked_streak == 1
    BarLevelDetector._reconcile_live(fake)          # check 2 → alarm
    assert len(pushes) == 1 and fake._naked_streak == 2

    # a clean verdict resets the streak → next naked is 1/2 again (no push)
    monkeypatch.setattr(rc, "gather_and_reconcile", lambda gateway=None: _ok_verdict())
    BarLevelDetector._reconcile_live(fake)
    assert fake._naked_streak == 0
    monkeypatch.setattr(rc, "gather_and_reconcile", lambda gateway=None: _naked_verdict())
    BarLevelDetector._reconcile_live(fake)
    assert len(pushes) == 1
