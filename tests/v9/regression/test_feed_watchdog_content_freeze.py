"""Regression: feed_watchdog must HALT on a stalled feed (canonical bars stop
advancing) even when bridge pushes stay fresh — and must NOT false-halt from
the export file's ET-as-UTC ts offset.

2026-07-15 root: bars stopped reaching the store at 14:25 ET (DB frozen ~98min,
not advancing) while the DLL kept re-writing the export files every ~2s. The
push-time check saw them ALIVE, so the veto never fired and S2/S4 would have
traded on a stalled feed. Separately, the file bar `ts` is written ET-as-UTC
(~4h early), so the freshness check reads the DB's corrected ts, not the file.
"""
import datetime as _dt_mod

from backend.v9.services import feed_watchdog as fw


class _FakeDT:
    """now() fixed inside RTH (10:00 CT, Wed) so the RTH gate passes."""

    @staticmethod
    def now(tz=None):
        return _dt_mod.datetime(2026, 7, 15, 10, 0, tzinfo=tz)

    @staticmethod
    def fromisoformat(s):
        return _dt_mod.datetime.fromisoformat(s)


def _raise_import(*a, **k):
    raise ImportError("test isolation — bypass real StreamHealthService")


def _arm(monkeypatch, db_age):
    monkeypatch.setenv("FEED_WATCHDOG", "1")
    monkeypatch.setattr(fw, "datetime", _FakeDT)
    monkeypatch.setattr(fw, "_db_max_bar_age", lambda: db_age)
    # Isolate from the real app's StreamHealthService (may hold stale push-times)
    # so these tests exercise ONLY the content path.
    monkeypatch.setattr(fw.importlib, "import_module", _raise_import)


def test_stalled_feed_halts(monkeypatch):
    """Newest DB bar 2h old → HALT (blocked)."""
    _arm(monkeypatch, db_age=7200)
    alive, reason = fw.is_feed_alive()
    assert alive is False
    assert "frozen" in reason


def test_fresh_bars_pass(monkeypatch):
    """Newest DB bar 2min old → not halted by the content check."""
    _arm(monkeypatch, db_age=120)
    alive, _ = fw.is_feed_alive()
    assert alive is True


def test_db_unreadable_fail_open(monkeypatch):
    """DB age None (unreadable) → fail OPEN (never a synthetic halt)."""
    _arm(monkeypatch, db_age=None)
    alive, _ = fw.is_feed_alive()
    assert alive is True


def test_boundary_just_under_threshold_passes(monkeypatch):
    """Age just under the 600s threshold → alive (one missed bar tolerated)."""
    _arm(monkeypatch, db_age=fw.CONTENT_STALE_SECONDS - 1)
    alive, _ = fw.is_feed_alive()
    assert alive is True


def test_disabled_flag_never_halts(monkeypatch):
    """FEED_WATCHDOG off → always alive even with a stalled feed."""
    monkeypatch.setenv("FEED_WATCHDOG", "0")
    monkeypatch.setattr(fw, "datetime", _FakeDT)
    monkeypatch.setattr(fw, "_db_max_bar_age", lambda: 99999)
    alive, _ = fw.is_feed_alive()
    assert alive is True
