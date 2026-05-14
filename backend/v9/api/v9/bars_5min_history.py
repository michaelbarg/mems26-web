"""GET /api/v9/chart/bars5min — 5-min bars for chart rendering.

Supports cursor-based pagination via ?before=<ts> for pan-to-load (Wave A1.5).
"""
from typing import Optional
from fastapi import APIRouter, Query
import sqlite3

router = APIRouter(tags=["v9-bars-history"])

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"


@router.get("/api/v9/chart/bars5min")
def get_bars_5min(
    limit: int = Query(60, le=200),
    before: Optional[str] = Query(None, description="ISO timestamp — fetch bars BEFORE this ts"),
):
    """Return 5-min bars, oldest first.

    Without 'before': latest N bars.
    With 'before': N bars older than the given timestamp (for pan-to-load).
    """
    limit = min(max(limit, 1), 200)
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        if before:
            rows = conn.execute(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min WHERE ts < ? ORDER BY ts DESC LIMIT ?",
                (before, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        bars = [{"ts": r["ts"], "o": r["open"], "h": r["high"], "l": r["low"], "c": r["close"], "v": r["volume"]} for r in reversed(rows)]
        return bars
    except Exception:
        return []
