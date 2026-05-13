"""MEMS26 unified backend — serves V8-compatible routes + V9 API.

Entry point for Render:
    web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""

import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.v9.app import v9_router, init_event_dispatcher

# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="MEMS26",
    version="9.0.0",
    description="Unified backend: V8 compat + V9 trading API",
)

# ── CORS ─────────────────────────────────────────────────────

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount V9 routes ──────────────────────────────────────────

app.include_router(v9_router)


@app.on_event("startup")
async def _startup():
    """Initialize EventDispatcher + BarIngestionService at unified app startup."""
    import logging
    _logger = logging.getLogger("mems26")

    init_event_dispatcher()

    # Start Bar Ingestion (D-077: must run before system hydration)
    from backend.v9.services.bar_ingestion import bar_ingestion_service
    bar_ingestion_service.start()
    _logger.info("[Main] BarIngestionService started: running=%s", bar_ingestion_service.is_running)

    # Start 5-min Bar Aggregator (Principle 10: data-driven, always-on)
    from backend.v9.services.bar_aggregator_5min import five_min_aggregator
    _logger.info("[Main] FiveMinAggregator initialized: bars_closed=%d", five_min_aggregator.bars_closed)

    # BarRouter: central bar distribution (D1.6)
    from backend.v9.services.bar_router import BarRouter
    bar_router = BarRouter()
    app.state.bar_router = bar_router

    # Wire BarRouter into bars API module
    from backend.v9.api.v9.bars import set_bar_router
    set_bar_router(bar_router)

    # Subscribe 5-min aggregator to tick_reversal_15 via BarRouter
    bar_router.subscribe("tick_reversal_15", five_min_aggregator.on_bar_event)

    # D1.9.3: Instantiate + register systems via BarRouter
    try:
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        five_min_system = FiveMinSystem()
        app.state.five_min_system = five_min_system
        five_min_system.hydrate()
        for bt in five_min_system.subscribed_bar_types():
            bar_router.subscribe(bt, five_min_system.process_bar)
        _logger.info("[Main] FiveMinSystem hydrated + subscribed: %s", five_min_system.subscribed_bar_types())
    except Exception as e:
        _logger.error("[Main] FiveMinSystem startup failed: %s", e)

    # 6.4: Instantiate + register FootprintSystem via BarRouter
    try:
        from backend.v9.systems.footprint.footprint_system import FootprintSystem
        footprint_system = FootprintSystem()
        app.state.footprint_system = footprint_system
        footprint_system.hydrate()
        for bt in footprint_system.subscribed_bar_types():
            bar_router.subscribe(bt, footprint_system.process_bar)
        _logger.info("[Main] FootprintSystem hydrated + subscribed: %s", footprint_system.subscribed_bar_types())
    except Exception as e:
        _logger.error("[Main] FootprintSystem startup failed: %s", e)

    # 7.4: Instantiate + register WoodiesSystem via BarRouter
    try:
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem
        woodies_system = WoodiesSystem()
        app.state.woodies_system = woodies_system
        woodies_system.hydrate()
        for bt in woodies_system.subscribed_bar_types():
            bar_router.subscribe(bt, woodies_system.process_bar)
        _logger.info("[Main] WoodiesSystem hydrated + subscribed: %s", woodies_system.subscribed_bar_types())
    except Exception as e:
        _logger.error("[Main] WoodiesSystem startup failed: %s", e)

    # 8.3: Instantiate + register TPOSystem via BarRouter
    try:
        from backend.v9.systems.tpo.tpo_system import TPOSystem
        tpo_system = TPOSystem()
        app.state.tpo_system = tpo_system
        tpo_system.hydrate()
        for bt in tpo_system.subscribed_bar_types():
            bar_router.subscribe(bt, tpo_system.process_bar)
        _logger.info("[Main] TPOSystem hydrated + subscribed: %s", tpo_system.subscribed_bar_types())
    except Exception as e:
        _logger.error("[Main] TPOSystem startup failed: %s", e)

    # P5.1.2: Subscribe DayTypeStateMachine to BarRouter 5min
    try:
        from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
        from backend.v9.systems.day_type.schemas import BarInput
        import time as _time_mod

        day_type_machine = DayTypeStateMachine()
        app.state.day_type_machine = day_type_machine
        _prev_day_type = {"value": "UNKNOWN"}  # mutable for closure

        async def _day_type_on_bar(event):
            """Bridge BarRouter event to DayTypeStateMachine.process_bar."""
            bar = event.payload if hasattr(event, 'payload') else event
            try:
                # Read IB from TPO state (P5.1.3: single source of truth)
                tpo_sys = getattr(app.state, 'tpo_system', None)
                ib_h = tpo_sys.ib_high if tpo_sys else None
                ib_l = tpo_sys.ib_low if tpo_sys else None

                # Read opening type from TPO (P5.1.4)
                opening_type = "UNKNOWN"
                if tpo_sys:
                    tpo_state = tpo_sys.get_current()
                    opening_type = tpo_state.get("opening_type", "NA")

                bar_input = BarInput(
                    ts=_time_mod.time(),
                    session_min=0,  # computed by state machine internally
                    open=float(bar.get("open", bar.get("o", 0))),
                    high=float(bar.get("high", bar.get("h", 0))),
                    low=float(bar.get("low", bar.get("l", 0))),
                    close=float(bar.get("close", bar.get("c", 0))),
                    volume=float(bar.get("volume", bar.get("v", 0))),
                    ib_high=ib_h,
                    ib_low=ib_l,
                )
                state = day_type_machine.process_bar(bar_input)

                # Persist to v9_day_type_state (P5.1.2)
                try:
                    import sqlite3
                    from datetime import datetime, timezone
                    conn = sqlite3.connect("/Users/michael/Downloads/mems26_web_git/data/mems26_local.db")
                    conn.execute(
                        """INSERT INTO v9_day_type_state (ts, stage, day_type, classification, confidence,
                           ib_width_class, opening_type, behavior, lock_state, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            datetime.now(timezone.utc).isoformat(),
                            state.stage.value if hasattr(state.stage, 'value') else str(state.stage),
                            state.day_type.value if hasattr(state.day_type, 'value') else str(state.day_type),
                            state.day_type.value if state.lock_state == "LOCKED" else None,
                            state.confidence,
                            state.ib_width.value if hasattr(state.ib_width, 'value') else None,
                            opening_type,
                            state.behavior.value if hasattr(state.behavior, 'value') else None,
                            state.lock_state.value if hasattr(state.lock_state, 'value') else str(state.lock_state),
                            datetime.now(timezone.utc).isoformat(),
                        )
                    )
                    conn.commit()
                    conn.close()
                except Exception as db_err:
                    _logger.debug("[DayType] DB persist skipped: %s", db_err)

                # P5.1.5: Publish on classification CHANGE only
                dt_val = state.day_type.value if hasattr(state.day_type, 'value') else str(state.day_type)
                if dt_val != _prev_day_type["value"]:
                    _logger.info("[DayType] Classification changed: %s -> %s (conf=%.2f)",
                                 _prev_day_type["value"], dt_val, state.confidence)
                    _prev_day_type["value"] = dt_val
                    try:
                        await bar_router.publish("day_type_classification", {
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "day_type": dt_val,
                            "status": state.lock_state.value if hasattr(state.lock_state, 'value') else str(state.lock_state),
                            "confidence": state.confidence,
                            "stage": state.stage.value if hasattr(state.stage, 'value') else str(state.stage),
                            "ib_high": ib_h,
                            "ib_low": ib_l,
                            "ib_class": state.ib_width.value if hasattr(state.ib_width, 'value') else None,
                            "opening_type": opening_type,
                            "previous_day_type": _prev_day_type["value"],
                        })
                    except Exception:
                        pass
            except Exception as e:
                _logger.debug("[DayType] process_bar error: %s", e)

        bar_router.subscribe("5min", _day_type_on_bar)
        _logger.info("[Main] DayTypeStateMachine subscribed to 5min via BarRouter")
    except Exception as e:
        _logger.error("[Main] DayTypeStateMachine startup failed: %s", e)

    # 9.2: Instantiate KillzoneSystem (time-based, no bar subscriptions)
    try:
        import asyncio as _aio
        from backend.v9.systems.killzone.killzone_system import KillzoneSystem
        killzone_system = KillzoneSystem()
        app.state.killzone_system = killzone_system
        killzone_system.hydrate()
        _logger.info("[Main] KillzoneSystem hydrated: %s", killzone_system.current_state.get("current_zone", {}).get("name"))

        async def _killzone_loop():
            while True:
                await killzone_system.tick()
                await _aio.sleep(30)
        _aio.ensure_future(_killzone_loop())
        _logger.info("[Main] KillzoneSystem tick loop started (30s)")
    except Exception as e:
        _logger.error("[Main] KillzoneSystem startup failed: %s", e)

    _logger.info("[Main] BarRouter created: %s", bar_router.get_stats())

    # Historical Replay: warm system buffers from DB (D2.2)
    from backend.v9.services.historical_replay import HistoricalReplay
    db_path = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    historical = HistoricalReplay(db_path=db_path, bar_router=bar_router)
    app.state.historical_replay = historical
    try:
        _logger.info("[Main] HistoricalReplay: starting 12h warmup...")
        await historical.warm_all_systems(hours=12)
        _logger.info("[Main] HistoricalReplay stats: %s", historical.get_stats())
    except Exception as e:
        _logger.error("[Main] HistoricalReplay failed (non-fatal): %s", e)


# ── Health (unified) ─────────────────────────────────────────

_START_TS = time.time()


@app.get("/health")
def health():
    """Top-level health check — used by Render zero-downtime deploys."""
    uptime = time.time() - _START_TS
    return {
        "status": "ok",
        "service": "mems26-unified",
        "version": "9.0.0",
        "uptime_s": round(uptime, 1),
        "v9_mounted": True,
    }
