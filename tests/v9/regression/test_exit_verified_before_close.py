"""T4 — the books may not close until Sierra proves the exit happened.

Michael, live 2026-08-14: "המערכת הודיעה על מימוש ובפועל לא בוצע המימוש בסיארה."
Trade #682: booked CLOSED/$0 at 20:00:07, Sierra still SHORT 4 @7799.25 until the
21:02—21:09 stops. Real −$75, booked $0, LIVE slot freed for 62 minutes.

These tests EXECUTE the verifier (no source-string matching — that is exactly the
mistake that let the first MAE_SCRATCH "fix" ship broken on 08-14).
"""
import os

import pytest

from backend.v9.services import exit_verifier as ev


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    ev.clear()
    monkeypatch.setenv("EXIT_VERIFY_V1", "1")
    monkeypatch.setenv("EXIT_VERIFY_TIMEOUT_S", "45")
    monkeypatch.setenv("EXIT_VERIFY_MAX_ATTEMPTS", "2")
    yield
    ev.clear()


def _qty(monkeypatch, value):
    """Pin what Sierra reports (None = stale/unknown)."""
    monkeypatch.setattr(ev, "_sierra_qty", lambda: value)


def _silence_push(monkeypatch):
    sent = []
    monkeypatch.setattr(ev, "_push", lambda e, t, b: sent.append((e, t, b)))
    return sent


class TestHappyPath:
    def test_close_is_deferred_at_registration(self, monkeypatch):
        closed = []
        ok = ev.register(682, source="mae_scratch", reason="MAE",
                         on_confirmed=lambda: closed.append(682))
        assert ok is True
        assert closed == [], "books must NOT close on registration — that is the bug"
        assert ev.is_pending(682)

    def test_flat_confirms_and_closes(self, monkeypatch):
        closed = []
        ev.register(682, source="mae_scratch", reason="MAE",
                    on_confirmed=lambda: closed.append(682))
        _qty(monkeypatch, 0)
        assert ev.verify_pending() == 1
        assert closed == [682]
        assert not ev.is_pending(682)

    def test_no_double_close(self, monkeypatch):
        closed = []
        ev.register(682, source="mae_scratch", reason="MAE",
                    on_confirmed=lambda: closed.append(682))
        _qty(monkeypatch, 0)
        for _ in range(5):
            ev.verify_pending()
        assert closed == [682]


class TestTheActualIncident:
    """Reproduce 08-14 #682: command written, Sierra keeps holding -4."""

    def test_position_still_open_keeps_books_open(self, monkeypatch):
        closed = []
        _silence_push(monkeypatch)
        ev.register(682, source="mae_scratch", reason="MAE",
                    on_confirmed=lambda: closed.append(682))
        _qty(monkeypatch, -4)
        # 62 minutes of polling, exactly as happened live
        t0 = ev._pending[682].registered_ts
        for i in range(1, 63):
            ev.verify_pending(now=t0 + i * 60)
        assert closed == [], (
            "the books closed over a live Sierra position — this is the ghost "
            "Michael reported")

    def test_it_retries_the_flatten_before_giving_up(self, monkeypatch):
        emitted = []
        monkeypatch.setattr(ev, "_reemit_flatten", lambda p: emitted.append(p.attempt) or True)
        _silence_push(monkeypatch)
        ev.register(682, source="mae_scratch", reason="MAE", on_confirmed=lambda: None)
        _qty(monkeypatch, -4)
        t0 = ev._pending[682].registered_ts
        ev.verify_pending(now=t0 + 10)     # inside the window — no retry yet
        assert emitted == []
        ev.verify_pending(now=t0 + 50)     # past the 45s window → retry
        assert emitted == [2]

    def test_it_shouts_when_the_exit_never_executes(self, monkeypatch):
        monkeypatch.setattr(ev, "_reemit_flatten", lambda p: True)
        sent = _silence_push(monkeypatch)
        closed = []
        ev.register(682, source="mae_scratch", reason="MAE",
                    on_confirmed=lambda: closed.append(682))
        _qty(monkeypatch, -4)
        t0 = ev._pending[682].registered_ts
        ev.verify_pending(now=t0 + 50)     # attempt 2
        ev.verify_pending(now=t0 + 100)    # exhausted
        events = [e for e, _t, _b in sent]
        assert "exit_not_executed" in events
        assert closed == [], "never close the books on an unverified exit"
        assert not ev.is_pending(682), "stop re-emitting into a stuck DLL"

    def test_a_late_exit_still_confirms(self, monkeypatch):
        """Sierra fills at 40s — slow, but real. Books must close, not linger."""
        closed = []
        ev.register(682, source="mae_scratch", reason="MAE",
                    on_confirmed=lambda: closed.append(682))
        t0 = ev._pending[682].registered_ts
        _qty(monkeypatch, -4)
        ev.verify_pending(now=t0 + 20)
        assert closed == []
        _qty(monkeypatch, 0)
        ev.verify_pending(now=t0 + 40)
        assert closed == [682]


