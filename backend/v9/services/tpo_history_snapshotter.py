"""P31 Issue B — TPO history snapshotter.

Sierra Study ID:3 ("TPO Value Area Lines · Today (developing)") draws a stepped
pink line for POC/VAH/VAL that updates every 30 min as new TPO letters
accumulate. Our chart must replicate this look — see
``docs/handoff/SIERRA_STUDIES_CONFIG_2026-05-19.md`` Study ID:3 and Michael's
clarification on 2026-05-22.

Constraint: Sierra's DLL only emits a single live ``session.poc/vah/val`` in
``tpo.json``; it does **not** expose per-letter history. Michael (2026-05-22 AM)
rejected DLL changes ("the data is live, just use it"). Solution: this service
samples the live value at every 30-min RTH boundary and persists it into
``v9_tpo_history`` so the API can serve stepped periods to the frontend
``TpoContinuityOverlay``.

CC #2 investigation deliverable (2026-05-22 09:15 ET) graded this path **B1**:
LOC ~105, risk LOW, fidelity HIGH, effort ~3 h. See
``docs/handoff/CC_INVESTIGATE_TPO_STEPPED_PERIODS.md``.

Behavior:
    * Snapshot only during RTH (``market_clock.is_rth_open``, holiday-aware).
    * Skip if ``tpo.json`` mtime is older than ``STALE_THRESHOLD_S`` (DLL
      paused, replay quiet, market closed for a half-day, …).
    * ``INSERT OR REPLACE`` keyed by ``ux_v9_tpo_history_ts`` so the same slot
      can be re-snapshotted safely (e.g., on startup catch-up).
    * On startup, write the **current** 30-min slot immediately so the chart
      isn't empty until the next boundary if the backend was restarted
      mid-session.
    * Main loop sleeps until the next 30-min ET boundary + a small DLL-update
      buffer, snapshots, repeats.

Edge cases handled:
    * DST transitions — uses ``zoneinfo("America/New_York")`` via market_clock.
    * Half-day closes — ``is_rth_open`` already honours ``HALF_DAYS_2026``.
    * Replay mode — defers to ``current_clock_state()``; if status is
      ``PENDING`` (replay clock not yet primed), the snapshot is skipped.
    * Restart mid-RTH — catch-up writes the current slot's POC immediately.
    * Persistent failure — exception inside the loop is logged and the loop
      backs off 60 s before retrying so we don't hot-loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from backend.v9.services.market_clock import (
    ClockStatus,
    current_clock_state,
    is_rth_open,
    now_et,
    now_utc,
)

logger = logging.getLogger(__name__)

UTC = ZoneInfo("UTC")

DEFAULT_TPO_JSON_PATH = Path(
    os.getenv(
        "V9_TPO_EXPORT_PATH",
        "/Users/michael/SierraChart_Data/v9_export/tpo.json",
    )
)
DEFAULT_DB_PATH = os.getenv(
    "V9_DB_PATH",
    "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db",
)

SNAPSHOT_INTERVAL_MIN = 30
STALE_THRESHOLD_S = 120.0
POST_BOUNDARY_BUFFER_S = 5.0
ERROR_BACKOFF_S = 60.0


class TPOHistorySnapshotter:
    """Periodic worker that writes per-letter TPO POC/VAH/VAL to v9_tpo_history."""

    def __init__(
        self,
        *,
        tpo_json_path: Path = DEFAULT_TPO_JSON_PATH,
        db_path: str = DEFAULT_DB_PATH,
        interval_min: int = SNAPSHOT_INTERVAL_MIN,
        stale_threshold_s: float = STALE_THRESHOLD_S,
        post_boundary_buffer_s: float = POST_BOUNDARY_BUFFER_S,
    ) -> None:
        self.tpo_json_path = Path(tpo_json_path)
        self.db_path = db_path
        self.interval_min = interval_min
        self.stale_threshold_s = stale_threshold_s
        self.post_boundary_buffer_s = post_boundary_buffer_s
        self._task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Spawn the background loop on the current event loop."""
        if self._task is not None and not self._task.done():
            logger.warning("[tpo_snapshotter] already running")
            return
        self._task = asyncio.create_task(self._run(), name="tpo_history_snapshotter")
        # WARNING level so the line survives uvicorn's INFO filter — useful as
        # the post-restart smoke check (`grep tpo_snapshotter /tmp/backend.log`).
        logger.warning(
            "[tpo_snapshotter] task started — tpo.json=%s db=%s interval=%dmin",
            self.tpo_json_path,
            self.db_path,
            self.interval_min,
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
        logger.info("[tpo_snapshotter] task stopped")

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        # 1) Startup catch-up — fill the current slot immediately so a restart
        #    mid-RTH doesn't leave the chart blank until the next boundary.
        try:
            result = self.snapshot_now(reason="startup_catchup")
            logger.info("[tpo_snapshotter] startup catch-up: %s", result)
        except Exception as e:
            logger.exception("[tpo_snapshotter] startup catch-up failed: %s", e)

        # 2) Loop: sleep until next 30-min boundary + buffer, snapshot, repeat.
        while True:
            try:
                next_boundary = self.next_boundary_utc()
                sleep_s = max(0.0, (next_boundary - now_utc()).total_seconds())
                sleep_s += self.post_boundary_buffer_s
                logger.debug(
                    "[tpo_snapshotter] sleep %.0fs → boundary %s UTC + %.0fs buffer",
                    sleep_s,
                    next_boundary.isoformat(),
                    self.post_boundary_buffer_s,
                )
                await asyncio.sleep(sleep_s)
                result = self.snapshot_now(reason="boundary")
                logger.info("[tpo_snapshotter] boundary snapshot: %s", result)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("[tpo_snapshotter] loop iteration failed: %s", e)
                await asyncio.sleep(ERROR_BACKOFF_S)

    # ------------------------------------------------------------------
    # Public snapshot entry-points (testable without an event loop)
    # ------------------------------------------------------------------

    def snapshot_now(self, *, reason: str = "manual") -> Dict[str, Any]:
        """Attempt one snapshot for the current 30-min slot.

        Returns a dict describing what happened (written / skipped + reason).
        Never raises — exceptions are converted to a structured ``error`` key
        so the caller can log a single line per attempt.
        """
        clock = current_clock_state()
        if clock.status != ClockStatus.READY:
            return {"skipped": "clock_pending", "reason": reason}

        et = clock.now_et
        if not is_rth_open(et):
            return {
                "skipped": "not_rth",
                "reason": reason,
                "et": et.isoformat() if et is not None else None,
            }

        tpo = self._read_tpo_json()
        if tpo is None:
            return {"skipped": "tpo_json_missing", "reason": reason}

        age_s = self._tpo_age_s()
        if age_s > self.stale_threshold_s:
            return {
                "skipped": "tpo_stale",
                "age_s": round(age_s, 1),
                "threshold_s": self.stale_threshold_s,
                "reason": reason,
            }

        session = tpo.get("session") or {}
        poc, vah, val = session.get("poc"), session.get("vah"), session.get("val")
        if not all(isinstance(x, (int, float)) for x in (poc, vah, val)):
            return {
                "skipped": "session_levels_missing",
                "poc": poc,
                "vah": vah,
                "val": val,
                "reason": reason,
            }

        ib = tpo.get("ib") or {}
        ib_found = bool(ib.get("found"))
        ib_high = ib.get("high") if ib_found else None
        ib_low = ib.get("low") if ib_found else None

        ts_str = self.slot_start_ts_str(et)
        try:
            self._upsert_history_row(
                ts_str=ts_str,
                poc=float(poc),
                vah=float(vah),
                val=float(val),
                ib_high=ib_high,
                ib_low=ib_low,
            )
        except sqlite3.Error as e:
            logger.error("[tpo_snapshotter] DB write failed for ts=%s: %s", ts_str, e)
            return {"error": "db_write_failed", "ts": ts_str, "exception": str(e), "reason": reason}

        return {
            "ok": True,
            "ts": ts_str,
            "poc": float(poc),
            "vah": float(vah),
            "val": float(val),
            "ib_high": ib_high,
            "ib_low": ib_low,
            "tpo_age_s": round(age_s, 1),
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # IO helpers (test-overridable)
    # ------------------------------------------------------------------

    def _read_tpo_json(self) -> Optional[dict]:
        if not self.tpo_json_path.exists():
            logger.warning("[tpo_snapshotter] tpo.json missing: %s", self.tpo_json_path)
            return None
        try:
            return json.loads(self.tpo_json_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("[tpo_snapshotter] tpo.json read failed: %s", e)
            return None

    def _tpo_age_s(self) -> float:
        try:
            return time.time() - self.tpo_json_path.stat().st_mtime
        except OSError:
            return float("inf")

    def _upsert_history_row(
        self,
        *,
        ts_str: str,
        poc: float,
        vah: float,
        val: float,
        ib_high: Optional[float],
        ib_low: Optional[float],
    ) -> None:
        """INSERT OR REPLACE — idempotent on ``ts`` via ``ux_v9_tpo_history_ts``."""
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
            "INSERT OR REPLACE INTO v9_tpo_history "
            "(ts, poc, vah, val, ib_high, ib_low, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (ts_str, poc, vah, val, ib_high, ib_low),
        )

    # ------------------------------------------------------------------
    # Slot math (pure functions — exposed for tests)
    # ------------------------------------------------------------------

    @staticmethod
    def slot_start_ts_str(et: datetime) -> str:
        """Format the start of the 30-min slot containing ``et`` as **UTC
        wall-clock**, naive (no TZ suffix).

        Why UTC, not ET (as the original implementation did): the bridge
        §9 fix (`bridge/v9_streams/base_stream.py::_chicago_to_utc`)
        stores ``v9_bars_5min.ts`` as **real UTC** wall-clock strings
        (e.g., RTH open = ``2026-05-22 13:30:00``, not ``09:30:00``).
        The chart's ``tsToUnix`` in ``ChartV5b.tsx`` parses every ts
        string as ET (``-04:00`` suffix), so a bar at UTC ``13:30`` ends
        up at chart-internal unix ``17:30 UTC`` — and a TPO marker at
        ET ``09:30`` ends up at chart-internal ``13:30 UTC``. Both go
        through the same shift, so to align the pink stepped POC line
        with the actual RTH-open candle, the snapshotter must write the
        same UTC wall-clock that the bars use.

        Discovered live during the 16:30 IL RTH UAT on 2026-05-22 — the
        first pink markers landed 4 hours to the left of the RTH-open
        candle. Symmetric bug to the chart's stale ``tsToUnix`` comment.
        """
        utc = et.astimezone(UTC)
        slot_minute = (utc.minute // 30) * 30
        slot_start_utc = utc.replace(minute=slot_minute, second=0, microsecond=0)
        # T-159 TZ fix (cowork 30.08): the old format was naive ("%Y-%m-%d %H:%M:%S")
        # which PG timestamptz interprets in the session TZ (Israel +03), adding
        # a +3h shift. Use ISO with +00:00 so PG stores the correct UTC instant.
        # Median staleness drops from 182min to ~15min.
        return slot_start_utc.strftime("%Y-%m-%d %H:%M:%S+00:00")

    def next_boundary_utc(self, *, ref_et: Optional[datetime] = None) -> datetime:
        """Next 30-min ET wall-clock boundary, returned in UTC for sleep math."""
        et = ref_et if ref_et is not None else now_et()
        slot_minute = (et.minute // 30) * 30
        current_slot_et = et.replace(minute=slot_minute, second=0, microsecond=0)
        next_boundary_et = current_slot_et + timedelta(minutes=self.interval_min)
        return next_boundary_et.astimezone(UTC)


# ----------------------------------------------------------------------
# Module-level singleton — convenient for FastAPI startup wiring + tests
# ----------------------------------------------------------------------

_singleton: Optional[TPOHistorySnapshotter] = None


def get_snapshotter() -> TPOHistorySnapshotter:
    global _singleton
    if _singleton is None:
        _singleton = TPOHistorySnapshotter()
    return _singleton


def reset_singleton_for_tests() -> None:
    """Clear the singleton — used by tests that need a fresh instance."""
    global _singleton
    _singleton = None
