"""MEMS26 unified backend — serves V8-compatible routes + V9 API.

Entry point for Render:
    web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""

import asyncio
import os
import time
import sqlite3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.v9.app import v9_router, init_event_dispatcher
from backend.v9.api.journal_compat_routes import router as journal_compat_router
from backend.v9.systems.day_type.prev_day import (
    load_previous_day_context as _load_previous_day_context,
    missing_pd_context as _missing_pd_context,
)

DEFAULT_LOCAL_DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

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
app.include_router(journal_compat_router)


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
    import asyncio as _asyncio
    from backend.v9.services.bar_router import BarRouter
    bar_router = BarRouter()
    bar_router.bind_main_loop(_asyncio.get_running_loop())
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

    # P-15TR.4: ReversalBarHandler subscribes to tick_reversal_15
    try:
        from backend.v9.systems.reversal import ReversalBarHandler
        reversal_handler = ReversalBarHandler()
        app.state.reversal_handler = reversal_handler
        reversal_handler.subscribe(bar_router)
        _logger.info("[Main] ReversalBarHandler subscribed to tick_reversal_15")
    except Exception as e:
        _logger.error("[Main] ReversalBarHandler startup failed: %s", e)

    # P5.1.2: Subscribe DayTypeStateMachine to BarRouter 5min
    try:
        from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
        from backend.v9.systems.day_type.schemas import BarInput, IBClassification, Stage
        from backend.v9.systems.day_type.detector import classify_ib_width
        from backend.v9.systems.day_type.consumer import DayTypeConsumer
        from backend.v9.db.session import SessionLocal
        from backend.v9.services.market_clock import minutes_since_rth_open, now_et
        from backend.v9.api.v9.day_type_seed import maybe_seed_ib_from_tpo

        day_type_machine = DayTypeStateMachine()
        app.state.day_type_machine = day_type_machine
        _day_type_consumer = DayTypeConsumer(SessionLocal)
        _prev_day_type = {"value": "UNKNOWN"}  # mutable for closure

        def _load_previous_day_context_for_startup():
            try:
                return _load_previous_day_context()
            except Exception as pd_err:
                _logger.warning("[DayType] previous day context unavailable: %s", pd_err)
                return _missing_pd_context(("pd_high", "pd_low", "pd_close"))

        async def _day_type_on_bar(event):
            """Bridge BarRouter event to DayTypeStateMachine.process_bar."""
            bar = event.payload if hasattr(event, 'payload') else event
            try:
                # Read IB from v9_bars_5min (P31 IB source fix: bars are
                # more current than TPOSystem which can lag behind Sierra).
                # IB = first 60 min of RTH (09:30-10:30 ET).
                tpo_sys = getattr(app.state, 'tpo_system', None)
                ib_h, ib_l = None, None
                try:
                    from datetime import datetime, time as _time, timedelta
                    from zoneinfo import ZoneInfo
                    _et = ZoneInfo("America/New_York")
                    today_et = datetime.now(_et).date()
                    rth_open = datetime.combine(today_et, _time(9, 30), tzinfo=_et)
                    ib_end = rth_open + timedelta(hours=1)
                    rth_open_str = rth_open.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
                    ib_end_str = ib_end.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
                    import sqlite3 as _sql3
                    _conn = _sql3.connect(DEFAULT_LOCAL_DB_PATH)
                    _row = _conn.execute(
                        "SELECT MAX(high), MIN(low) FROM v9_bars_5min "
                        "WHERE symbol='MES' AND ts >= ? AND ts < ?",
                        (rth_open_str, ib_end_str),
                    ).fetchone()
                    _conn.close()
                    if _row and _row[0] is not None:
                        ib_h, ib_l = float(_row[0]), float(_row[1])
                except Exception as _ib_err:
                    _logger.warning("[DayType] IB from bars failed: %s — falling back to TPO", _ib_err)
                    ib_h = tpo_sys.ib_high if tpo_sys else None
                    ib_l = tpo_sys.ib_low if tpo_sys else None

                # Read opening type from TPO (P5.1.4)
                opening_type = "UNKNOWN"
                if tpo_sys:
                    tpo_state = tpo_sys.get_current()
                    opening_type = tpo_state.get("opening_type", "NA")

                # Compute session_min from the central market clock (replay-aware).
                et_now = now_et()
                _session_min = minutes_since_rth_open(et_now)
                pd_ctx = _load_previous_day_context_for_startup()

                bar_input = BarInput(
                    ts=et_now.timestamp(),
                    session_min=_session_min,
                    open=float(bar.get("open", bar.get("o", 0))),
                    high=float(bar.get("high", bar.get("h", 0))),
                    low=float(bar.get("low", bar.get("l", 0))),
                    close=float(bar.get("close", bar.get("c", 0))),
                    volume=float(bar.get("volume", bar.get("v", 0))),
                    pd_high=pd_ctx.get("pd_high"),
                    pd_low=pd_ctx.get("pd_low"),
                    pd_close=pd_ctx.get("pd_close"),
                    ib_high=ib_h,
                    ib_low=ib_l,
                )
                # Mid-session restart guard (P30 C1): when the FastAPI process
                # restarts after RTH 10:30, the fresh machine would otherwise
                # land at stage A3, see session_min >= ib_period_min and lock
                # IB from a single 5-min bar (~5 pt → NARROW), which steered
                # 2026-05-19 to a wrong Nontrend verdict. Seed IB from TPO's
                # already-locked values and skip to B1 in that scenario.
                tpo_ib_locked = bool(getattr(tpo_sys, "ib_locked", False)) if tpo_sys else False
                maybe_seed_ib_from_tpo(
                    machine=day_type_machine,
                    session_min=_session_min,
                    tpo_ib_locked=tpo_ib_locked,
                    tpo_ib_high=ib_h,
                    tpo_ib_low=ib_l,
                    logger=_logger,
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
                            str(state.lock_state),
                            datetime.now(timezone.utc).isoformat(),
                        )
                    )
                    conn.commit()
                    conn.close()
                except Exception as db_err:
                    _logger.debug("[DayType] DB persist skipped: %s", db_err)

                # V9: Persist to v9_day_type_history via DayTypeConsumer (3a-S4)
                try:
                    classification = day_type_machine.to_classification()
                    if classification is not None:
                        _day_type_consumer.consume({
                            "timestamp": classification.timestamp.isoformat(),
                            "day_type": classification.day_type.value,
                            "probability": classification.probability,
                            "directional_certainty": classification.directional_certainty,
                            "trading_confidence": classification.trading_confidence,
                            "ib_h": classification.ib_h,
                            "ib_l": classification.ib_l,
                            "ib_width": classification.ib_width,
                            "ib_width_class": classification.ib_width_class,
                            "opening_type": classification.opening_type,
                            "last_updated_at": classification.last_updated_at.isoformat(),
                            "reasoning_notes": classification.reasoning_notes,
                            "active_zohar_rules": classification.active_zohar_rules,
                            # P31 §C: pass the state machine's lock_state so the
                            # V1-legacy `status` column reflects PENDING vs LOCKED
                            # instead of being hardcoded to LOCKED.
                            "lock_state": str(state.lock_state),
                        })
                except Exception as consumer_err:
                    # P31 §C: was logger.debug — silent failures hid a schema-drift
                    # IntegrityError (status/confidence NOT NULL) for weeks.
                    _logger.warning(
                        "[DayType] V9 consumer persist failed: %s", consumer_err
                    )

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
                            "status": str(state.lock_state),
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

    # P-TG.5: TradingGateway initialization
    try:
        from backend.v9.gateway import TradingGateway
        trading_gateway = TradingGateway()
        # Wire system registry for cross-context snapshots
        system_registry = {}
        for attr_name in ("day_type_machine", "five_min_system", "footprint_system",
                          "woodies_system", "tpo_system", "killzone_system"):
            sys_ref = getattr(app.state, attr_name, None)
            if sys_ref:
                system_registry[attr_name] = sys_ref
        trading_gateway.set_system_registry(system_registry)
        app.state.trading_gateway = trading_gateway
        _logger.info("[Main] TradingGateway initialized: %s", trading_gateway.get_status())

        # Prompt 14/22-alt: inject gateway into firing systems for validated auto-routing
        if hasattr(app.state, 'five_min_system') and app.state.five_min_system:
            app.state.five_min_system.set_gateway(trading_gateway)
            _logger.info("[Main] S2 FiveMinSystem → gateway injected")
        if hasattr(app.state, 'footprint_system') and app.state.footprint_system:
            app.state.footprint_system.set_gateway(trading_gateway)
            _logger.info("[Main] S3 FootprintSystem → gateway injected")
        if hasattr(app.state, 'woodies_system') and app.state.woodies_system:
            app.state.woodies_system.set_gateway(trading_gateway)
            _logger.info("[Main] S4 WoodiesSystem → gateway injected")

        # P31-02b: inject FootprintSystem into FiveMinSystem so process_bar
        # reads cot/amt/belly in-process (~1ms) instead of HTTP self-calls (~8s).
        if hasattr(app.state, 'five_min_system') and app.state.five_min_system \
           and hasattr(app.state, 'footprint_system') and app.state.footprint_system:
            app.state.five_min_system.set_footprint_system(app.state.footprint_system)
            _logger.info("[Main] S2 FiveMinSystem ← footprint_system injected (P31-02b)")
    except Exception as e:
        _logger.error("[Main] TradingGateway startup failed: %s", e)

    # PG1-1: BarLevelDetector — glue between BarRouter and W11 TradeManager
    try:
        from backend.v9.db.session import SessionLocal
        from backend.v9.services.trade_manager import TradeManager
        from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector

        tm_db = SessionLocal()
        trade_manager = TradeManager(db=tm_db)
        bar_level_detector = BarLevelDetector(trade_manager=trade_manager)
        bar_level_detector.subscribe(bar_router)
        app.state.trade_manager = trade_manager
        app.state.bar_level_detector = bar_level_detector
        _logger.info("[Main] BarLevelDetector subscribed to 5min — SHADOW trades will auto-close")
        gw = getattr(app.state, "trading_gateway", None)
        if gw is not None and hasattr(gw, "set_trade_manager"):
            gw.set_trade_manager(trade_manager)
            _logger.info("[Main] TradingGateway → TradeManager wired for SHADOW PnL")

        # P-WS.1: inject main loop into TradeEventEmitter for WS broadcast
        try:
            from backend.v9.services.trade_manager.events import set_trade_events_loop
            set_trade_events_loop(asyncio.get_event_loop())
            _logger.info("[Main] TradeEventEmitter ← main loop injected (WS push active)")
        except Exception as _e:
            _logger.warning("[Main] TradeEventEmitter loop injection failed: %s", _e)

        # P-CHOP.1: start background chop_score cache refresher (30s interval)
        # Prevents 3s event-loop block on cold-cache Woodies fires.
        try:
            from backend.v9.systems.layer0.chop_score import start_background_refresher
            start_background_refresher(interval_s=30.0)
            _logger.info("[Main] chop_score background refresher started (30s)")
        except Exception as _e:
            _logger.warning("[Main] chop_score refresher start failed: %s", _e)
    except Exception as e:
        _logger.error("[Main] BarLevelDetector startup failed: %s", e)

    # Historical Replay: warm system buffers from DB (D2.2)
    from backend.v9.services.historical_replay import HistoricalReplay
    db_path = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    historical = HistoricalReplay(db_path=db_path, bar_router=bar_router)
    app.state.historical_replay = historical
    # P30 2026-05-20: warm_all_systems replays ~144 5-min bars through
    # BarRouter. Even as `asyncio.create_task` the published events run their
    # sync handlers (e.g. `BarLevelDetector.on_bar` at 5–11 s each because
    # of a `InvalidRequestError: session is in committed state` regression)
    # on the same event loop — the FastAPI startup phase never completes
    # and the server never binds port 8000. Skip by default so the cockpit
    # comes up instantly. Re-enable per-deploy by exporting V9_DO_WARMUP=1.
    if os.getenv("V9_DO_WARMUP", "").lower() in ("1", "true", "yes"):
        async def _run_warmup():
            try:
                _logger.info("[Main] HistoricalReplay: starting 12h warmup (background)...")
                await historical.warm_all_systems(hours=12)
                _logger.info("[Main] HistoricalReplay stats: %s", historical.get_stats())
            except Exception as e:
                _logger.error("[Main] HistoricalReplay failed (non-fatal): %s", e)
        asyncio.create_task(_run_warmup())
    else:
        _logger.info("[Main] HistoricalReplay: skipped at startup (V9_DO_WARMUP not set)")

    # P31 Issue B — TPO history snapshotter (writes v9_tpo_history every 30-min
    # RTH boundary so the chart's pink line can step like Sierra Study ID:3).
    # See backend/v9/services/tpo_history_snapshotter.py and
    # docs/handoff/CC_INVESTIGATE_TPO_STEPPED_PERIODS.md (CC #2 path B1).
    if os.getenv("V9_DISABLE_TPO_SNAPSHOTTER", "").lower() not in ("1", "true", "yes"):
        try:
            from backend.v9.services.tpo_history_snapshotter import get_snapshotter
            snapshotter = get_snapshotter()
            snapshotter.start()
            app.state.tpo_history_snapshotter = snapshotter
            _logger.info("[Main] TPOHistorySnapshotter started")
        except Exception as e:
            _logger.error("[Main] TPOHistorySnapshotter startup failed (non-fatal): %s", e)
    else:
        _logger.info("[Main] TPOHistorySnapshotter: disabled via V9_DISABLE_TPO_SNAPSHOTTER")

    # P31 Phase 1 — EOD archive scheduler (auto-fires at 15:55 ET on trading
    # days; runs 90-day retention prune after each archive). Selected per
    # docs/handoff/CC_UNIFIED_HISTORY_ARCHITECTURE_SPEC.md path (ii).
    if os.getenv("V9_DISABLE_EOD_SCHEDULER", "").lower() not in ("1", "true", "yes"):
        try:
            from backend.v9.services.eod_archive_scheduler import get_scheduler as _get_eod_sched
            eod_scheduler = _get_eod_sched()
            eod_scheduler.start()
            app.state.eod_archive_scheduler = eod_scheduler
            _logger.info("[Main] EODArchiveScheduler started")
        except Exception as e:
            _logger.error("[Main] EODArchiveScheduler startup failed (non-fatal): %s", e)
    else:
        _logger.info("[Main] EODArchiveScheduler: disabled via V9_DISABLE_EOD_SCHEDULER")

    # P31 Phase 2 — Startup gap-fill (Michael 2026-05-22 "I want to see all
    # the data already in the dashboard when we turn on"). Reads rolling
    # Sierra exports for 5min/CVD/VP and INSERT-OR-IGNOREs anything newer
    # than MAX(ts). Idempotent — safe to re-run. Bounded by export size.
    if os.getenv("V9_DISABLE_HISTORY_LOADER", "").lower() not in ("1", "true", "yes"):
        try:
            from backend.v9.services.history_loader import get_loader as _get_history_loader
            loader = _get_history_loader()
            summary = loader.run_gap_fill(reason="startup")
            app.state.history_loader = loader
            app.state.history_last_gap_fill = summary
            _logger.warning(  # WARNING so it survives uvicorn filter
                "[Main] history_loader startup gap-fill elapsed=%.2fs streams=%d",
                summary.get("elapsed_s", 0.0),
                len(summary.get("streams", {})),
            )
        except Exception as e:
            _logger.error("[Main] history_loader startup failed (non-fatal): %s", e)
    else:
        _logger.info("[Main] history_loader: disabled via V9_DISABLE_HISTORY_LOADER")


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
