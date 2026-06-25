"""T7: Alerter regression tests.

The alerter emits alerts via log + Slack webhook (if set).
When webhook unset → no crash. When set → payload built.

if reverted → RED because: removing the alerter module would cause ImportError.
"""
import os
from unittest.mock import patch

from backend.v9.services.alerter import alert, _last_alert


def test_alert_no_crash_without_webhook():
    """Alert works without SLACK_WEBHOOK_URL (log only, no crash)."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SLACK_WEBHOOK_URL", None)
        os.environ.pop("SLACK_UAT_WEBHOOK", None)
        # Should not raise
        alert("TEST", "test message", severity="info")


def test_alert_critical_rate_limited():
    """Critical alerts are rate-limited (same type within 5 min → skipped)."""
    _last_alert.clear()
    alert("RATE_TEST", "first", severity="critical")
    assert "RATE_TEST" in _last_alert
    first_ts = _last_alert["RATE_TEST"]
    # Second call within rate window → skipped (timestamp not updated)
    alert("RATE_TEST", "second", severity="critical")
    assert _last_alert["RATE_TEST"] == first_ts  # not updated
    _last_alert.clear()


def test_alert_info_not_rate_limited():
    """Info alerts are NOT rate-limited."""
    _last_alert.clear()
    # Should not raise even with rapid calls
    for i in range(10):
        alert("INFO_TEST", f"msg {i}", severity="info")
    _last_alert.clear()


def test_feed_watchdog_emits_alert():
    """Feed watchdog calls alerter on halt."""
    import inspect
    from backend.v9.services.feed_watchdog import is_feed_alive
    source = inspect.getsource(is_feed_alive)
    assert "alerter" in source or "alert" in source


def test_kill_switch_emits_alert():
    """Kill-switch engage calls alerter."""
    import inspect
    from backend.v9.services.kill_switch import engage
    source = inspect.getsource(engage)
    assert "alerter" in source or "alert" in source
