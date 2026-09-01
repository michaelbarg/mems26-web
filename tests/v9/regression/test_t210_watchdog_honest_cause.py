"""T-210 — DAYTYPE_WATCHDOG escalation-3 must measure the feed before blaming it.

The alarm fired CRITICAL with *"the 5min feed (bridge/DLL) is likely dead"*
while the feed was demonstrably alive, and it phone-pushes. It never looked at
a bar: it measures the age of the newest `v9_day_type_state` ROW, and that
table is CHANGE-DRIVEN, not per-bar. Verified 2026-09-01 on production:
75 rows / 75 distinct ts, irregular intervals, and a 70-minute gap between
13:50 and 15:00 ET purely because the label did not change while the feed was
producing a bar every 5 minutes.

Naming the wrong subsystem is worse than saying "unknown" — it sends the human
to the wrong machine.

Anti-tautological: drives the REAL `_escalate` with the real module state; only
the DB probe is stubbed.

if reverted → RED because: restoring the unconditional "the 5min feed
(bridge/DLL) is likely dead" string makes test_alive_feed_is_not_blamed fail,
since the message would accuse the feed while the probe says 0.9 min.
"""
import logging

import pytest


@pytest.fixture(autouse=True)
def _reset_escalation():
    from backend.v9.services import daytype_watchdog as w
    w._esc.update({"first_stale_ts": 0.0, "force_close_ts": 0.0, "critical_ts": 0.0})
    yield
    w._esc.update({"first_stale_ts": 0.0, "force_close_ts": 0.0, "critical_ts": 0.0})


class _RecLogger:
    """Captures the module logger directly — no dependence on propagation."""
    def __init__(self):
        self.critical_msgs = []

    def critical(self, msg, *a):
        self.critical_msgs.append(msg % a if a else msg)

    def warning(self, msg, *a):
        pass

    def info(self, msg, *a):
        pass


def _run_escalation(monkeypatch, caplog, feed_age):
    from backend.v9.services import daytype_watchdog as w

    import time
    rec = _RecLogger()
    monkeypatch.setattr(w, "_five_min_feed_age_min", lambda: feed_age)
    monkeypatch.setattr(w, "logger", rec)
    # the first call only ARMS first_stale_ts and returns — seed it so this
    # call is the one that reaches stage 3 (the real production sequence).
    w._esc["first_stale_ts"] = time.time() - 600.0
    w._esc["force_close_ts"] = time.time()      # keep stage 2 inert
    w._escalate(w.STALE_THRESHOLD_MIN * 3 + 1)
    return " ".join(rec.critical_msgs)


def test_alive_feed_is_not_blamed(monkeypatch, caplog):
    """Feed fresh → the alarm must say so, and must NOT call it dead."""
    msg = _run_escalation(monkeypatch, caplog, feed_age=0.9)
    assert msg, "escalation-3 did not fire at all"
    assert "ALIVE" in msg, msg
    assert "NOT a dead feed" in msg, msg
    assert "likely dead" not in msg, (
        "T-210 regression: the alarm blamed the feed while the probe said the "
        "newest bar was 0.9 min old — " + msg)
    # and it must name the real alternative
    assert "written on change" in msg, msg


def test_stale_feed_is_still_reported(monkeypatch, caplog):
    """Anti-tautology: when the feed really IS stale, say so."""
    msg = _run_escalation(monkeypatch, caplog,
                          feed_age=__import__(
                              "backend.v9.services.daytype_watchdog",
                              fromlist=["x"]).STALE_THRESHOLD_MIN * 4)
    assert "IS stale too" in msg, msg
    assert "likely cause" in msg, msg


def test_unknown_feed_age_says_unknown(monkeypatch, caplog):
    """Rule 1: probe failure must produce an explicit UNKNOWN, not a guess."""
    msg = _run_escalation(monkeypatch, caplog, feed_age=None)
    assert "UNKNOWN" in msg, msg
    assert "cannot attribute" in msg, msg
    assert "likely dead" not in msg, msg


def test_feed_probe_reads_the_live_bar_table():
    """SoT: the probe must read v9_bars_5min_woodies, not v9_bars_5min.

    Reading the stalled/gapped table is the 2026-06-22 class and would make the
    alarm lie in the other direction.
    """
    import inspect
    from backend.v9.services.daytype_watchdog import _five_min_feed_age_min

    src = inspect.getsource(_five_min_feed_age_min)
    assert "v9_bars_5min_woodies" in src
    assert "FROM v9_bars_5min " not in src


def test_feed_probe_returns_none_on_failure(monkeypatch):
    """Honest failure, never a synthesised age."""
    from backend.v9.services import daytype_watchdog as w
    import backend.v9.db.read as dbread

    monkeypatch.setattr(dbread, "read_scalar",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))
    assert w._five_min_feed_age_min() is None
