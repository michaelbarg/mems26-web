"""5-min System API endpoints.

All handlers read from app.state.five_min_system — the single instance
created by backend.main, hydrated, and wired to BarRouter.  Never create
a separate FiveMinSystem here.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v9/five_min", tags=["v9-five-min"])


def _get_system(request: Request):
    """Return the live FiveMinSystem or None."""
    return getattr(request.app.state, "five_min_system", None)


@router.get("/current")
def get_current(request: Request):
    """Current 5-min system state."""
    sys = _get_system(request)
    if sys is None:
        return JSONResponse(
            status_code=503,
            content={"error": "FiveMinSystem not initialized"},
        )
    return sys.get_state()


@router.get("/setups")
def get_setups():
    """Recent setups (placeholder — will populate from DB)."""
    return {"setups": [], "count": 0}


@router.get("/fire")
def get_fire(request: Request):
    """Latest fire state — last pattern detection result."""
    sys = _get_system(request)
    if sys is None:
        return JSONResponse(
            status_code=503,
            content={"error": "FiveMinSystem not initialized"},
        )
    state = sys.get_state()
    return {
        "fired": state.get("last_pattern") is not None,
        "pattern": state.get("last_pattern"),
        "confluence": state.get("last_confluence", 0),
        "mode": state.get("mode"),
        "reasoning_notes": sys.current_state.get("last_reasoning_notes", "")
            if hasattr(sys, 'current_state') and isinstance(getattr(sys, 'current_state', None), dict) else "",
    }


@router.get("/stats")
def get_stats(request: Request):
    """System counters."""
    sys = _get_system(request)
    if sys is None:
        return JSONResponse(
            status_code=503,
            content={"error": "FiveMinSystem not initialized"},
        )
    return {
        "mode": sys.mode,
        "buffer_size": sys.buffer_size,
        "patterns_detected": 0,
        "setups_published": 0,
    }
