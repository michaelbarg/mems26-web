"""5-min System API endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v9/five_min", tags=["v9-five-min"])

# Module-level system instance
_system = None


def _get_system():
    global _system
    if _system is None:
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        _system = FiveMinSystem()
        _system.hydrate()
    return _system


@router.get("/current")
def get_current():
    """Current 5-min system state."""
    return _get_system().get_state()


@router.get("/setups")
def get_setups():
    """Recent setups (placeholder — will populate from DB)."""
    return {"setups": [], "count": 0}


@router.get("/fire")
def get_fire():
    """Latest fire state — last pattern detection result."""
    sys = _get_system()
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
def get_stats():
    """System counters."""
    sys = _get_system()
    return {
        "mode": sys.mode,
        "buffer_size": sys.buffer_size,
        "patterns_detected": 0,
        "setups_published": 0,
    }
