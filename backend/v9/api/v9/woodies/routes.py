from fastapi import APIRouter, Request
import sqlite3

router = APIRouter(prefix="/api/v9/woodies", tags=["woodies"])


@router.get("/current")
async def woodies_current(request: Request):
    sys = getattr(request.app.state, "woodies_system", None)
    if sys is None:
        return {"running": False, "error": "WoodiesSystem not initialized"}
    return sys.get_current()


@router.get("/signals")
async def woodies_signals(request: Request, limit: int = 20):
    db_path = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM v9_woodies_signals ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return {"entries": [dict(r) for r in rows]}
    except Exception as e:
        return {"entries": [], "error": str(e)}
