"""SessionBoundaryManager — idempotent daily rollover at 18:00 ET.

Reads last_rollover_date from v9_session_meta. If stale, performs rollover:
  1. Resets DayTypeStateMachine
  2. Resets RiskValidator daily counters
  3. Updates last_rollover_date

Per design doc section 2.2: calling check_rollover() twice on the same day is a no-op.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional, Protocol

from backend.v9.common.trading_date import et_today

logger = logging.getLogger(__name__)


class Resettable(Protocol):
    """Any object with a reset() method."""
    def reset(self) -> None: ...


class DailyResettable(Protocol):
    """Any object with a daily_reset() method."""
    def daily_reset(self) -> None: ...


class SessionBoundaryManager:
    """Manages the 18:00 ET session boundary rollover.

    Args:
        db_path: Path to SQLite database.
        day_type_machine: DayTypeStateMachine instance (has .reset()).
        risk_validator: RiskValidator instance (has .daily_reset()), optional.
    """

    def __init__(
        self,
        db_path: str,
        day_type_machine: Optional[Resettable] = None,
        risk_validator: Optional[DailyResettable] = None,
    ):
        self.db_path = db_path
        self.day_type_machine = day_type_machine
        self.risk_validator = risk_validator
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create v9_session_meta if it doesn't exist."""
        from backend.v9.db.safe_writer import safe_execute
        safe_execute("""
            CREATE TABLE IF NOT EXISTS v9_session_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """, db_path=self.db_path)

    def _get_last_rollover_date(self) -> Optional[date]:
        """Read last_rollover_date from DB."""
        try:
            from backend.v9.db.read import read_scalar
            val = read_scalar(
                "SELECT value FROM v9_session_meta WHERE key = 'last_rollover_date'"
            )
            if val:
                return date.fromisoformat(val)
            return None
        except Exception as e:
            logger.warning("[SessionBoundary] read last_rollover_date failed: %s", e)
            return None

    def _set_last_rollover_date(self, d: date) -> None:
        """Write last_rollover_date to DB (upsert)."""
        from backend.v9.db.safe_writer import safe_execute
        safe_execute(
            """INSERT INTO v9_session_meta (key, value) VALUES ('last_rollover_date', ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (d.isoformat(),),
            db_path=self.db_path,
        )

    def check_rollover(self) -> bool:
        """Check if rollover is needed and perform it if so.

        Returns True if rollover was performed, False if already up-to-date.
        Idempotent: calling twice on the same day is a no-op.

        FIRST RUN (last=None): seed without resetting. A fresh DB or
        test DB should not trigger a state-machine wipe just because
        there is no rollover history yet. (P31.1-T1 fix for Finding #2.)
        """
        today = et_today()
        last = self._get_last_rollover_date()

        # FIRST RUN — no rollover history. Seed and skip.
        if last is None:
            logger.info("[SessionBoundary] first run on %s — seeding (no reset)", today)
            self._set_last_rollover_date(today)
            return False

        # Already rolled over today — no-op.
        if last >= today:
            logger.debug("[SessionBoundary] already rolled over for %s", today)
            return False

        # last < today → real rollover.
        return self._perform_rollover(today)

    def subscribe_to_bar_router(self, bar_router) -> None:
        """First-bar fallback: check rollover on every 5min bar.

        Handles the case where the backend runs through 18:00 ET
        without a restart. Belt-and-suspenders with the startup hook.
        """
        async def _on_bar(event):
            try:
                self.check_rollover()
            except Exception as e:
                logger.warning("[SessionBoundary] first-bar fallback error: %s", e, exc_info=True)
        bar_router.subscribe("5min", _on_bar)
        logger.info("[SessionBoundary] subscribed to 5min via BarRouter (first-bar fallback)")

    def _perform_rollover(self, today: date) -> bool:
        """Execute the rollover sequence.

        Order: archive → truncate → reset machine → reset risk → mark done.
        Per CLAUDE.md Rule 1: archive INSERTs then marks ROLLED_OVER. Never DELETE.
        """
        try:
            logger.info("[SessionBoundary] rollover fired for date=%s", today)

            # 1. ARCHIVE yesterday's data
            archived = self._archive_yesterday(today)
            logger.info("[SessionBoundary] archived: %s", archived)

            # 2. TRUNCATE stale v9_day_type_state rows (>2 days old)
            truncated = self._truncate_stale_state(today)
            logger.info("[SessionBoundary] truncated v9_day_type_state: %d rows", truncated)

            # 3. RESET state machine
            if self.day_type_machine is not None:
                self.day_type_machine.reset()
                logger.info("[SessionBoundary] DayTypeStateMachine reset")

            # 4. RESET risk validator
            if self.risk_validator is not None:
                self.risk_validator.daily_reset()
                logger.info("[SessionBoundary] RiskValidator daily_reset")

            # 5. MARK rollover complete
            self._set_last_rollover_date(today)
            return True

        except Exception as e:
            logger.error("[SessionBoundary] rollover failed: %s", e, exc_info=True)
            return False

    def _archive_yesterday(self, today: date) -> dict:
        """Archive rows with date < today into _archive tables, then mark ROLLED_OVER.

        Never DELETE — per CLAUDE.md Rule 1 (honest data > silent loss).
        """
        counts = {"day_type": 0, "tpo_sessions": 0, "woodies_signals": 0}
        from backend.v9.db.safe_writer import safe_execute
        today_iso = today.isoformat()
        safe_execute("""
            INSERT INTO v9_day_type_archive
              SELECT *, datetime('now') AS archived_at
              FROM v9_day_type_history
              WHERE date < ? AND COALESCE(status, '') != 'ROLLED_OVER'
        """, (today_iso,), db_path=self.db_path)
        safe_execute("""
            UPDATE v9_day_type_history
              SET status = 'ROLLED_OVER'
              WHERE date < ? AND COALESCE(status, '') != 'ROLLED_OVER'
        """, (today_iso,), db_path=self.db_path)
        safe_execute("""
            INSERT INTO v9_tpo_sessions_archive
              (session_id, session_type, trading_date, opened_ts, closed_ts,
               poc_price, vah_price, val_price, range_high, range_low,
               total_volume, profile_shape, opening_type,
               ib_high, ib_low, ib_locked, letter_count, archived_at)
              SELECT session_id, session_type, trading_date, opened_ts, closed_ts,
                     poc_price, vah_price, val_price, range_high, range_low,
                     total_volume, profile_shape, opening_type,
                     ib_high, ib_low, ib_locked, letter_count, datetime('now')
              FROM v9_tpo_sessions
              WHERE trading_date < ?
        """, (today_iso,), db_path=self.db_path)
        safe_execute("""
            INSERT INTO v9_woodies_signals_archive
              SELECT *, datetime('now') AS archived_at
              FROM v9_woodies_signals
              WHERE date(ts) < ?
        """, (today_iso,), db_path=self.db_path)
        return counts

    def _truncate_stale_state(self, today: date) -> int:
        """Delete v9_day_type_state rows older than 2 days."""
        from backend.v9.db.safe_writer import safe_execute
        cutoff = (today - timedelta(days=2)).isoformat()
        safe_execute("DELETE FROM v9_day_type_state WHERE date(ts) < ?", (cutoff,), db_path=self.db_path)
        return 0  # rowcount not available via safe_execute
