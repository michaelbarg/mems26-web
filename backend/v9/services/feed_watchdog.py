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

# ── CONTENT staleness (frozen-tail / stalled feed) ───────────────────
# 2026-07-15 root: the push-time check below is defeated by a "frozen-tail" —
# the DLL keeps re-writing the export file every ~2s (mtime + bridge push stay
# fresh) while new bars stop reaching the trading store. Verified: bars stopped
# at 14:25 ET while pushes stayed fresh → S2/S4 would have fired on a stalled
# feed. So we ALSO check how old the newest CANONICAL bar is.
#
# We read this from the DB (v9_bars_5min), NOT the export file: the file's bar
# `ts` is written ET-as-UTC (a ~4h offset vs true UTC — verified: the same last
# bar, close 7606, shows 14:25 UTC in the file but 18:25 UTC / 21:25 IL in the
# DB). Reading the file `ts` would compute a permanent ~4h "staleness" and
# false-halt even on a healthy feed. The DB carries the corrected tz-aware ts.
#
# A 5-min bar tip is always up to ~5min old in normal operation; >2 missed bars
# (600s) means bars stopped advancing. Env-tunable, default 600s.
CONTENT_STALE_SECONDS = float(os.getenv("FEED_CONTENT_STALE_SECONDS", "600"))


def _db_max_bar_age() -> Optional[float]:
    """Age (seconds) of the newest bar in the canonical LIVE table v9_bars_5min_woodies.

    SoT fix (Michael approval, 2026-07-16 16:4x IDT): was v9_bars_5min — the LEGACY
    table, which froze at 07-15 22:55 (stopped being fed) while live bars flow into
    v9_bars_5min_woodies (docs/SOURCE_OF_TRUTH.md). The stale read false-halted every
    fire on 07-16 (valid ZLR SHORT blocked 16:35, feed actually 1min fresh). Exactly
    the known SoT failure CLAUDE.md §Codebase-Index warns about (2026-06-22).

    TZ-safe (the DB ts is tz-aware / corrected, unlike the ET-as-UTC file ts).
    Returns None on any error → the caller fails OPEN (never a synthetic halt;
    Source-of-Truth Rule 1).
    """
    try:
        import datetime as _dt
        from backend.v9.db.read import read_scalar
        row = read_scalar("SELECT MAX(ts) FROM v9_bars_5min_woodies")
        if row is None:
            return None
        if not hasattr(row, "tzinfo"):
            return None
        now = _dt.datetime.now(_dt.timezone.utc)
        if row.tzinfo is None:
            row = row.replace(tzinfo=_dt.timezone.utc)
        return (now - row).total_seconds()
    except Exception:
        return None


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

    # ── CONTENT-freshness (frozen-tail / stalled feed) — DB canonical ts ──
    # Catches the case where bridge pushes stay fresh but new bars stop reaching
    # the trading store. Uses the DB's corrected tz-aware ts (see _db_max_bar_age
    # — the file ts is ET-as-UTC and would false-halt). Fails open when the DB
    # is unreadable (age None).
    db_age = _db_max_bar_age()
    if db_age is not None and db_age > CONTENT_STALE_SECONDS:
        reason = ("FEED_WATCHDOG HALT: canonical bars frozen — newest v9_bars_5min_woodies "
                  "is %.0fmin old (threshold %.0fs); bars stopped advancing while "
                  "pushes may stay fresh" % (db_age / 60.0, CONTENT_STALE_SECONDS))
        logger.warning("[FeedWatchdog] %s", reason)
        try:
            from backend.v9.services.alerter import alert
            alert("FEED_HALT", reason, severity="critical")
        except Exception:
            pass
        return (False, reason)

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
