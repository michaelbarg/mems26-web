"""API: /api/v9/footprint/* — System 3 status and journal."""
from fastapi import APIRouter, Request

from backend.v9.db.read import read_all

router = APIRouter(prefix="/api/v9/footprint", tags=["footprint"])


@router.get("/current")
async def footprint_current(request: Request):
    sys = getattr(request.app.state, "footprint_system", None)
    if sys is None:
        return {"running": False, "error": "FootprintSystem not initialized"}
    return sys.get_current()


@router.get("/fire")
async def footprint_fire(request: Request):
    """Latest fire state from T3 signals (absorption / stacked_imbalance / sweep_return / exhaustion)."""
    sys = getattr(request.app.state, "footprint_system", None)
    if sys is None:
        return {"fired": False, "error": "FootprintSystem not initialized"}
    state = sys.get_current()
    last_fire = state.get("last_fire")
    return {"fired": last_fire is not None, "fire": last_fire}


@router.get("/journal")
async def footprint_journal(request: Request, limit: int = 20):
    try:
        rows = read_all(
            "SELECT * FROM v9_footprint_journal ORDER BY id DESC LIMIT :limit",
            {"limit": limit},
        )
        return {"entries": rows}
    except Exception as e:
        return {"entries": [], "error": str(e)}
