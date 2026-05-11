"""Day Type hydration stub (D-077).

Minimal hydration: loads existing state from DB.
Full Day Type hydration (PD data, TPO inputs) deferred to PROMPT 5.1
(after TPO Engine exists).
"""

import logging
from datetime import date

from backend.v9.systems.base.trading_system import HydrationResult
from backend.v9.db.session import SessionLocal

logger = logging.getLogger("mems26.systems.day_type")


def hydrate_day_type() -> HydrationResult:
    """Minimal hydration: load today's state from DB if it exists."""
    try:
        from backend.v9.db.models.day_type_history import V9DayTypeHistory
        db = SessionLocal()
        today = date.today()
        latest = (
            db.query(V9DayTypeHistory)
            .filter(V9DayTypeHistory.date == today)
            .first()
        )
        db.close()

        if latest:
            return HydrationResult(
                success=True,
                reached_state=latest.status or "FORMING",
                bars_replayed=0,
                confidence=latest.confidence or 0.0,
                notes="Loaded from DB (full backfill TBD in PROMPT 5.1)",
            )

        return HydrationResult(
            success=True,
            reached_state="A1",
            bars_replayed=0,
            confidence=0.0,
            notes="Fresh start, no prior state for today",
        )
    except Exception as e:
        logger.warning("[DayType] Hydration error: %s", e)
        return HydrationResult(
            success=False,
            reached_state="ERROR",
            error=str(e),
        )
