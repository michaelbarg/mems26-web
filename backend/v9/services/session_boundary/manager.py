"""SessionBoundaryManager — idempotent daily rollover at 18:00 ET.

Reads last_rollover_date from v9_session_meta. If stale, performs rollover:
  1. Resets DayTypeStateMachine
  2. Resets RiskValidator daily counters
  3. Updates last_rollover_date

Per design doc section 2.2: calling check_rollover() twice on the same day is a no-op.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime
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
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS v9_session_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("[SessionBoundary] table creation failed: %s", e)

    def _get_last_rollover_date(self) -> Optional[date]:
        """Read last_rollover_date from DB."""
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT value FROM v9_session_meta WHERE key = 'last_rollover_date'"
            ).fetchone()
            conn.close()
            if row and row[0]:
                return date.fromisoformat(row[0])
            return None
        except Exception as e:
            logger.warning("[SessionBoundary] read last_rollover_date failed: %s", e)
            return None

    def _set_last_rollover_date(self, d: date) -> None:
        """Write last_rollover_date to DB (upsert)."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO v9_session_meta (key, value) VALUES ('last_rollover_date', ?)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                (d.isoformat(),),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("[SessionBoundary] write last_rollover_date failed: %s", e)

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

    def _perform_rollover(self, today: date) -> bool:
        """Execute the rollover sequence.

        1. Reset DayTypeStateMachine
        2. Reset RiskValidator daily counters
        3. Mark last_rollover_date = today
        """
        try:
            logger.info("[SessionBoundary] rollover fired for date=%s", today)

            if self.day_type_machine is not None:
                self.day_type_machine.reset()
                logger.info("[SessionBoundary] DayTypeStateMachine reset")

            if self.risk_validator is not None:
                self.risk_validator.daily_reset()
                logger.info("[SessionBoundary] RiskValidator daily_reset")

            self._set_last_rollover_date(today)
            return True

        except Exception as e:
            logger.error("[SessionBoundary] rollover failed: %s", e, exc_info=True)
            return False
