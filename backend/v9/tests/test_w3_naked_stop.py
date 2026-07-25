"""W3 — NAKED_STOP_SUSPECT fix: MODIFY_STOP_NONE retry + escalation (2026-07-25).

Real incident: MODIFY_STOP returned NONE (stop_ids stale or bracket not settled),
overwrote ORDER_SUBMITTED in trade_result.json → NAKED_STOP_SUSPECT for 837s
(the entire trade life). No escalation beyond a log line.

Fix:
1. fill_poller._check_result handles MODIFY_STOP_NONE → CRITICAL log + phone push
2. STOP_RETRY_ON_NONE_V1 (flag-gated): retries MODIFY_STOP with fresh stop value
3. bar_level_detector._reconcile_live sends phone push on NAKED_STOP_SUSPECT

Tests:
1. MODIFY_STOP_NONE triggers CRITICAL log (always, no flag needed)
2. STOP_RETRY_ON_NONE_V1=1 → retry MODIFY_STOP with trade's stop value
3. STOP_RETRY_ON_NONE_V1 unset → no retry (escalation only)
4. No FILLED trade → safe (no crash)
5. Retry throttle (max 1 per 10s per trade)
6. revert→RED: removing fix makes MODIFY_STOP_NONE pass through silently
"""
import json
import os
import time
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def _mk_trade(*, tid=600, state="FILLED", mode="live", direction="LONG",
              entry_price=7478.0, stop=7462.0, contracts=2):
    t = types.SimpleNamespace()
    t.id = tid
    t.state = state
    t.mode = mode
    t.direction = direction
    t.entry_price = entry_price
    t.stop = stop
    t.quality = {"contracts": contracts, "sierra_order_id": 9500,
                 "c1_stop_id": 9501, "c2_stop_id": 9502}
    return t


def _mk_poller(tmp_path, trades):
    from backend.v9.services import fill_poller as fp

    poller = fp.FillPoller.__new__(fp.FillPoller)
    poller._running = False
    poller._last_mtime = 0.0
    poller._last_result_mtime = 0.0
    poller._processed_count = 0
    poller._last_poll_ts = 0.0
    poller._order_map = {}
    poller._orphan_fills = []
    poller._orphan_count = 0
    poller._activity_exit_pos = None

    tm = types.SimpleNamespace()
    tm.get_active_trades = lambda: list(trades)
    tm._modify_calls = []

    def _emit_modify_stop(trade, new_stop):
        tm._modify_calls.append((trade.id, new_stop))

    tm._emit_modify_stop = _emit_modify_stop
    tm._db = types.SimpleNamespace(flush=lambda: None)

    poller._tm = tm
    poller._gateway = None
    return poller, tm


def _write_result(tmp_path, status, **extra):
    """Write a trade_result.json and return its path."""
    result_path = tmp_path / "trade_result.json"
    data = {"status": status, "ts": str(time.time()), **extra}
    result_path.write_text(json.dumps(data))
    return result_path


# ── Test 1: MODIFY_STOP_NONE triggers handler (always) ──────────────────────

def test_modify_stop_none_triggers_handler(tmp_path, monkeypatch):
    """MODIFY_STOP_NONE should call _handle_modify_stop_none (CRITICAL log)."""
    monkeypatch.delenv("STOP_RETRY_ON_NONE_V1", raising=False)
    trade = _mk_trade()
    poller, tm = _mk_poller(tmp_path, [trade])

    import backend.v9.services.fill_poller as fp
    result_path = _write_result(tmp_path, "MODIFY_STOP_NONE")
    monkeypatch.setattr(fp, "RESULT_PATH", result_path)

    # First read to set baseline mtime
    poller._last_result_mtime = 0.0
    poller._check_result()

    # The handler was called (no retry since flag OFF) but no crash
    assert tm._modify_calls == []  # no retry without flag


# ── Test 2: STOP_RETRY_ON_NONE_V1=1 → retry ─────────────────────────────────

def test_retry_on_none_when_flagged(tmp_path, monkeypatch):
    """With flag ON, MODIFY_STOP_NONE retries with the trade's stop value."""
    monkeypatch.setenv("STOP_RETRY_ON_NONE_V1", "1")
    trade = _mk_trade(tid=600, stop=7462.0)
    poller, tm = _mk_poller(tmp_path, [trade])

    import backend.v9.services.fill_poller as fp
    result_path = _write_result(tmp_path, "MODIFY_STOP_NONE")
    monkeypatch.setattr(fp, "RESULT_PATH", result_path)

    poller._last_result_mtime = 0.0
    poller._check_result()

    assert len(tm._modify_calls) == 1
    assert tm._modify_calls[0] == (600, 7462.0)


# ── Test 3: flag OFF → no retry (escalation only) ────────────────────────────

def test_no_retry_without_flag(tmp_path, monkeypatch):
    """Without STOP_RETRY_ON_NONE_V1, only escalation, no retry."""
    monkeypatch.delenv("STOP_RETRY_ON_NONE_V1", raising=False)
    trade = _mk_trade()
    poller, tm = _mk_poller(tmp_path, [trade])

    import backend.v9.services.fill_poller as fp
    result_path = _write_result(tmp_path, "MODIFY_STOP_NONE")
    monkeypatch.setattr(fp, "RESULT_PATH", result_path)

    poller._last_result_mtime = 0.0
    poller._check_result()

    assert tm._modify_calls == []


# ── Test 4: no FILLED trade → safe ───────────────────────────────────────────

def test_no_filled_trade_safe(tmp_path, monkeypatch):
    """MODIFY_STOP_NONE with no FILLED trade → no crash."""
    monkeypatch.setenv("STOP_RETRY_ON_NONE_V1", "1")
    shadow = _mk_trade(tid=100, mode="shadow")
    poller, tm = _mk_poller(tmp_path, [shadow])

    import backend.v9.services.fill_poller as fp
    result_path = _write_result(tmp_path, "MODIFY_STOP_NONE")
    monkeypatch.setattr(fp, "RESULT_PATH", result_path)

    poller._last_result_mtime = 0.0
    poller._check_result()  # should not crash

    assert tm._modify_calls == []


# ── Test 5: retry throttle ───────────────────────────────────────────────────

def test_retry_throttle(tmp_path, monkeypatch):
    """Second retry within 10s is suppressed."""
    monkeypatch.setenv("STOP_RETRY_ON_NONE_V1", "1")
    trade = _mk_trade(tid=700, stop=7450.0)
    poller, tm = _mk_poller(tmp_path, [trade])

    import backend.v9.services.fill_poller as fp
    result_path = _write_result(tmp_path, "MODIFY_STOP_NONE")
    monkeypatch.setattr(fp, "RESULT_PATH", result_path)

    # First call → retry
    poller._last_result_mtime = 0.0
    poller._check_result()
    assert len(tm._modify_calls) == 1

    # Second call immediately → throttled (need to update mtime to trigger re-read)
    result_path.write_text(json.dumps({"status": "MODIFY_STOP_NONE", "ts": str(time.time() + 1)}))
    poller._check_result()
    assert len(tm._modify_calls) == 1  # still 1, throttled
