"""MEMS26 V9 FastAPI application.

Can be run standalone OR mounted into the unified backend (backend.main).
"""

import logging

from fastapi import APIRouter, FastAPI
from backend.v9.api.v9 import bars, signals, markers, trades, configs, websocket, health_streams, trade_commands, status, audit, spec_compliance
from backend.v9.systems.day_type.api import router as day_type_router
from backend.v9.api.v9.five_min.routes import router as five_min_router
from backend.v9.api.v9.footprint.routes import router as footprint_router
from backend.v9.api.v9.woodies.routes import router as woodies_router
from backend.v9.api.v9.tpo_routes import router as tpo_api_router
from backend.v9.api.v9.killzone_routes import router as killzone_api_router
from backend.v9.api.v9.bars_5min_history import router as bars_5min_history_router
from backend.v9.api.v9.reversal_routes import router as reversal_api_router
from backend.v9.api.v9.chop_score_routes import router as chop_score_router
from backend.v9.api.v9.gateway_routes import router as gateway_api_router
from backend.v9.api.v9.shadow_routes import router as shadow_api_router
from backend.v9.ws.router import router as ws_event_bus_router

logger = logging.getLogger(__name__)

# ── Composite router (used by backend.main for mounting) ──
v9_router = APIRouter()
v9_router.include_router(bars.router)
v9_router.include_router(signals.router)
v9_router.include_router(markers.router)
v9_router.include_router(trades.router)
v9_router.include_router(configs.router)
v9_router.include_router(websocket.router)
v9_router.include_router(health_streams.router)
v9_router.include_router(trade_commands.router)
v9_router.include_router(ws_event_bus_router)
v9_router.include_router(status.router)
v9_router.include_router(audit.router)
v9_router.include_router(spec_compliance.router)
v9_router.include_router(day_type_router)
v9_router.include_router(five_min_router)
v9_router.include_router(footprint_router)
v9_router.include_router(woodies_router)
v9_router.include_router(tpo_api_router)
v9_router.include_router(killzone_api_router)
v9_router.include_router(bars_5min_history_router)
v9_router.include_router(reversal_api_router)
v9_router.include_router(chop_score_router)
v9_router.include_router(gateway_api_router)
v9_router.include_router(shadow_api_router)


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
    from backend.v9.services.stream_health import StreamHealthService
    from backend.v9.systems.wrappers import (
        DayTypeSystem, Chart5MinSystem, TickReversalSystem,
        WoodiesSystem, TPOSystem, KillzoneSystem,
    )
    from backend.v9.api.v9.bars import set_event_dispatcher, set_stream_health
    from backend.v9.api.v9.health_streams import set_stream_health_service

    # Initialize StreamHealthService (in-memory singleton)
    stream_health = StreamHealthService()

    dispatcher = EventDispatcher(gateway=gateway)
    dispatcher.set_stream_health(stream_health)

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
    set_stream_health(stream_health)

    # Inject into health_streams API module
    set_stream_health_service(stream_health)

    # Populate subscribed_systems from routing table
    routing = dispatcher.get_routing_table()
    for stream_name, sys_ids in routing.items():
        stream_health.set_subscribed_systems(stream_name, sys_ids)

    registered = dispatcher.get_registered_systems()
    logger.info(
        "[V9] EventDispatcher initialized: %d systems, %d streams",
        len(registered), len(routing),
    )
    for stream, sys_ids in routing.items():
        logger.info("[V9]   %s -> systems %s", stream, sys_ids)

    logger.info("[V9] StreamHealthService initialized: tracking %d streams", 10)

    return dispatcher


# ── Standalone app (python -m backend.v9.app) ──
app = FastAPI(title="MEMS26 V9", version="9.0.0")
app.include_router(v9_router)


@app.on_event("startup")
def _startup():
    """Initialize EventDispatcher + BarIngestionService when running standalone."""
    init_event_dispatcher()

    # Start Bar Ingestion (D-077: must run before system hydration)
    from backend.v9.services.bar_ingestion import bar_ingestion_service
    bar_ingestion_service.start()
    logger.info("[V9] BarIngestionService started: running=%s", bar_ingestion_service.is_running)
