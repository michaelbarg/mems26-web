"""Regression — a poisoned transaction must never silence trade writes.

mac-2 passed the full gate chain (gateway logged `duplicate_fire`, reachable
only after post-gate registration) yet wrote ZERO rows to v9_trades for 28 days,
and `v9_trades_id_seq.last_value` still equalled MAX(id) — proving `add()` was
never reached. Its log carried 37 × psycopg2 InFailedSqlTransaction: the shared
Session (main.py:1076, TradeManager + BarLevelDetector + FillPoller) had been
aborted by one consumer and NOBODY rolled it back, so Postgres discarded every
later statement.

`pool_pre_ping` did not and cannot help — it detects a dead connection, not an
aborted transaction on a live one.
"""
import inspect

import pytest

from backend.v9.db import session_guard


class _FakeSession:
    """Minimal Session double: poisoned until rollback() is called."""

    def __init__(self, poisoned=False):
        self.poisoned = poisoned
        self.rollbacks = 0
        self.executes = 0

    def execute(self, *a, **k):
        self.executes += 1
        if self.poisoned:
            raise RuntimeError(
                "psycopg2.errors.InFailedSqlTransaction: current transaction "
                "is aborted, commands ignored until end of transaction block")
        return True

    def rollback(self):
        self.rollbacks += 1
        self.poisoned = False


class TestEnsureClean:
    def test_healthy_session_untouched(self):
        s = _FakeSession(poisoned=False)
        assert session_guard.ensure_clean(s) is False
        assert s.rollbacks == 0

    def test_poisoned_session_is_rolled_back(self):
        s = _FakeSession(poisoned=True)
        assert session_guard.ensure_clean(s, where="test") is True
        assert s.rollbacks == 1
        assert s.poisoned is False

    def test_none_session_is_safe(self):
        assert session_guard.ensure_clean(None) is False

    def test_rollback_failure_never_raises(self):
        class _Bad(_FakeSession):
            def rollback(self):
                raise RuntimeError("rollback exploded")

        assert session_guard.ensure_clean(_Bad(poisoned=True)) is False


class TestSafeWrite:
    def test_success_passes_through(self):
        s = _FakeSession()
        assert session_guard.safe_write(s, lambda: 42) == 42
        assert s.rollbacks == 0

    def test_poisoned_write_rolls_back_and_retries_once(self):
        s = _FakeSession()
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("InFailedSqlTransaction: aborted")
            return "ok"

        assert session_guard.safe_write(s, fn, where="t") == "ok"
        assert s.rollbacks == 1 and calls["n"] == 2

    def test_unrelated_error_is_not_swallowed(self):
        s = _FakeSession()

        def fn():
            raise ValueError("a real bug")

        with pytest.raises(ValueError):
            session_guard.safe_write(s, fn)
        assert s.rollbacks == 0

    def test_second_failure_propagates(self):
        s = _FakeSession()

        def fn():
            raise RuntimeError("current transaction is aborted")

        with pytest.raises(RuntimeError):
            session_guard.safe_write(s, fn)


class TestWiring:
    def test_accept_setup_cleans_before_writing(self):
        from backend.v9.services.trade_manager.manager import TradeManager
        src = inspect.getsource(TradeManager.accept_setup)
        assert "ensure_clean" in src

    def test_fill_poller_cleans_after_a_swallowed_error(self):
        from backend.v9.services.fill_poller import FillPoller
        src = inspect.getsource(FillPoller.run)
        assert "ensure_clean" in src
        i_warn = src.index("poll error (continuing)")
        assert src.index("ensure_clean") > i_warn  # cleanup AFTER the swallow

    def test_gateway_commit_failures_clean_up(self):
        from backend.v9.gateway import trading_gateway
        src = inspect.getsource(trading_gateway)
        # all three modes (shadow/demo/live) must clean a failed commit
        assert src.count("ensure_clean") >= 3
