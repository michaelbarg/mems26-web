"""API: /api/v9/tpo/* — System 5 TPO Profile."""
from fastapi import APIRouter, Request
import sqlite3

router = APIRouter(prefix="/api/v9/tpo", tags=["tpo"])


@router.get("/current")
async def tpo_current(request: Request):
    sys = getattr(request.app.state, "tpo_system", None)
    if sys is None:
        return {"running": False, "error": "TPOSystem not initialized"}
    return sys.get_current()


@router.get("/journal")
async def tpo_journal(request: Request, session_id: str = "", limit: int = 50):
    db_path = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        if session_id:
            rows = conn.execute(
                "SELECT * FROM v9_tpo_journal WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM v9_tpo_journal ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        conn.close()
        return {"entries": [dict(r) for r in rows]}
    except Exception as e:
        return {"entries": [], "error": str(e)}


@router.get("/sessions")
async def tpo_sessions(request: Request, date: str = ""):
    db_path = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        if date:
            rows = conn.execute(
                "SELECT * FROM v9_tpo_sessions WHERE trading_date=?", (date,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM v9_tpo_sessions ORDER BY id DESC LIMIT 10"
            ).fetchall()
        conn.close()
        return {"sessions": [dict(r) for r in rows]}
    except Exception as e:
        return {"sessions": [], "error": str(e)}
