"""MEMS26 V9 FastAPI application.

Can be run standalone OR mounted into the unified backend (backend.main).
"""

from fastapi import APIRouter, FastAPI
from backend.v9.api.v9 import bars, signals, markers, trades, configs, websocket

# ── Composite router (used by backend.main for mounting) ──
v9_router = APIRouter()
v9_router.include_router(bars.router)
v9_router.include_router(signals.router)
v9_router.include_router(markers.router)
v9_router.include_router(trades.router)
v9_router.include_router(configs.router)
v9_router.include_router(websocket.router)


@v9_router.get("/api/v9/health")
def v9_health():
    return {"status": "ok", "version": "v9.0.0"}


# ── Standalone app (python -m backend.v9.app) ──
app = FastAPI(title="MEMS26 V9", version="9.0.0")
app.include_router(v9_router)
