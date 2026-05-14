"""API route for Behavior Phase (Layer 2 advisory)."""
from fastapi import APIRouter
from .phase_detector import detect_phase

router = APIRouter(prefix="/api/v9/behavior_phase", tags=["behavior-phase"])


@router.get("/current")
async def behavior_phase_current():
    """Current behavior phase classification (advisory, not firing)."""
    import requests
    bars = []
    ib_high = ib_low = poc = None

    try:
        resp = requests.get("http://localhost:8000/api/v9/chart/bars5min?limit=20", timeout=3)
        if resp.ok:
            bars = resp.json() if isinstance(resp.json(), list) else []
    except Exception:
        pass

    try:
        tpo = requests.get("http://localhost:8000/api/v9/tpo/current", timeout=2).json()
        ib_high = tpo.get("ib_high")
        ib_low = tpo.get("ib_low")
        poc = tpo.get("poc")
    except Exception:
        pass

    result = detect_phase(bars, ib_high=ib_high, ib_low=ib_low, poc=poc)
    return {
        "phase": result.phase.value,
        "confidence": result.confidence,
        "reasoning_notes": result.reasoning_notes,
        "indicators": result.indicators,
    }
