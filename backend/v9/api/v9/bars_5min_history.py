"""GET /api/v9/bars/5min — last N 5-min bars for chart rendering."""
from fastapi import APIRouter, Query
import sqlite3

router = APIRouter(tags=["v9-bars-history"])

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"


@router.get("/api/v9/chart/bars5min")
def get_bars_5min(limit: int = Query(60, le=200)):
    """Return last N 5-min bars, oldest first."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ts, open, high, low, close, volume FROM v9_bars_5min ORDER BY ts DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        bars = [{"ts": r["ts"], "o": r["open"], "h": r["high"], "l": r["low"], "c": r["close"], "v": r["volume"]} for r in reversed(rows)]
        return bars
    except Exception as e:
        return []
