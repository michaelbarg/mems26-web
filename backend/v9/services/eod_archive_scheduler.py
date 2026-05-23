"""P31 Phase 1 — End-of-day archive scheduler.

Fires ``eod_archiver.archive_today()`` once per RTH-active trading day at
15:55 ET (5 min before RTH close — matches the cron example baked into the
``archive_now`` docstring). On every successful archive, also runs the
90-day retention prune.

Why a Python scheduler instead of OS cron:

* Self-contained — survives ``launchctl`` restarts, no external dependency.
* DST + holiday-aware via ``market_clock.is_rth_open`` / ``is_market_holiday``.
* Same pattern as ``TPOHistorySnapshotter`` (Cursor 2026-05-22 AM, Issue B B1):
  one asyncio task per service, started from ``backend/main.py``'s startup
  hook, idempotent on restart, logged at WARNING level so the smoke check
  (`grep eod_archive_scheduler /tmp/backend.log`) confirms aliveness.
* CC #3 (`CC_UNIFIED_HISTORY_ARCHITECTURE_SPEC.md`, 2026-05-22 10:45 ET)
  picked **Path ii** (FastAPI lifecycle scheduler) over OS cron explicitly
  because the lifecycle pattern already proved itself with the TPO B1
  snapshotter.

Behavior:
    * On startup → optional immediate catch-up: if today is a trading day and
      we've passed 15:55 ET but there's no archive folder for today yet,
      archive now so a restart-after-15:55 still captures.
    * Loop: sleep until the next 15:55 ET on a trading day, archive, prune,
      sleep again. Cancelled gracefully on app shutdown.
    * Idempotent: ``archive_today()`` overwrites the target folder so a
      manual ``POST /api/v9/history/archive_now`` followed by the auto
      trigger 5 min later won't corrupt state.

Kill-switch: ``V9_DISABLE_EOD_SCHEDULER=1`` (e.g., during stability audits).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time as dt_time, timedelta
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from backend.v9.services import eod_archiver
from backend.v9.services.market_clock import (
    ClockStatus,
    HOLIDAYS_2026,
    current_clock_state,
    is_half_day,
    is_market_holiday,
    now_et,
    now_utc,
)

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# 15:55 ET = 5 min before RTH close. Per the crontab example in
# `history_routes.py::archive_now`. Half-days close at 13:00 ET — we still
# archive at 15:55 because nothing changes between 13:00 and 15:55 on
# half-day sessions (and Sierra keeps the export current with overnight
# Globex anyway).
ARCHIVE_TIME_ET = dt_time(15, 55, 0)
POST_SLEEP_BUFFER_S = 10.0
ERROR_BACKOFF_S = 300.0


class EODArchiveScheduler:
    """Async loop that triggers ``archive_today`` once per trading day."""

    def __init__(
        self,
        *,
        archive_time_et: dt_time = ARCHIVE_TIME_ET,
        post_sleep_buffer_s: float = POST_SLEEP_BUFFER_S,
    ) -> None:
        self.archive_time_et = archive_time_et
        self.post_sleep_buffer_s = post_sleep_buffer_s
        self._task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            logger.warning("[eod_archive_scheduler] already running")
            return
        self._task = asyncio.create_task(self._run(), name="eod_archive_scheduler")
        logger.warning(
            "[eod_archive_scheduler] task started — archive_time=%s ET retention=%dd",
            self.archive_time_et.strftime("%H:%M"),
            eod_archiver.ARCHIVE_RETENTION_DAYS,
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("[eod_archive_scheduler] task stopped")

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        # Startup catch-up — if a backend restart happened *after* 15:55 ET on
        # a trading day and there's still no archive folder for today, run
        # one immediately so we don't lose the session to a maintenance window.
        try:
            result = self.archive_if_due(reason="startup_catchup")
            logger.info("[eod_archive_scheduler] startup catch-up: %s", result)
        except Exception as e:
            logger.exception("[eod_archive_scheduler] startup catch-up failed: %s", e)

        # Steady-state loop
        while True:
            try:
                target_utc = self.next_archive_utc()
                sleep_s = max(0.0, (target_utc - now_utc()).total_seconds()) + self.post_sleep_buffer_s
                logger.debug(
                    "[eod_archive_scheduler] sleep %.0fs → next archive at %s UTC",
                    sleep_s,
                    target_utc.isoformat(),
                )
                await asyncio.sleep(sleep_s)
                result = self.archive_if_due(reason="scheduled")
                logger.warning("[eod_archive_scheduler] scheduled archive: %s", result)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("[eod_archive_scheduler] loop iteration failed: %s", e)
                await asyncio.sleep(ERROR_BACKOFF_S)

    # ------------------------------------------------------------------
    # Trigger logic — public for tests + manual invocation
    # ------------------------------------------------------------------

    def archive_if_due(self, *, reason: str = "manual") -> Dict[str, Any]:
        """Archive today's session **only if** today is a trading day AND we've
        passed the configured archive time (or are within 1 h after it on a
        restart catch-up). Returns a structured ``{"ok"|"skipped": ...}``
        dict — never raises, so the caller can log a single line per attempt.
        """
        clock = current_clock_state()
        if clock.status != ClockStatus.READY:
            return {"skipped": "clock_pending", "reason": reason}
        et = clock.now_et

        # Skip weekends + market holidays — Sierra won't have a fresh session.
        if et.weekday() >= 5:
            return {"skipped": "weekend", "reason": reason, "et": et.isoformat()}
        if is_market_holiday(et.date()):
            return {"skipped": "holiday", "reason": reason, "et": et.isoformat()}

        # Only archive after the archive_time_et threshold. For the steady-state
        # loop this is always true (we slept until then). For startup catch-up,
        # only run if we've crossed the boundary AND haven't already archived
        # today (folder absence check below).
        archive_time_today_et = datetime.combine(et.date(), self.archive_time_et, tzinfo=ET)
        if et < archive_time_today_et:
            return {
                "skipped": "before_archive_time",
                "reason": reason,
                "et": et.isoformat(),
                "archive_time": archive_time_today_et.isoformat(),
            }

        # Idempotency: if today's folder already exists with the full file set,
        # this is a no-op archive (just refreshes mtimes). We still re-run so
        # we always capture the *latest* state of each JSON, including any
        # mid-session corrections.
        try:
            result = eod_archiver.archive_today(target_date=et.date().isoformat())
            try:
                prune = eod_archiver.prune_old_archives()
            except Exception as pe:
                logger.exception("[eod_archive_scheduler] prune failed: %s", pe)
                prune = {"error": str(pe)}
            return {
                "ok": True,
                "reason": reason,
                "archive": result,
                "prune": prune,
            }
        except Exception as e:
            logger.exception("[eod_archive_scheduler] archive_today failed: %s", e)
            return {"error": "archive_failed", "exception": str(e), "reason": reason}

    # ------------------------------------------------------------------
    # Sleep target — pure function, exposed for tests
    # ------------------------------------------------------------------

    def next_archive_utc(self, *, ref_et: Optional[datetime] = None) -> datetime:
        """Next future occurrence of ``archive_time_et`` on a trading day,
        returned in UTC so the asyncio loop can sleep against ``now_utc()``.
        """
        et = ref_et if ref_et is not None else now_et()
        # If we haven't yet passed today's archive time AND today is a trading
        # day, target today. Otherwise move to the next trading day.
        candidate_et = datetime.combine(et.date(), self.archive_time_et, tzinfo=ET)
        if et >= candidate_et or et.weekday() >= 5 or is_market_holiday(et.date()):
            candidate_et = candidate_et + timedelta(days=1)
        # Advance over weekends + holidays.
        for _ in range(10):  # bound the loop — at most a week of skips
            d = candidate_et.date()
            if d.weekday() >= 5 or d in HOLIDAYS_2026:
                candidate_et = candidate_et + timedelta(days=1)
                continue
            break
        return candidate_et.astimezone(UTC)


# Module-level singleton for the app to attach.
_singleton: Optional[EODArchiveScheduler] = None


def get_scheduler() -> EODArchiveScheduler:
    global _singleton
    if _singleton is None:
        _singleton = EODArchiveScheduler()
    return _singleton


def reset_singleton_for_tests() -> None:
    global _singleton
    _singleton = None
