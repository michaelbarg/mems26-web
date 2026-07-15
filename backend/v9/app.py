"""MEMS26 V9 FastAPI application.

Can be run standalone OR mounted into the unified backend (backend.main).
"""

import logging
from typing import Optional

from fastapi import APIRouter, FastAPI, Request
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
from backend.v9.api.v9.pre_fire_routes import router as pre_fire_router
from backend.v9.systems.behavior_phase.routes import router as behavior_phase_router
from backend.v9.api.v9.price_routes import router as price_api_router
from backend.v9.api.v9.clock_routes import router as clock_api_router
from backend.v9.api.v9.open_type_routes import router as open_type_api_router
from backend.v9.api.v9.day_type_v9_routes import router as day_type_v9_router
from backend.v9.api.v9.cumulative_delta_routes import router as cvd_api_router
from backend.v9.api.v9.woodies_chart_routes import router as woodies_chart_router
from backend.v9.api.v9.history_routes import router as history_api_router
from backend.v9.api.v9.admin_routes import router as admin_api_router
from backend.v9.api.v9.build_status_routes import router as build_status_router
from backend.v9.api.v9.key_levels_routes import router as key_levels_router
from backend.v9.api.v9.chart_replay_routes import router as chart_replay_router
from backend.v9.api.v9.trade_review_routes import router as trade_review_router
from backend.v9.api.v9.daytype_classify_routes import router as daytype_classify_router
from backend.v9.api.v9.system6_routes import router as system6_router, alias_router as system6_alias_router
from backend.v9.api.v9.live_ledger_routes import router as live_ledger_router
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
v9_router.include_router(pre_fire_router)
v9_router.include_router(behavior_phase_router)
v9_router.include_router(price_api_router)
v9_router.include_router(clock_api_router)
v9_router.include_router(open_type_api_router)
v9_router.include_router(day_type_v9_router)
v9_router.include_router(system6_router)
v9_router.include_router(system6_alias_router)  # /api/v9/s6 alias for ActiveTradeCard
v9_router.include_router(live_ledger_router)
v9_router.include_router(cvd_api_router)
v9_router.include_router(woodies_chart_router)
v9_router.include_router(history_api_router)
v9_router.include_router(admin_api_router)
v9_router.include_router(build_status_router)
v9_router.include_router(key_levels_router)
v9_router.include_router(chart_replay_router)
v9_router.include_router(trade_review_router)
v9_router.include_router(daytype_classify_router)
from backend.v9.api.v9.kill_switch_routes import router as kill_switch_router
v9_router.include_router(kill_switch_router)
# In-dashboard Claude chat (Michael 07-12) — grounded in live system context;
# requires ANTHROPIC_API_KEY in .env (out-of-git), honest 503 without it.
from backend.v9.api.v9.agent_chat import router as agent_chat_router
v9_router.include_router(agent_chat_router)

# T1 (Michael 07-14): read-only Sierra live-detection check (pre-live gate).
from backend.v9.api.v9.sierra_live_check import router as sierra_live_check_router
v9_router.include_router(sierra_live_check_router)


@v9_router.get("/api/v9/health")
async def v9_health():
    return {"status": "ok", "version": "v9.0.0"}


@v9_router.get("/api/v9/cockpit/heartbeat")
async def cockpit_heartbeat():
    """Lightweight heartbeat for cockpit UI — no Redis, no external calls.

    Returns cheap local truth only: backend alive, mode, timestamp,
    live_price file age, and WS client count (all in-memory).
    Target: <20ms.
    """
    import os
    import time
    from backend.v9.ws.manager import price_ws_manager

    mode = os.getenv("MEMS26_MODE", "shadow")
    now = time.time()

    # Live price file age (cheap stat call, no file read)
    live_price_path = os.path.join(
        os.getenv("V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export"),
        "live_price.json",
    )
    try:
        price_file_age_ms = int((now - os.path.getmtime(live_price_path)) * 1000)
    except OSError:
        price_file_age_ms = -1  # file missing

    return {
        "alive": True,
        "mode": mode,
        "ts": now,
        "price_file_age_ms": price_file_age_ms,
        "ws_clients": len(price_ws_manager._clients),
    }


def _health_from_running(running: bool) -> str:
    return "healthy" if running else "unknown"


def _system_payload(
    system_id: int,
    name: str,
    *,
    state=None,
    sub_state=None,
    confidence: float = 0,
    health: str = "unknown",
    raw: Optional[dict] = None,
) -> dict:
    return {
        "id": system_id,
        "name": name,
        "state": state,
        "subState": sub_state,
        "confidence": confidence,
        "health": health,
        "raw": raw or {},
    }