class TestHonestUnknown:
    def test_stale_state_never_counts_as_flat(self, monkeypatch):
        """Rule 1: a missing sierra_state is None, never a synthesized zero."""
        _silence_push(monkeypatch)
        closed = []
        ev.register(682, source="mae_scratch", reason="MAE",
                    on_confirmed=lambda: closed.append(682))
        _qty(monkeypatch, None)
        t0 = ev._pending[682].registered_ts
        for i in range(1, 20):
            ev.verify_pending(now=t0 + i * 30)
        assert closed == [], "unknown must never be read as flat"

    def test_unknown_is_bounded_and_loud(self, monkeypatch):
        """Waiting silently forever is not the safe side — it just moves the
        failure somewhere nobody looks. After EXIT_VERIFY_UNKNOWN_MAX_S the
        books still stay open, but Michael is told."""
        monkeypatch.setenv("EXIT_VERIFY_UNKNOWN_MAX_S", "300")
        sent = _silence_push(monkeypatch)
        closed = []
        ev.register(682, source="mae_scratch", reason="MAE",
                    on_confirmed=lambda: closed.append(682))
        _qty(monkeypatch, None)
        t0 = ev._pending[682].registered_ts
        ev.verify_pending(now=t0 + 120)
        assert ev.is_pending(682) and not sent, "must not shout too early"
        ev.verify_pending(now=t0 + 400)
        assert [e for e, _t, _b in sent] == ["exit_unverifiable"]
        assert closed == [], "an unverifiable exit never closes the books"


class TestRollback:
    def test_flag_off_restores_immediate_close(self, monkeypatch):
        monkeypatch.setenv("EXIT_VERIFY_V1", "0")
        assert ev.register(682, source="mae_scratch", reason="MAE",
                           on_confirmed=lambda: None) is False
        assert not ev.is_pending(682)


class TestWiring:
    def test_both_s6_exit_paths_defer(self):
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        # neither path may close inline any more
        assert 'self._tm.close_trade(trade.id, reason="MAE_SCRATCH")' not in src
        assert 'self._tm.close_trade(trade.id, reason="TARGET_APPROACH_REALIZE")' not in src
        assert src.count("exit_verifier") >= 2

    def test_the_poller_runs_the_verifier(self):
        import inspect
        from backend.v9.services import fill_poller
        src = inspect.getsource(fill_poller)
        assert "_verify_pending_exits" in src
        assert src.index("self._verify_pending_exits()") < src.index("self._maybe_reconcile()")


class TestAnotherPathClosedItFirst:
    """POSITION_TRUTH_SYNC_V1, a Sierra stop fill, or a manual close may reach
    the books first. That is a correct outcome — not a double close, not an
    alert."""

    def test_pending_retires_quietly(self, monkeypatch):
        closed = []
        ev.register(682, source="mae_scratch", reason="MAE",
                    on_confirmed=lambda: closed.append(682),
                    still_open=lambda: False)
        _qty(monkeypatch, 0)
        ev.verify_pending()
        assert closed == [], "must not close a trade the books already closed"
        assert not ev.is_pending(682)

    def test_unknown_open_state_keeps_verifying(self, monkeypatch):
        def _boom():
            raise RuntimeError("db down")
        closed = []
        ev.register(682, source="mae_scratch", reason="MAE",
                    on_confirmed=lambda: closed.append(682), still_open=_boom)
        _qty(monkeypatch, 0)
        ev.verify_pending()
        assert closed == [682], "unknown must fall through to the reality check"

    def test_detector_exposes_the_open_check(self):
        from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
        import types as _t

        class _TM:
            def get_active_trades(self):
                return [_t.SimpleNamespace(id=682)]

        d = BarLevelDetector(_TM())
        assert d._trade_still_open(682) is True
        assert d._trade_still_open(999) is False
