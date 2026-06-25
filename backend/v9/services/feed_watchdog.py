"""Feed watchdog — block fires when canonical trading streams are stale.

LIVE blocker #0: the 06-19 Juneteenth incident (bridge bars_5min died ~12:00,
half-RTH blind, orphan position 186/187). Never silently trade on a dead feed.

Flag: FEED_WATCHDOG (default OFF in shadow; designed for ON at LIVE).

When ON: checks the two canonical trading streams (5min, woodies_5min) via
StreamHealthService. If BOTH are stale (> threshold), returns HALTED with
reason. The gateway blocks all new fires. Auto-resumes when either stream
delivers a fresh push.

Does NOT check live_price (tick stream, not bar stream) or non-trading
streams (footprint, tick_reversal, etc.).
"""
from __future__ import annotations

import importlib
import logging
import os
import time
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger("feed_watchdog")

# Staleness threshold: if BOTH canonical bar streams haven't pushed for this
# many seconds during RTH, the feed is dead. 90s = 1.5× the 5-min bar interval.
STALE_THRESHOLD_SECONDS = 90.0

# The two streams that matter for trading decisions (bar data for S2+S4)
CANONICAL_STREAMS = ("5min", "woodies_5min")


def is_feed_alive() -> Tuple[bool, Optional[str]]:
    """Check if the canonical trading streams are alive.

    Returns (alive: bool, reason: str or None).
    When FEED_WATCHDOG is OFF → always (True, None).
    """
    if os.environ.get("FEED_WATCHDOG", "0").lower() not in ("1", "true", "yes"):
        return (True, None)

    # Only check during RTH (08:30–15:15 CT) — outside RTH, streams are expected to be idle
    try:
        from zoneinfo import ZoneInfo
        ct = ZoneInfo("America/Chicago")
        now_ct = datetime.now(ct)
        ct_min = now_ct.hour * 60 + now_ct.minute
        if ct_min < 510 or ct_min > 915:  # before 08:30 or after 15:15
            return (True, None)
    except Exception:
        pass  # fail-open if TZ unavailable

    # Read stream health from the singleton (app.state.stream_health_service)
    try:
        _app = importlib.import_module("backend.v9.app").app
        _shs = getattr(_app.state, "stream_health_service", None)
        if _shs is None:
            return (True, None)  # service not initialized yet → fail-open

        now = time.time()
        stale_streams = []
        for stream_name in CANONICAL_STREAMS:
            with _shs._lock:
                state = _shs._streams.get(stream_name)
            if state is None:
                continue
            age = now - state.last_bridge_push_ts if state.last_bridge_push_ts > 0 else -1
            if age < 0 or age > STALE_THRESHOLD_SECONDS:
                stale_streams.append((stream_name, age))

        if len(stale_streams) >= len(CANONICAL_STREAMS):
            # ALL canonical streams are stale → HALT
            details = ", ".join("%s(%.0fs)" % (n, a) for n, a in stale_streams)
            reason = "FEED_WATCHDOG HALT: all canonical streams stale [%s] (threshold %.0fs)" % (
                details, STALE_THRESHOLD_SECONDS)
            logger.warning("[FeedWatchdog] %s", reason)
            try:
                from backend.v9.services.alerter import alert
                alert("FEED_HALT", reason, severity="critical")
            except Exception:
                pass
            return (False, reason)

    except Exception as e:
        logger.debug("[FeedWatchdog] check failed (fail-open): %s", e)

    return (True, None)
