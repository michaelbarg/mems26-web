"""Day-type writer watchdog — detects AND heals a stale v9_day_type_state.

Incident 2026-08-05: day_type_state writer died at 11:45 IL, no entries
for 2h15m (08:45-11:00 ET). Missed the entire IB formation period.
Incident 2026-08-07 (K2 root diagnosis, 2026-08-08): 54-60 min gaps DURING
RTH although this watchdog warned every 5 minutes. Three stacked defects:

1. The P2-7 "self-heal" (reset the write-on-change signature) was DEAD CODE
   in production: its only caller (bar_level_detector.on_bar) passed
   `app_state=getattr(self, "_app_state", None)` and NOTHING in the backend
   ever set `_app_state` — so app_state was always None and the reset block
   never ran. Fixed here: when the caller passes None, resolve the REAL
   backend.main app.state directly (lazy import — no cycle at runtime).
2. Even a working signature reset cannot heal INPUT STARVATION: the writer
   is an event handler on the "5min" topic, and the FiveMinAggregator only
   closes a bar when the NEXT tick crosses the boundary. Its
   force_close_if_stale() existed for exactly this but had ZERO callers
   (same never-wired class as drain_command_queue). Escalation stage 2 now
   calls it: a stale partial bar is force-closed and published, the writer
   runs on real data. (Rule 1: we publish data we actually hold — never
   synthesize a bar.)
3. main.py armed the signature BEFORE the INSERT, so one failed write
   silenced the writer until the state changed — fixed in
   backend/v9/systems/day_type/state_persist.py (arm-after-success).

Escalation ladder on staleness during RTH (never raises, rate-limited):
  stage 1 (every check): reset the write-on-change signature → if bars flow,
          the next bar force-writes a row.
  stage 2 (staleness persists >= 60s after stage 1, max 1/min): force-close
          the aggregator's stale partial 5-min bar → publishes a real bar →
          the writer runs even when tick flow paused mid-bar.
  stage 3 (staleness > 2x threshold): CRITICAL log + ops_log ERROR — the
          5min input feed itself is dead (bridge/DLL); code cannot heal a
          dead feed, a human must look. No synthetic rows (Rule 1).

Designed to run every bar (bar_level_detector) or from a periodic task.
Never raises — fail-safe.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

STALE_THRESHOLD_MIN = float(os.environ.get("DAYTYPE_STALE_THRESHOLD_MIN", "10"))
_last_alert_ts: float = 0.0
_ALERT_COOLDOWN_S = 300  # 5 min between alerts

# Escalation state (module-level; reset whenever the writer is healthy again)
_esc = {"first_stale_ts": 0.0, "force_close_ts": 0.0, "critical_ts": 0.0}
_FORCE_CLOSE_MIN_STALE_S = 60.0   # give the sig-reset one fair chance first
_FORCE_CLOSE_COOLDOWN_S = 60.0


def _is_rth_now() -> bool:
    """True inside 09:30-16:00 ET (extracted for tests)."""
    from zoneinfo import ZoneInfo
    et_now = datetime.now(ZoneInfo("America/New_York"))
    et_hour = et_now.hour
    et_min = et_now.minute
    return (et_hour > 9 or (et_hour == 9 and et_min >= 30)) and et_hour < 16


def _resolve_app_state(app_state):
    """K2 fix #1: the self-heal must reach the REAL app.state.

    The production caller (bar_level_detector) always passed None because
    nothing ever set `_app_state` on it or on the gateway — so the signature
    reset never ran, live, since P2-7 shipped. When the caller cannot supply
    it, resolve backend.main's app directly (lazy import; backend.main is the
    real entrypoint per SYSTEM_INDEX — NOT backend.v9.main)."""
    if app_state is not None:
        return app_state
    try:
        from backend.main import app as _main_app
        return _main_app.state
    except Exception:
        return None


def _escalate(age_min: float) -> None:
    """Stages 2+3 — see module docstring. Never raises."""
    now = time.time()
    if _esc["first_stale_ts"] == 0.0:
        _esc["first_stale_ts"] = now
        return
    persisted_s = now - _esc["first_stale_ts"]

    # Stage 2: the sig-reset had its chance and no row appeared → the writer
    # is not RUNNING (input starvation). Force-close the aggregator's stale
    # partial bar so a REAL bar publishes and the writer runs.
    if persisted_s >= _FORCE_CLOSE_MIN_STALE_S and \
            (now - _esc["force_close_ts"]) >= _FORCE_CLOSE_COOLDOWN_S:
        _esc["force_close_ts"] = now
        try:
            from backend.v9.services.bar_aggregator_5min import five_min_aggregator
            closed = five_min_aggregator.force_close_if_stale()
            if closed is not None:
                logger.warning(
                    "[DAYTYPE_WATCHDOG] ESCALATION-2: force-closed stale partial "
                    "5min bar %s → published, writer will run this bar",
                    getattr(closed, "start_ts", "?"))
            else:
                logger.warning(
                    "[DAYTYPE_WATCHDOG] ESCALATION-2: no stale partial bar to "
                    "force-close — 5min input feed has no data at all")
        except Exception as e:
            logger.warning("[DAYTYPE_WATCHDOG] ESCALATION-2 force-close failed: %s", e)

    # Stage 3: still stale far past the threshold — the feed itself is dead.
    if age_min > STALE_THRESHOLD_MIN * 2 and (now - _esc["critical_ts"]) >= _ALERT_COOLDOWN_S:
        _esc["critical_ts"] = now
        logger.critical(
            "[DAYTYPE_WATCHDOG] ESCALATION-3: day_type_state stale %.0f min "
            "despite sig-reset + force-close — the 5min feed (bridge/DLL) is "
            "likely dead. Day-type gates are running on stale state.", age_min)
        try:
            from scripts.ops_log import log_event
            log_event("daytype_watchdog", "ERROR",
                      f"writer starved {age_min:.0f}min — 5min feed likely dead "
                      f"(sig-reset + force-close did not produce a row)")
        except Exception:
            pass


def check_daytype_staleness(app_state=None) -> Optional[str]:
    """Check if the day-type writer is stale. If stale, HEAL (see module doc).

    Returns:
        None if healthy, or a warning string if stale.
    """
    try:
        from backend.v9.db.read import read_one

        if not _is_rth_now():
            return None  # outside RTH — no concern

        # Last day_type_state entry
        row = read_one(
            "SELECT ts, day_type FROM v9_day_type_state ORDER BY ts DESC LIMIT 1",
            {},
        )
        if not row:
            return _warn("no v9_day_type_state rows at all")

        last_ts = row["ts"]
        if isinstance(last_ts, str):
            last_ts = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)

        age_min = (datetime.now(timezone.utc) - last_ts).total_seconds() / 60

        # H2 (2026-08-13): before crying stale, check the writer heartbeat.
        # Write-on-change produces no row when state is unchanged — the DB
        # timestamp goes stale but the writer is alive. If the heartbeat is
        # recent (< threshold), the writer processed a bar recently and just
        # had nothing new to write. This prevents the false "starved" that
        # fired every 5 minutes on 08-12 (Variation/B2 stable for 3 hours).
        if age_min > STALE_THRESHOLD_MIN:
            _hb = None
            try:
                _real_app = app_state
                if _real_app is None:
                    from backend.main import app as _real_app_mod
                    _real_app = _real_app_mod.state
                _hb = getattr(_real_app, "_daytype_writer_heartbeat", None)
            except Exception:
                pass
            if _hb is not None:
                _hb_age_min = (time.time() - _hb) / 60.0
                if _hb_age_min < STALE_THRESHOLD_MIN:
                    # Writer is alive, just idle (state unchanged)
                    return None

        if age_min > STALE_THRESHOLD_MIN:
            msg = _warn(
                f"day_type_state stale: last entry {age_min:.0f}min ago "
                f"(threshold {STALE_THRESHOLD_MIN}min), last_type={row['day_type']}"
            )
            # Stage 1 self-heal: reset the write-on-change signature so the next
            # bar forces a fresh DB write. K2: resolve the REAL app.state when
            # the caller passed None (the production path always did).
            app_state = _resolve_app_state(app_state)
            if app_state is not None:
                try:
                    app_state._last_dts_sig = None
                    logger.warning("[DAYTYPE_WATCHDOG] SELF-HEAL: reset _last_dts_sig — "
                                   "next bar will force a DB write")
                except Exception:
                    pass
            _escalate(age_min)
            return msg

        # Healthy again → reset the escalation ladder
        _esc["first_stale_ts"] = 0.0
        return None
    except Exception as e:
        # No-silent-failures (CLAUDE.md): was logger.debug — a broken check is
        # a blind watchdog and must be visible. Reuse the alert cooldown so a
        # persistent failure logs once per 5 min, not per bar.
        global _last_alert_ts
        now = time.time()
        if now - _last_alert_ts >= _ALERT_COOLDOWN_S:
            _last_alert_ts = now
            logger.warning("[DAYTYPE_WATCHDOG] check failed (fail-safe): %s", e)
        return None


def _warn(msg: str) -> str:
    """Log warning with cooldown to avoid spam."""
    global _last_alert_ts
    now = time.time()
    if now - _last_alert_ts < _ALERT_COOLDOWN_S:
        return msg  # still return the message, just don't re-log
    _last_alert_ts = now
    logger.warning("[DAYTYPE_WATCHDOG] %s", msg)
    try:
        from scripts.ops_log import log_event
        log_event("daytype_watchdog", "WARN", msg)
    except Exception:
        pass
    return msg
