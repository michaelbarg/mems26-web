"""Trade reality detection — REAL (Sierra-backed) vs PHANTOM (records ≠ reality).

Audit + regression harness for how MEMS26 tells a live-at-the-broker trade apart
from a phantom (backend believes it holds a position while Sierra is flat). It
drives the SYS-3 reconciler ``reconcile_position(tm)`` end-to-end against a fake
TradeManager and a REAL (temp) ``sierra_state.json`` — exercising the true
freshness/parse code in ``_sierra_state_qty`` / ``_sierra_state_working`` rather
than stubbing the reads — so the assertions cannot pass tautologically.

Properties proven (task 2026-07-13, "real-vs-phantom"):
  (a) TM short 1c  + Sierra qty=-1               → MATCH (real), never closes.
  (b) TM short 1c  + Sierra qty=0 / working=0,
      PHANTOM_HEAL_V1=1, sustained >= streak      → phantom detected, close_trade called.
  (c) same phantom shape, PHANTOM_HEAL_V1=0       → stays DIVERGENCE, never closes.

Anti-tautological guards baked in:
  * A SUB-streak flat (calls 1..N-1) must NOT heal — a momentary flat can never
    false-trigger the phantom close (the 07-10 phantom-CLOSE-of-a-REAL-trade risk).
  * A STALE state file (src falls back to the events journal) must NOT heal even
    with the flag ON and streak=1 — phantom-heal requires the FRESH DLL state
    file, not the fragile events journal (the 07-10 duplicate-feeder bug).
  * I-62: a demo/live target crossing on a bar must NOT book a hit — the real
    fill comes from FillPoller (Sierra), never from bar-price inference.

Companion to: backend/v9/tests/test_fix13_state_reconcile.py (state-vs-events
freshness) and backend/v9/tests/test_i62_full_target_guard.py (I-62 T-hit guard).
"""
import json
import time
import types

import pytest

from backend.v9.services import sierra_position_reconciler as spr


# ── fakes ───────────────────────────────────────────────────────────────────
def _mk_trade(direction="SHORT", contracts=1, mode="live", tid=340, state="FILLED"):
    """Minimal V9Trade stand-in with exactly the fields reconcile_position reads."""
    t = types.SimpleNamespace()
    t.id = tid
    t.mode = mode
    t.state = state
    t.direction = direction
    t.quality = {"contracts": contracts}   # trade_contract_count() reads this
    t.t1_hit_ts = None
    t.t2_hit_ts = None
    t.t3_hit_ts = None
    return t


class FakeTM:
    """Fake TradeManager: serves get_active_trades() and records close_trade()."""

    def __init__(self, trades):
        self._trades = list(trades)
        self.closed = []  # [(trade_id, reason), ...]

    def get_active_trades(self, mode=None):
        return list(self._trades)

    def close_trade(self, trade_id, reason=None, exit_price=None):
        self.closed.append((int(trade_id), reason))
        for t in self._trades:
            if t.id == trade_id:
                t.state = "CLOSED"   # realistic: a closed trade leaves the active set


