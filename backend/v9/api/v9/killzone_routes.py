"""API: /api/v9/killzone/* — System 6 Killzone."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v9/killzone", tags=["killzone"])


@router.get("/current")
async def killzone_current(request: Request):
    sys = getattr(request.app.state, "killzone_system", None)
    if sys is None:
        return {"running": False, "error": "KillzoneSystem not initialized"}
    return sys.get_current()
