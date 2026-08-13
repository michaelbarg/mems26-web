"""Regression — orphan-breach alert died silently on 2026-08-12 (~$229 bleed).

Chain of death (all three fixed 2026-08-13):
1. PHONE_ALERTS_V1 unset → phone_alert.push() skipped the remote leg entirely.
2. phone_alert._send_pushover read PUSHOVER_TOKEN/PUSHOVER_USER — names that were
   never in .env (real names: PUSHOVER_API_TOKEN/PUSHOVER_USER_KEY).
3. Transport was urllib (broken SSL on Framework-Python 3.9).

Fix: phone_alert delegates to ntfy_notify (system curl, Pushover-primary, real
env names), and ntfy_notify.notify() no longer aborts before the Pushover leg
when NTFY_TOPIC is missing.
"""
import subprocess
import time
from unittest import mock

import pytest


@pytest.fixture
def _creds(monkeypatch):
    monkeypatch.setenv("PUSHOVER_USER_KEY", "u-test")
    monkeypatch.setenv("PUSHOVER_API_TOKEN", "t-test")
    monkeypatch.setenv("PHONE_ALERTS_V1", "1")
    monkeypatch.delenv("PHONE_ALERT_PROVIDER", raising=False)


def _drain_threads():
    time.sleep(0.3)


def test_notify_pushover_fires_without_ntfy_topic(monkeypatch, _creds):
    """NTFY_TOPIC missing must NOT kill the Pushover leg (13.08 fix)."""
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    from backend.v9.services import ntfy_notify
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        m = mock.Mock()
        m.returncode = 0
        m.stdout = b'{"status":1}'
        m.stderr = b""
        return m

    monkeypatch.setattr(ntfy_notify.subprocess, "run", fake_run)
    monkeypatch.setattr(ntfy_notify, "_rate_limited", lambda: False)
    ntfy_notify.notify("t", "m", priority="urgent")
    _drain_threads()
    pushover = [c for c in calls if any("pushover.net" in str(a) for a in c)]
    assert pushover, "Pushover leg must fire even with no NTFY_TOPIC"
    joined = " ".join(str(a) for a in pushover[0])
    assert "token=t-test" in joined and "user=u-test" in joined
    assert "priority=1" in joined  # urgent → 1


def test_phone_alert_push_reaches_pushover_with_real_env_names(monkeypatch, _creds):
    """phone_alert.push (the orphan-breach caller) must reach the curl/Pushover
    transport using PUSHOVER_API_TOKEN/PUSHOVER_USER_KEY — the names actually
    present in .env."""
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    from backend.v9.services import ntfy_notify, phone_alert
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        m = mock.Mock()
        m.returncode = 0
        m.stdout = b'{"status":1}'
        m.stderr = b""
        return m

    monkeypatch.setattr(ntfy_notify.subprocess, "run", fake_run)
    monkeypatch.setattr(ntfy_notify, "_rate_limited", lambda: False)
    phone_alert._last_sent.clear()
    phone_alert.push("test_orphan_breach", "STOP LEVEL BREACHED", "6c LONG", priority=1)
    _drain_threads()
    pushover = [c for c in calls if any("pushover.net" in str(a) for a in c)]
    assert pushover, "orphan-breach class alert must reach Pushover transport"


def test_phone_alert_disabled_still_no_crash(monkeypatch):
    """PHONE_ALERTS_V1 off: local-only path, never raises."""
    monkeypatch.setenv("PHONE_ALERTS_V1", "0")
    from backend.v9.services import phone_alert
    phone_alert.push("k", "t", "m", priority=1)  # must not raise


def test_machine_tag_prefixes_title(monkeypatch, _creds):
    """13.08 (two Macs live in parallel): every push title carries the
    machine tag so Michael knows WHICH machine is talking."""
    monkeypatch.setenv("MACHINE_TAG", "מק-1")
    monkeypatch.setenv("NTFY_TOPIC", "t-test")
    from backend.v9.services import ntfy_notify
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        m = mock.Mock(); m.returncode = 0; m.stdout = b'{"status":1}'; m.stderr = b""
        return m

    monkeypatch.setattr(ntfy_notify.subprocess, "run", fake_run)
    monkeypatch.setattr(ntfy_notify, "_rate_limited", lambda: False)
    ntfy_notify.notify("FIRED GB100", "x", priority="high")
    _drain_threads()
    joined = " ".join(str(a) for c in calls for a in c)
    assert "[מק-1] FIRED GB100" in joined
