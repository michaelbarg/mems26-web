"""P30 G6 — `/api/v9/history/*` — yesterday-replay endpoints.

Backed by `backend.v9.services.eod_archiver`. Filesystem-only — no DB
schema changes required. Cockpit's "Hist" tab consumes `/yesterday`.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.v9.services import eod_archiver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v9/history", tags=["history"])

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.get("/dates")
async def history_dates():
    """List archived trading dates (YYYY-MM-DD), newest first."""
    return {"dates": eod_archiver.list_archived_dates()}


@router.get("/yesterday")
async def history_yesterday():
    """Bundle of yesterday's session exports.

    Uses market_clock.get_previous_trading_day so Saturday → Friday, holidays
    skipped (D-070). Falls back to the most recent archived date if the
    market clock service is unavailable.
    """
    try:
        from backend.v9.services.market_clock import get_previous_trading_day
        prev = get_previous_trading_day().isoformat()
    except Exception as e:
        logger.warning("[history] market_clock unavailable: %s — using newest archive", e)
        dates = eod_archiver.list_archived_dates()
        if not dates:
            raise HTTPException(status_code=404, detail="no archives present")
        prev = dates[0]

    payload = eod_archiver.read_session(prev)
    if not payload.get("available_files"):
        raise HTTPException(
            status_code=404,
            detail=f"no archive for {prev} — run POST /api/v9/history/archive_now first",
        )
    return payload


@router.get("/{date}")
async def history_by_date(date: str):
    """Bundle for an explicit YYYY-MM-DD."""
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    payload = eod_archiver.read_session(date)
    if not payload.get("available_files"):
        raise HTTPException(status_code=404, detail=f"no archive for {date}")
    return payload


@router.post("/archive_now")
async def archive_now(date: Optional[str] = Query(default=None, description="Override ET-today")):
    """Snapshot the current Sierra exports into the archive.

    Idempotent — re-running overwrites the same folder. Schedule via cron:

        # crontab -e (15:55 ET Mon-Fri)
        55 15 * * 1-5  curl -s -X POST http://localhost:8000/api/v9/history/archive_now
    """
    if date is not None and not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    return eod_archiver.archive_today(target_date=date)