def _write_state(path, qty, working, age_s=0.0):
    """Write a DLL-style sierra_state.json. age_s>0 backdates mtime → forces stale."""
    path.write_text(json.dumps({
        "ts": int(time.time()), "is_sim": 1,
        "position_qty": qty, "avg_price": 7596.0,
        "working_orders": working, "orders": [],
    }) + "\n")
    if age_s:
        import os
        old = time.time() - age_s
        os.utime(path, (old, old))


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Reset the module-global phantom streak + env between tests (no leakage)."""
    spr._phantom_flat_streak = 0
    monkeypatch.delenv("PHANTOM_HEAL_V1", raising=False)
    monkeypatch.delenv("PHANTOM_HEAL_STREAK", raising=False)
    yield
    spr._phantom_flat_streak = 0


# ── (a) REAL: TM short 1, Sierra qty=-1 → MATCH ─────────────────────────────
def test_real_short_matches_sierra(monkeypatch, tmp_path):
    """Broker holds -1 with brackets working; backend holds short 1 → MATCH."""
    state = tmp_path / "sierra_state.json"
    _write_state(state, qty=-1, working=2)      # real: qty matches, orders working
    monkeypatch.setattr(spr, "STATE_FILE", state)

    tm = FakeTM([_mk_trade(direction="SHORT", contracts=1)])
    ok, msg = spr.reconcile_position(tm)

    assert ok is True, msg
    assert "MATCH" in msg, msg
    assert "src=state" in msg, msg          # authoritative source = fresh DLL state
    assert "TM=-1" in msg and "Sierra=-1" in msg, msg
    assert tm.closed == [], "a REAL (matching) trade must never be closed"
    assert spr._phantom_flat_streak == 0, "match resets the phantom streak"


# ── (b) PHANTOM: flag ON, sustained flat → detected + close_trade called ────
def test_phantom_short_healed_after_sustained_streak(monkeypatch, tmp_path):
    """Sierra DEFINITIVELY flat (qty=0, working=0) while backend holds short 1.
    Sub-streak calls must NOT heal; only when the streak reaches the threshold
    does phantom-heal close the trade and free the slot."""
    state = tmp_path / "sierra_state.json"
    _write_state(state, qty=0, working=0)       # broker flat, NO working orders
    monkeypatch.setattr(spr, "STATE_FILE", state)
    monkeypatch.setenv("PHANTOM_HEAL_V1", "1")
    monkeypatch.setenv("PHANTOM_HEAL_STREAK", "3")

    tm = FakeTM([_mk_trade(direction="SHORT", contracts=1, tid=340)])

    # Calls 1 & 2 (sub-streak): a momentary flat must NOT trigger a close.
    for expected_streak in (1, 2):
        ok, msg = spr.reconcile_position(tm)
        assert ok is False, msg
        assert "DIVERGENCE" in msg, msg
        assert f"streak {expected_streak}/3" in msg, msg   # counter is advancing
        assert tm.closed == [], f"healed too early at streak {expected_streak}"
        assert spr._phantom_flat_streak == expected_streak

    # Call 3: streak hits the threshold → phantom detected → close_trade called.
    ok, msg = spr.reconcile_position(tm)
    assert ok is True, msg
    assert "PHANTOM-HEAL" in msg, msg
    assert "340" in msg, msg                              # the healed trade id
    assert tm.closed == [(340, "phantom_reconcile")], tm.closed
    assert spr._phantom_flat_streak == 0, "streak resets after a heal"


# ── (c) FLAG OFF: same phantom shape stays DIVERGENCE, never closes ─────────
def test_phantom_stays_divergence_when_flag_off(monkeypatch, tmp_path):
    """With PHANTOM_HEAL_V1=0 the identical flat/held shape must NEVER close —
    it stays a loud DIVERGENCE no matter how long the flat persists."""
    state = tmp_path / "sierra_state.json"
    _write_state(state, qty=0, working=0)
    monkeypatch.setattr(spr, "STATE_FILE", state)
    monkeypatch.setenv("PHANTOM_HEAL_V1", "0")   # explicit OFF

    tm = FakeTM([_mk_trade(direction="SHORT", contracts=1, tid=341)])

    for _ in range(5):                            # well past any streak threshold
        ok, msg = spr.reconcile_position(tm)
        assert ok is False, msg
        assert "DIVERGENCE" in msg, msg
    assert tm.closed == [], "flag OFF must never close a trade"
    assert spr._phantom_flat_streak == 0, "flag OFF → else-branch keeps streak at 0"


# ── anti-tautology: phantom-heal requires the FRESH state file, not events ──
def test_phantom_heal_requires_fresh_state_not_events_journal(monkeypatch, tmp_path):
    """Even with the flag ON and streak=1 (would heal instantly IF allowed): a
    flat reading that comes from the STALE state file → fallback to the events
    journal (src=events) must NOT heal. The events journal (07-10 duplicate-feeder
    bug) is never trusted to CLOSE a real trade — only the fresh DLL state file is."""
    state = tmp_path / "sierra_state.json"
    _write_state(state, qty=0, working=0, age_s=60.0)   # STALE → state reads → None
    monkeypatch.setattr(spr, "STATE_FILE", state)
    monkeypatch.setattr(spr, "_sierra_position_qty", lambda: 0)  # events say flat
    monkeypatch.setenv("PHANTOM_HEAL_V1", "1")
    monkeypatch.setenv("PHANTOM_HEAL_STREAK", "1")      # threshold=1 → instant IF allowed

    tm = FakeTM([_mk_trade(direction="SHORT", contracts=1, tid=342)])

    for _ in range(4):
        ok, msg = spr.reconcile_position(tm)
        assert ok is False, msg
        assert "DIVERGENCE" in msg and "src=events" in msg, msg
    assert tm.closed == [], "phantom-heal must NEVER fire from the events journal"


# ── I-62: demo/live target crossings await a REAL Sierra fill (no bar-booking)
def test_i62_demo_live_target_not_booked_from_bar():
    """A bar whose high crosses T2 must NOT book the hit on a LIVE trade — the
    real fill is delivered by FillPoller from Sierra, never inferred from a bar.
    (Incident 350, 07-10: a phantom 'T2 HIT at 7622' booked a fictional +$112.5
    win while Sierra had already stopped the runner near 7610.)"""
    import asyncio
    from unittest.mock import MagicMock
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector

    trade = MagicMock()
    trade.id = 350
    trade.direction = "LONG"
    trade.entry_price = 7608.5
    trade.state = "PARTIAL"
    trade.mode = "live"
    trade.t1, trade.t1_hit_ts = 7617.5, object()   # T1 already done
    trade.t2, trade.t2_hit_ts = 7622.0, None
    trade.t3, trade.t3_hit_ts = 7622.5, None
    trade.stop, trade.stop_hit_ts = 7611.25, None
    trade.entry_ts = None

    tm = MagicMock()
    tm.get_active_trades.return_value = [trade]
    det = BarLevelDetector(tm)
    bar = {"ts": 1783707800, "high": 7622.0, "low": 7612.0,
           "open": 7615.0, "close": 7620.0}
    # Use a dedicated loop and DO NOT touch the global event-loop policy
    # (asyncio.run() would clear the current loop and break sibling tests that
    # rely on the deprecated get_event_loop() auto-create, e.g. the existing
    # test_i62_full_target_guard.py when this file runs first in a full suite).
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(det.on_bar(bar))
    finally:
        loop.close()

    tm.on_target_hit.assert_not_called()   # I-62: awaits Sierra fill, no bar-booking
    tm.on_stop_hit.assert_not_called()
