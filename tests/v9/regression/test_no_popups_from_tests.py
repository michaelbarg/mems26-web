"""A test run must never put a dialog on Michael's trading Mac.

2026-08-17, ~08:30 IL: Michael sent a screenshot of a modal macOS alert reading
"🔴 t" / "m1" and said "תפסיק את כל ההתראות האלה". Those strings are TEST
fixtures — the popups were mine.

Mechanism: the suite is run with `env -i` on purpose, so tests cannot be
poisoned by `.env` (importing fire_drill at collection time once polluted 83+
tests). But `local_alert` is deliberately DEFAULT-ON — that inversion exists
because on 07-27 twelve CRITICAL naked-stop alerts died silently while Michael
was blind for 41 minutes on 10 naked contracts, and he lost more than half the
account. With `env -i` the flag is unset, so the safety default won, and every
test touching an alert path opened a real osascript window and played a real
sound on the machine that was about to trade.

The default-ON is right and stays. What was missing is that a test is not a
trading session.
"""
import os

from backend.v9.services import local_alert


class TestSilentUnderPytest:
    def test_disabled_while_pytest_runs(self):
        assert local_alert.enabled() is False, (
            "a test run must never open a window on the trading machine")

    def test_pytest_is_detected(self):
        assert local_alert._under_test() is True

    def test_the_safety_default_is_intact_outside_tests(self, monkeypatch):
        """Opting OUT stays the explicit action — the 07-27 ruling."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setenv("_", "/usr/bin/python3")
        monkeypatch.delenv("LOCAL_ALERTS_V1", raising=False)
        assert local_alert.enabled() is True

    def test_explicit_off_is_honoured(self, monkeypatch):
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setenv("_", "/usr/bin/python3")
        monkeypatch.setenv("LOCAL_ALERTS_V1", "0")
        assert local_alert.enabled() is False

    def test_the_phone_path_goes_through_the_same_gate(self):
        """phone_alert.push() calls local_alert FIRST and ALWAYS (07-27), so
        silencing local_alert is what actually stops the popups."""
        import inspect
        from backend.v9.services import phone_alert
        src = inspect.getsource(phone_alert.push)
        assert "local_alert" in src
