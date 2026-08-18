"""A notification that fails once must not be lost.

Michael, 2026-08-18: "there are no alerts on the watch, and there used to be."

The transport was configured correctly and the credentials were valid — a
manual send returned {"status":1} on the first try. What the log showed was
that the sends had LEFT and DIED:

    pushover send failed rc=6    (curl: could not resolve host)
    pushover send failed rc=28   (curl: 6s timeout)

One attempt, no retry, `logger.warning`, gone. A DNS blip or a loaded machine
was enough to make a fire or a close silently never reach him — the same
blindness class as the 08-12 orphan that ran unseen.
"""
import subprocess
import pytest

from backend.v9.services import ntfy_notify as N


@pytest.fixture(autouse=True)
def _creds(monkeypatch):
    monkeypatch.setenv("PUSHOVER_USER_KEY", "u-test")
    monkeypatch.setenv("PUSHOVER_API_TOKEN", "t-test")
    monkeypatch.setattr(N.time, "sleep", lambda *_: None)   # no real backoff


def _result(rc, out=b""):
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=out, stderr=b"")


OK = _result(0, b'{"status":1}')
DNS = _result(6)          # could not resolve host
TIMEOUT = _result(28)     # the 6s -m expired


class TestItRetries:
    def test_a_dns_blip_no_longer_loses_the_alert(self, monkeypatch):
        calls = []

        def _run(cmd, **kw):
            calls.append(1)
            return DNS if len(calls) == 1 else OK

        monkeypatch.setattr(N.subprocess, "run", _run)
        N._pushover("🔫 LONG #1", "fired", "high", "fire")
        assert len(calls) == 2, "gave up after the first failure"

    def test_a_timeout_no_longer_loses_the_alert(self, monkeypatch):
        calls = []

        def _run(cmd, **kw):
            calls.append(1)
            return TIMEOUT if len(calls) < 3 else OK

        monkeypatch.setattr(N.subprocess, "run", _run)
        N._pushover("✅ #1 WIN", "+$120", "high", "close")
        assert len(calls) == 3

    def test_it_stops_once_delivered(self, monkeypatch):
        calls = []
        monkeypatch.setattr(N.subprocess, "run",
                            lambda *a, **k: (calls.append(1), OK)[1])
        N._pushover("t", "m", "default", "")
        assert len(calls) == 1, "a delivered message must not be re-sent"

    def test_it_is_bounded(self, monkeypatch):
        calls = []
        monkeypatch.setattr(N.subprocess, "run",
                            lambda *a, **k: (calls.append(1), DNS)[1])
        N._pushover("t", "m", "default", "")
        assert len(calls) == 3, "must not retry forever on a daemon thread"

    def test_an_exception_is_retried_too(self, monkeypatch):
        calls = []

        def _run(cmd, **kw):
            calls.append(1)
            if len(calls) == 1:
                raise OSError("network down")
            return OK

        monkeypatch.setattr(N.subprocess, "run", _run)
        N._pushover("t", "m", "default", "")
        assert len(calls) == 2


class TestItSaysSoWhenItGivesUp:
    def test_exhaustion_is_an_error_not_a_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(N.subprocess, "run", lambda *a, **k: DNS)
        with caplog.at_level("ERROR"):
            N._pushover("🚨 naked contract", "5c, stops cover 4", "urgent", "")
        assert any(r.levelname == "ERROR" for r in caplog.records), (
            "a notification that never arrived must not be a quiet warning")
        assert any("did NOT receive" in r.getMessage() for r in caplog.records)

    def test_it_never_raises_into_the_caller(self, monkeypatch):
        """Notification is best-effort: it must never touch the trading path."""
        def _boom(*a, **k):
            raise RuntimeError("curl exploded")
        monkeypatch.setattr(N.subprocess, "run", _boom)
        N._pushover("t", "m", "default", "")      # must not raise

    def test_missing_credentials_is_a_silent_skip(self, monkeypatch):
        monkeypatch.delenv("PUSHOVER_USER_KEY", raising=False)
        called = []
        monkeypatch.setattr(N.subprocess, "run",
                            lambda *a, **k: (called.append(1), OK)[1])
        N._pushover("t", "m", "default", "")
        assert not called
