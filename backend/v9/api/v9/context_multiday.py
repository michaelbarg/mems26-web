"""GET /api/v9/context/multiday — the 7-day Dalton context (plan 02.08 §B).

Computed from canonical bars (v9_bars_5min_woodies) via multiday_profile;
zero Sierra dependencies. Cached 5 minutes — this is session-scale context,
not tick data. Suspect (pre-cleanup) dates are flagged, never hidden (Rule 1).
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v9/context", tags=["v9-context"])

_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None}
_CACHE_TTL_S = 300
# bars before the 07-30 pipeline cleanup carry known twin/seam contamination
_SUSPECT_BEFORE = "2026-07-30"


def _compute() -> Dict[str, Any]:
    from backend.v9.db.read import read_all
    from backend.v9.systems.multiday_profile import build_context

    days: List[str] = [r["d"].isoformat() for r in read_all(
        "SELECT DISTINCT (ts AT TIME ZONE 'America/New_York')::date AS d "
        "FROM v9_bars_5min_woodies "
        "WHERE ts < date_trunc('day', now() AT TIME ZONE 'America/New_York') "
        "      AT TIME ZONE 'America/New_York' "
        "ORDER BY d DESC LIMIT 8", {})][::-1][-7:]

    sessions = []
    for d in days:
        sessions.append(list(read_all(
            f"SELECT open o, high h, low l, close c FROM v9_bars_5min_woodies "
            f"WHERE (ts AT TIME ZONE 'Asia/Jerusalem') >= '{d} 16:30:00' "
            f"AND (ts AT TIME ZONE 'Asia/Jerusalem') < '{d} 23:00:00' "
            f"ORDER BY ts", {})))

    # today's open (first RTH bar today), when the session has started
    today_open = None
    row = read_all(
        "SELECT open FROM v9_bars_5min_woodies "
        "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
        "(now() AT TIME ZONE 'America/New_York')::date "
        "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
        "ORDER BY ts LIMIT 1", {})
    if row:
        today_open = float(row[0]["open"])

    ctx = build_context(sessions, today_open=today_open,
                        suspect_dates=[d for d in days if d < _SUSPECT_BEFORE])
    ctx["dates"] = days
    return ctx


@router.get("/multiday")
def multiday() -> Dict[str, Any]:
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < _CACHE_TTL_S:
        return _CACHE["data"]
    try:
        data = _compute()
        data["computed_ts"] = now
        _CACHE.update(ts=now, data=data)
        return data
    except Exception as exc:
        logger.warning("[multiday] compute failed: %s", exc)
        return {"error": str(exc)[:120], "composite": None, "n_days_used": 0}
