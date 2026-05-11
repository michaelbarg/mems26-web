"""MEMS26 V9 FastAPI application.

Can be run standalone OR mounted into the unified backend (backend.main).
"""

import logging

from fastapi import APIRouter, FastAPI
from backend.v9.api.v9 import bars, signals, markers, trades, configs, websocket

logger = logging.getLogger(__name__)

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


# ── EventDispatcher initialization ──────────────────────────────

def init_event_dispatcher(gateway=None):
    """Initialize EventDispatcher with all 6 systems and wire into bars API.

    Called at startup (from backend.main or standalone).
    Returns the dispatcher instance for inspection/testing.
    """
    from backend.v9.services.event_dispatcher import EventDispatcher
    from backend.v9.systems.wrappers import (
        DayTypeSystem, Chart5MinSystem, TickReversalSystem,
        WoodiesSystem, TPOSystem, KillzoneSystem,
    )
    from backend.v9.api.v9.bars import set_event_dispatcher

    dispatcher = EventDispatcher(gateway=gateway)

    # Register all 6 systems
    systems = [
        DayTypeSystem(),
        Chart5MinSystem(),
        TickReversalSystem(),
        WoodiesSystem(),
        TPOSystem(),
        KillzoneSystem(),
    ]
    for system in systems:
        dispatcher.register_system(system)

    # Inject into bars API module
    set_event_dispatcher(dispatcher)

    routing = dispatcher.get_routing_table()
    registered = dispatcher.get_registered_systems()
    logger.info(
        "[V9] EventDispatcher initialized: %d systems, %d streams",
        len(registered), len(routing),
    )
    for stream, sys_ids in routing.items():
        logger.info("[V9]   %s -> systems %s", stream, sys_ids)

    return dispatcher


# ── Standalone app (python -m backend.v9.app) ──
app = FastAPI(title="MEMS26 V9", version="9.0.0")
app.include_router(v9_router)


@app.on_event("startup")
def _startup_event_dispatcher():
    """Initialize EventDispatcher when running standalone."""
    init_event_dispatcher()