@v9_router.get("/api/v9/cockpit/systems-snapshot")
async def cockpit_systems_snapshot(request: Request):
    """Single lightweight snapshot for S1-S6 cockpit state polling.

    No Redis, no Upstash, no HTTP self-calls, and no /api/v9/status dependency.
    This replaces the frontend's 12-request polling batch with one local read.
    """
    import time

    systems = {
        1: _system_payload(1, "Day Type"),
        2: _system_payload(2, "5-Min"),
        3: _system_payload(3, "Footprint"),
        4: _system_payload(4, "Woodies"),
        5: _system_payload(5, "TPO"),
        6: _system_payload(6, "Killzone"),
    }

    try:
        day_type_machine = getattr(request.app.state, "day_type_machine", None)
        if day_type_machine is not None:
            classification = day_type_machine.to_classification()
            if classification is not None:
                raw = {
                    "day_type": classification.day_type.value,
                    "probability": classification.probability,
                    "directional_certainty": classification.directional_certainty,
                    "trading_confidence": classification.trading_confidence,
                }
                systems[1] = _system_payload(
                    1,
                    "Day Type",
                    state=raw["day_type"],
                    confidence=raw["probability"] or 0,
                    health="healthy",
                    raw=raw,
                )
    except Exception:
        pass

    try:
        sys = getattr(request.app.state, "five_min_system", None)
        if sys is not None:
            current = sys.get_state()
            systems[2] = _system_payload(
                2,
                "5-Min",
                state=current.get("last_pattern") or current.get("mode") or "UNKNOWN",
                sub_state=current.get("mode"),
                confidence=(current.get("last_confluence") or 0) / 4,
                health=_health_from_running(bool(current.get("running", True))),
                raw=current,
            )
    except Exception:
        pass

    try:
        sys = getattr(request.app.state, "footprint_system", None)
        if sys is not None:
            current = sys.get_current()
            systems[3] = _system_payload(
                3,
                "Footprint",
                state=current.get("dominance") or current.get("combined_class") or current.get("last_classification") or "NO_SETUP",
                sub_state=current.get("initiative_type"),
                confidence=(current.get("last_confluence") or 0) / 10,
                health=_health_from_running(bool(current.get("running", True))),
                raw=current,
            )
    except Exception:
        pass

    try:
        sys = getattr(request.app.state, "woodies_system", None)
        if sys is not None:
            current = sys.get_current()
            patterns = current.get("active_patterns")
            top_pattern = patterns[0].get("pattern_id") if isinstance(patterns, list) and patterns else None
            systems[4] = _system_payload(
                4,
                "Woodies",
                state=top_pattern or current.get("last_signal_type") or current.get("signal") or "NEUTRAL",
                sub_state=current.get("direction"),
                confidence=(current.get("strength") or 0) / 3,
                health=_health_from_running(bool(current.get("running", True))),
                raw=current,
            )
    except Exception:
        pass

    try:
        sys = getattr(request.app.state, "tpo_system", None)
        if sys is not None:
            current = sys.get_current()
            migration = current.get("poc_migration") or {}
            systems[5] = _system_payload(
                5,
                "TPO",
                state=migration.get("direction") or current.get("profile_shape") or "NA",
                sub_state=current.get("session_type"),
                confidence=min((current.get("letter_count") or 0) / 13, 1),
                health=_health_from_running(bool(current.get("running", True))),
                raw=current,
            )
    except Exception:
        pass

    try:
        sys = getattr(request.app.state, "killzone_system", None)
        if sys is not None:
            current = sys.get_current()
            zone = current.get("current_zone") or {}
            edge_class = zone.get("edge_class")
            systems[6] = _system_payload(
                6,
                "Killzone",
                state=zone.get("name") or "UNKNOWN",
                sub_state=edge_class,
                confidence=1 if edge_class == "high" else 0.5 if edge_class == "medium" else 0.2,
                health=_health_from_running(bool(current.get("running", True))),
                raw=current,
            )
    except Exception:
        pass

    return {
        "ts": time.time(),
        "systems": systems,
        "count": len(systems),
    }


# ── EventDispatcher initialization ──────────────────────────────

def init_event_dispatcher(gateway=None):
    """Initialize EventDispatcher with all 5 systems and wire into bars API.

    Called at startup (from backend.main or standalone).
    Returns the dispatcher instance for inspection/testing.
    """
    from backend.v9.services.event_dispatcher import EventDispatcher
    from backend.v9.services.stream_health import StreamHealthService
    from backend.v9.systems.wrappers import (
        DayTypeSystem, TickReversalSystem,
        WoodiesSystem, TPOSystem, KillzoneSystem,
    )
    from backend.v9.api.v9.bars import set_event_dispatcher, set_stream_health
    from backend.v9.api.v9.health_streams import set_stream_health_service

    # Initialize StreamHealthService (in-memory singleton)
    stream_health = StreamHealthService()
    app.state.stream_health_service = stream_health  # T2: feed watchdog reads this

    dispatcher = EventDispatcher(gateway=gateway)
    dispatcher.set_stream_health(stream_health)

    # Register all 5 systems (Chart5MinSystem removed per D-090)
    systems = [
        DayTypeSystem(),
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

    # Frozen-tail watchdog (detect + alert, read-only)
    import asyncio
    from backend.v9.services.frozen_tail_watchdog import run_watchdog_loop
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(run_watchdog_loop())
        logger.info("[V9] Frozen-tail watchdog task scheduled")
    except RuntimeError:
        logger.warning("[V9] No event loop — frozen-tail watchdog not started (OK in tests)")
