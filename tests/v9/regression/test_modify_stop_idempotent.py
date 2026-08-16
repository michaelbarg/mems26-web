"""T2 — MODIFY_STOP must be idempotent, or it clogs the command wire.

Measured on 2026-08-14 (S6 audit): **393 identical MODIFY_STOP commands for a
single trade in one session**, and **110 command files expired in the queue
without ever being sent**. Mechanism: `_emit_modify_stop` wrote the command but
never wrote the new stop back to the trade, so System 6's `stop_not_at_be`
invariant kept reading the OLD stop and re-fired on every bar. A FLATTEN queued
behind that flood can expire before it reaches the DLL — which is exactly how a
"realized" trade stays open in Sierra.

Two guards, both tested by EXECUTION (not source inspection):
  1. in-memory dedup — identical (trade, stop) within 60s is not re-sent,
  2. DB write-back — the trade's stop reflects what we asked for, and a DB
     failure is rolled back so the shared session is not left ABORTED.
"""
import types

import pytest

from backend.v9.services.trade_manager import manager as mgr_mod


class _FakeDB:
    def __init__(self, fail=False):
        self.commits = 0
        self.rollbacks = 0
        self.fail = fail

    def commit(self):
        if self.fail:
            raise RuntimeError("current transaction is aborted")
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _trade(tid=657, stop=7800.0):
    return types.SimpleNamespace(
        id=tid, stop=stop, mode="live", direction="SHORT",
        entry_price=7810.0, contracts=4,
        quality={"c1_stop_id": 1, "c2_stop_id": 2},
        sierra_order_id=10110,
    )


@pytest.fixture
def tm(monkeypatch):
    """A TradeManager with the wire and mode checks stubbed."""
    m = mgr_mod.TradeManager.__new__(mgr_mod.TradeManager)
    m._db = _FakeDB()
    m._recent_stop_emits = {}
    monkeypatch.setattr(m, "_is_demo_mode", lambda t: True, raising=False)
    monkeypatch.setattr(m, "_get_sierra_order_id", lambda t: 10110, raising=False)
    sent = []
    monkeypatch.setattr(
        "backend.v9.services.sierra_command.write_modify_stop",
        lambda **kw: sent.append(kw) or {"ok": True},
    )
    return m, sent


class TestDedup:
    def test_identical_stop_is_sent_once(self, tm):
        m, sent = tm
        t = _trade()
        for _ in range(10):
            m._emit_modify_stop(t, 7805.0)
        assert len(sent) == 1, (
            f"the same stop was pushed {len(sent)} times — this is the 393-command flood")

    def test_a_different_stop_still_goes_through(self, tm):
        m, sent = tm
        t = _trade()
        m._emit_modify_stop(t, 7805.0)
        m._emit_modify_stop(t, 7803.0)
        assert len(sent) == 2, "a genuinely new stop must still reach Sierra"

    def test_dedup_is_per_trade(self, tm):
        m, sent = tm
        m._emit_modify_stop(_trade(657), 7805.0)
        m._emit_modify_stop(_trade(658), 7805.0)
        assert len(sent) == 2


class TestWriteBack:
    def test_trade_stop_is_updated(self, tm):
        m, sent = tm
        t = _trade(stop=7810.0)
        m._emit_modify_stop(t, 7805.0)
        assert t.stop == 7805.0, (
            "without the write-back the S6 invariant re-fires on every bar forever")
        assert m._db.commits == 1

    def test_db_failure_rolls_back_and_does_not_raise(self, monkeypatch, tm):
        m, sent = tm
        m._db = _FakeDB(fail=True)
        t = _trade()
        m._emit_modify_stop(t, 7805.0)  # must not raise
        assert m._db.rollbacks == 1, (
            "a failed commit must be rolled back — an ABORTED shared session "
            "silently kills every later write (the mac-2 failure mode)")

    def test_command_failure_skips_write_back(self, monkeypatch, tm):
        m, sent = tm

        def _boom(**kw):
            raise RuntimeError("queue full")

        monkeypatch.setattr(
            "backend.v9.services.sierra_command.write_modify_stop", _boom)
        t = _trade(stop=7810.0)
        m._emit_modify_stop(t, 7805.0)
        assert t.stop == 7810.0, "books must not claim a stop Sierra never received"
