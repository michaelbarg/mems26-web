"""API routes for 15-tick reversal bar enrichment (P-15TR.5)."""

from fastapi import APIRouter, Request
import sqlite3

router = APIRouter(prefix="/api/v9/reversal", tags=["reversal"])

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"


@router.get("/current")
async def reversal_current(request: Request):
    """Return latest reversal bar enrichment (cluster + empty zone)."""
    handler = getattr(request.app.state, "reversal_handler", None)
    if handler is None:
        return {"running": False, "error": "ReversalBarHandler not initialized"}
    return handler.get_current()


@router.get("/history")
async def reversal_history(limit: int = 20):
    """Return recent reversal enrichment records."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM v9_reversal_enrichment ORDER BY bar_ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return {"entries": [dict(r) for r in rows]}
    except Exception as e:
        return {"entries": [], "error": str(e)}
