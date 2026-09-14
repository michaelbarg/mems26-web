"""T-320: GET /api/v9/chart/setup_markers — read-only setup markers for chart.

Returns setups from v9_trades (all modes) for a given session date.
No writes, no computation — just reads what the gateway already recorded.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from zoneinfo import ZoneInfo

from backend.v9.db.read import read_all

logger = logging.getLogger("mems26.chart_setup_markers")

router = APIRouter(tags=["v9-chart"])

ET = ZoneInfo("America/New_York")
IL = ZoneInfo("Asia/Jerusalem")


@router.get("/api/v9/chart/setup_markers")
def get_setup_markers(session: Optional[str] = Query(None)):
    """Return setup markers for chart overlay.

    Each row from v9_trades becomes one marker with state, blocked_by, etc.
    """
    if not session:
        session = datetime.now(IL).strftime("%Y-%m-%d")

    # Session window: ET date 09:30 → next day 00:00
    try:
        d = datetime.strptime(session, "%Y-%m-%d")
    except ValueError:
        return []

    # Broad window to capture the session (Globex open through EOD)
    start = datetime(d.year, d.month, d.day, 9, 0, tzinfo=ET)
    end = start + timedelta(hours=15)

    rows = read_all(
        "SELECT id, mode, firing_system, direction, state, "
        "entry_ts, entry_price, stop, t1, t2, t3, "
        "pattern_id_at_entry, quality, created_at "
        "FROM v9_trades "
        "WHERE created_at >= :start AND created_at < :end "
        "ORDER BY created_at",
        {"start": start.isoformat(), "end": end.isoformat()},
    )

    markers = []
    for r in rows:
        q = {}
        if r.get("quality"):
            try:
                q = json.loads(r["quality"]) if isinstance(r["quality"], str) else (r["quality"] or {})
            except (json.JSONDecodeError, TypeError):
                pass
        meta = q.get("metadata") or {}

        blocked_by = q.get("blocked_by") or meta.get("blocked_by") or meta.get("shadow_blocked_by")
        reason = q.get("block_reason") or meta.get("block_reason")
        shadow_only = bool(meta.get("shadow_only") or r.get("mode") == "shadow")
        classification = (q.get("trigger") or q.get("classification")
                          or r.get("pattern_id_at_entry") or "")

        # Determine state
        mode = r.get("mode") or ""
        db_state = r.get("state") or ""
        if meta.get("shadow_blocked"):
            state = "blocked"
            blocked_by = blocked_by or meta.get("blocked_by")
        elif blocked_by:
            state = "blocked"
        elif db_state in ("CANCELLED",):
            state = "blocked"
        elif mode in ("live", "demo") and db_state != "CANCELLED":
            state = "fired"
        elif mode == "shadow" and not meta.get("shadow_blocked"):
            state = "armed"
        else:
            state = "armed"

        ts = r.get("entry_ts") or r.get("created_at")
        price = r.get("entry_price")

        markers.append({
            "ts": ts.isoformat() if hasattr(ts, "isoformat") else str(ts) if ts else None,
            "price": float(price) if price is not None else None,
            "system": r.get("firing_system"),
            "classification": classification,
            "direction": r.get("direction"),
            "state": state,
            "blocked_by": blocked_by,
            "reason": reason,
            "stop": float(r["stop"]) if r.get("stop") is not None else None,
            "t1": float(r["t1"]) if r.get("t1") is not None else None,
            "t2": float(r["t2"]) if r.get("t2") is not None else None,
            "t3": float(r["t3"]) if r.get("t3") is not None else None,
            "shadow_only": shadow_only,
        })

    return markers
