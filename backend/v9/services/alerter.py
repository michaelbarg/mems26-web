"""Alerter — emit alerts on critical events (log + Slack webhook-if-set).

Covers: feed-death/watchdog-halt, daily-loss-halt, kill-switch, fires, exits.
Slack webhook from SLACK_WEBHOOK_URL or SLACK_UAT_WEBHOOK (same as frozen_tail_watchdog).
When unset → logger.warning only (no crash).

Usage:
    from backend.v9.services.alerter import alert
    alert("FEED_HALT", "canonical streams stale >90s", severity="critical")
    alert("FIRE", "S4 ZLR SHORT @7450 → SHADOW", severity="info")
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from typing import Optional

logger = logging.getLogger("alerter")

# Rate-limit: don't spam the same alert type more than once per interval
_RATE_LIMIT_SECONDS = 300.0  # 5 minutes
_last_alert: dict = {}  # {alert_type: timestamp}


def alert(
    alert_type: str,
    message: str,
    severity: str = "info",
    extra: Optional[dict] = None,
) -> None:
    """Emit an alert via log + Slack webhook (if configured).

    Args:
        alert_type: e.g. "FEED_HALT", "DAILY_LOSS_HALT", "KILL_SWITCH", "FIRE", "EXIT"
        message: human-readable description
        severity: "info", "warning", "critical"
        extra: optional dict of additional data
    """
    now = time.time()

    # Rate-limit critical alerts to avoid spam
    if severity == "critical":
        last = _last_alert.get(alert_type, 0)
        if now - last < _RATE_LIMIT_SECONDS:
            return
        _last_alert[alert_type] = now

    # Always log
    log_msg = "[Alert:%s] %s %s" % (severity.upper(), alert_type, message)
    if severity == "critical":
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

    # Slack webhook (if configured)
    webhook = os.environ.get("SLACK_WEBHOOK_URL") or os.environ.get("SLACK_UAT_WEBHOOK")
    if not webhook:
        return

    try:
        emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")
        slack_text = "%s *%s* %s" % (emoji, alert_type, message)
        if extra:
            slack_text += "\n```%s```" % json.dumps(extra, default=str, indent=2)
        data = json.dumps({"text": slack_text}).encode()
        req = urllib.request.Request(webhook, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logger.debug("[Alerter] Slack send failed (non-fatal): %s", e)
