"""MEMS26 unified backend — serves V8-compatible routes + V9 API.

Entry point for Render:
    web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""

import asyncio
import os
import time
from datetime import timedelta


# (_SkipPersist removed 2026-08-08 K2 — the day-type persist block moved to
# backend/v9/systems/day_type/state_persist.py, which returns a status instead.)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env BEFORE any backend.v9 import — feature flags (e.g. S2_ATR_RELATIVE,
# S3_RELATIVE, S1_* calibration flags) are read at import time in
# backend/v9/shared/atr.py. Without this, a launch path that didn't `source .env`
# (LaunchAgent auto-restart, bare uvicorn) dropped every SHADOW flag to OFF —
# the 2026-06-06 "flags didn't fire in SHADOW" incident. Explicit env still wins.
from backend.env_loader import load_dotenv_file as _load_dotenv_file
_load_dotenv_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, ".env"))

# Configure the ROOT logger BEFORE the first `backend.v9` import — T-61 (Michael
# 2026-08-20, fix F3). uvicorn's LOGGING_CONFIG never gives root a handler, and the
# app's only basicConfig sits behind a LAZY import in status.py, so until somebody
# opened the dashboard every record fell through to `logging.lastResort` — WARNING+
# only, printed bare. On 2026-08-19 that made 22 shadow trades leave zero log lines.
# Placed after env_loader so MEMS26_LOG_LEVEL is readable from .env, and before
# backend.v9 so import-time records are captured too. Full diagnosis in the module.
from backend.logging_setup import configure_logging as _configure_logging
_configure_logging()

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


@app.on_event("shutdown")
async def _shutdown():
    """Graceful shutdown: WAL checkpoint to prevent corruption on restart."""
    import logging
    _logger = logging.getLogger("mems26")
    _logger.info("[Shutdown] WAL checkpoint starting")
    from backend.v9.db.safe_writer import safe_checkpoint
    safe_checkpoint()
    _logger.info("[Shutdown] WAL checkpoint complete — clean exit")


@app.on_event("startup")
async def _startup():
    """Initialize EventDispatcher + BarIngestionService at unified app startup."""
    import logging
    _logger = logging.getLogger("mems26")

    # T-61 boot probe. Re-assert the root config (cheap no-op; survives anything that
    # re-ran dictConfig between import time and startup) and emit the ONE line that
    # proves the INFO layer is alive in THIS pid. `scripts/fire_drill.py` goes NO-GO
    # when this line is missing for the running pid — so 2026-08-19-style blindness
    # (WARNING-only, no timestamps, `[ExitVerify]`/`SHADOW trade TM` invisible) can
    # never again go unnoticed for a whole session.
    try:
        from backend.logging_setup import boot_probe as _boot_probe, configure_logging as _cfg_log
        _cfg_log()
        _boot_probe()
    except Exception as _lg_err:  # logging must never block boot
        _logger.warning("[Main] boot probe failed (non-fatal): %s", _lg_err)

    # Schema self-heal on boot (idempotent, checkfirst=True): a new ORM model added
    # by `git pull` gets its table created on restart, not only at install time.
    # Root fix for v9_bars_5min_continuous — 01fa023 registered the model, but NOTHING
    # ran create_all on the real boot path (only db_init.sh at install did), so the
    # table was never built → /5min_continuous push raised "relation does not exist"
    # every bar → /tmp/backend.err.log ballooned to 6GB. Wrapped so a create_all
    # hiccup can never block boot.
    try:
        from backend.v9.db.session import init_db
        init_db()
        _logger.info("[Main] init_db() ok — schema ensured on boot")
    except Exception as _e:
        _logger.warning("[Main] init_db() on boot failed (non-fatal): %s", _e)

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
        bar_router.subscribe("day_type_classification", five_min_system.on_day_type_event)
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
        from backend.v9.systems.day_type.prev_day import load_tpo_previous_day_summary

        try:
            _prev_day_tpo = load_tpo_previous_day_summary()
            _prev_day_summary_for_machine = {
                "vah": _prev_day_tpo.get("vah"),
                "val": _prev_day_tpo.get("val"),
                # session_date = TODAY's trading session date (ET); it's the rate-limit
                # key inside classify_neutral_subtype, NOT the previous-day date.
                # Matches Stream 1 fix-up (api.py, commit a58ee61).
                "session_date": now_et().date().isoformat(),
            }
        except Exception as _pds_err:
            _logger.warning(
                "[DayType] prev_day_summary load failed: %s · NeuE/NeuC will fall back to NeuC",
                _pds_err,
            )
            _prev_day_summary_for_machine = None

        day_type_machine = DayTypeStateMachine(prev_day_summary=_prev_day_summary_for_machine)
        app.state.day_type_machine = day_type_machine
        _day_type_consumer = DayTypeConsumer(SessionLocal)
        _prev_day_type = {"value": "UNKNOWN"}  # mutable for closure
        _prev_bar_ts = {"value": None}  # dedup guard: skip re-processing same bar (4B fix)

        # D-S1DYN: Shadow reclassifier (IB-relative dynamic chain)
        import os as _flag_os
        S1_DYNAMIC_RECLASS = _flag_os.environ.get("S1_DYNAMIC_RECLASS", "").lower() in ("1", "true", "yes")
        _shadow_reclass = {"instance": None}  # mutable for closure; created after IB lock
        # #68 part-b: accumulate RTH bars in-memory for the new classifier
        _cls_rth_bars: list = []  # mutable list for closure; reset on new session date
        _cls_session_date = {"value": None}
        _cls_ctx_cache = {"loaded": False}  # one-time context loaded at IB lock

        def _load_previous_day_context_for_startup():
            try:
                return _load_previous_day_context()
            except Exception as pd_err:
                _logger.warning("[DayType] previous day context unavailable: %s", pd_err)
                return _missing_pd_context(("pd_high", "pd_low", "pd_close"))

        async def _day_type_on_bar(event):
            """Bridge BarRouter event to DayTypeStateMachine.process_bar."""
            # K2 note: this import used to live inside the (now-extracted)
            # persist block; the publish at the bottom still needs it.
            from datetime import datetime, timezone
            bar = event.payload if hasattr(event, 'payload') else event
            # 4B dedup: bridge republishes the same bar ~41× per 5min interval
            # (every file-poll mtime change). Skip if bar ts unchanged.
            bar_ts = bar.get("ts")
            if bar_ts is not None and bar_ts == _prev_bar_ts["value"]:
                return
            _prev_bar_ts["value"] = bar_ts
            try:
                # IB source of truth: Sierra Study ID:6 via tpo.json.
                # Pre-LIVE cleanup (2026-05-28): removed inline v9_bars_5min
                # synthesis ("P31 IB source fix") — that was a CLAUDE.md
                # violation and produced IB values that disagreed with
                # Sierra Chart on screen. NULL pre-RTH is correct behaviour;
                # the state machine ignores NULL IB and stays in stage A3.
                tpo_sys = getattr(app.state, 'tpo_system', None)
                ib_h, ib_l = None, None
                try:
                    from backend.v9.api.v9.tpo_routes import _load_sierra_tpo
                    _sierra_tpo = _load_sierra_tpo() or {}
                    if _sierra_tpo.get("ib_found"):
                        ib_h = _sierra_tpo.get("ib_high")
                        ib_l = _sierra_tpo.get("ib_low")
                except Exception as _ib_err:
                    _logger.warning("[DayType] Sierra IB load failed: %s", _ib_err)

                # Opening type from the state machine (computed in _stage_a2
                # from the first 3 RTH bars). FIX 1: was reading from TPO
                # which always returns "NA" (hardcoded in tpo_routes.py:383).
                opening_type = "UNKNOWN"
                if day_type_machine and day_type_machine.opening:
                    _ot = day_type_machine.opening.opening_type
                    opening_type = _ot.value if hasattr(_ot, 'value') else str(_ot)
                elif tpo_sys:
                    tpo_state = tpo_sys.get_current()
                    opening_type = tpo_state.get("opening_type", "UNKNOWN")

                # Compute session_min from the central market clock (replay-aware).
                et_now = now_et()
                _session_min = minutes_since_rth_open(et_now)
                # is_rth: True only for bars that fall inside 09:30–16:00 ET.
                # minutes_since_rth_open clamps to 0 pre-RTH so session_min
                # alone cannot distinguish an overnight bar from the 09:30 bar.
                from datetime import time as _time_cls
                _et_t = et_now.time()
                _is_rth_bar = _time_cls(9, 30) <= _et_t < _time_cls(16, 0)
                pd_ctx = _load_previous_day_context_for_startup()

                bar_input = BarInput(
                    ts=et_now.timestamp(),
                    session_min=_session_min,
                    is_rth=_is_rth_bar,
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

                # #68 part-b: accumulate RTH bars for the new classifier (in-memory, no DB)
                if _is_rth_bar:
                    _today = now_et().date().isoformat()
                    if _cls_session_date["value"] != _today:
                        _cls_rth_bars.clear()
                        _cls_session_date["value"] = _today
                        # Reset context cache for new day (force re-load at next IB lock)
                        _cls_ctx_cache.clear()
                        _cls_ctx_cache["loaded"] = False
                    _cls_rth_bars.append({
                        "o": bar_input.open, "h": bar_input.high,
                        "l": bar_input.low, "c": bar_input.close,
                        "v": bar_input.volume,
                    })
                    # Expose to gateway for opening-type gate (FIX B)
                    # The gateway reads via system_registry["day_type_machine"]._opening_gate_bars
                    day_type_machine._opening_gate_bars = _cls_rth_bars

                # #11 fix: rehydrate _cls_rth_bars from DB on mid-session restart.
                # When IB is locked but the in-memory buffer is short (restart wiped it),
                # seed from v9_bars_5min_woodies so the classifier can promote immediately
                # instead of starving for ~1h. Mirrors maybe_seed_ib_from_tpo pattern.
                # Fail-safe: disable with REHYDRATE_CLS_BARS=0 + restart.
                import os as _os
                _REHYDRATE = _os.environ.get("REHYDRATE_CLS_BARS", "1").lower() not in ("0", "false", "no")
                if (_REHYDRATE and _is_rth_bar and day_type_machine.ib_locked
                        and len(_cls_rth_bars) < 12
                        and not _cls_ctx_cache.get("_rehydrated")):
                    try:
                        from backend.v9.db.read import read_all as _ra_rehy
                        _today_rehy = now_et().date().isoformat()
                        _rehy_rows = _ra_rehy(
                            "SELECT open, high, low, close, volume FROM v9_bars_5min_woodies "
                            "WHERE (ts AT TIME ZONE 'America/New_York')::date = :d "
                            "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
                            "AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' "
                            "AND symbol = 'MES' ORDER BY ts", {"d": _today_rehy})
                        if _rehy_rows and len(_rehy_rows) > len(_cls_rth_bars):
                            _cls_rth_bars.clear()
                            for _rb in _rehy_rows:
                                _cls_rth_bars.append({
                                    "o": float(_rb["open"]), "h": float(_rb["high"]),
                                    "l": float(_rb["low"]), "c": float(_rb["close"]),
                                    "v": int(_rb.get("volume") or 0),
                                })
                            day_type_machine._opening_gate_bars = _cls_rth_bars
                            _logger.info("[S1-REHYDRATE] seeded _cls_rth_bars from DB: %d bars (IB locked, buffer was short)",
                                         len(_cls_rth_bars))
                    except Exception as _rehy_err:
                        _logger.warning("[S1-REHYDRATE] rehydration failed (continuing with short buffer): %s", _rehy_err)
                    _cls_ctx_cache["_rehydrated"] = True  # one-shot, don't retry every bar

                # #68 part-b: promote day_type from validated 7-type classifier.
                # Flag S1_ENGINE_NEW_CLASSIFIER (default OFF). REPLACES S1_LIVE_RECLASS
                # + ShadowReclassifier when ON. In-memory only — NO per-bar DB reads.
                _S1_NEW_CLS = _os.environ.get("S1_ENGINE_NEW_CLASSIFIER", "").lower() in ("1", "true", "yes")
                if _S1_NEW_CLS and day_type_machine.ib_locked:
                    try:
                        from backend.v9.systems.day_type.classifier_core import classify_session
                        from backend.v9.systems.day_type.state_machine import DayType as _DT

                        # Load classifier context ONCE at IB lock (not per-bar)
                        if not _cls_ctx_cache["loaded"]:
                            try:
                                from backend.v9.db.read import read_all, read_one, read_scalar
                                _cls_today = now_et().date().isoformat()
                                # Sierra TPO row → profile_shape, VAH, VAL
                                _sib = read_one(
                                    "SELECT profile_shape, vah_price, val_price, poc_price "
                                    "FROM v9_tpo_sessions WHERE trading_date = :d AND session_type = 'CASH' "
                                    "ORDER BY id DESC LIMIT 1", {"d": _cls_today})
                                _cls_ctx_cache["profile_shape"] = (_sib or {}).get("profile_shape")
                                _cls_ctx_cache["tpo_vah"] = float((_sib or {}).get("vah_price") or 0) or None
                                _cls_ctx_cache["tpo_val"] = float((_sib or {}).get("val_price") or 0) or None
                                _cls_ctx_cache["poc_at_ib"] = float((_sib or {}).get("poc_price") or 0) or None
                                # IB width history
                                _hist = read_all(
                                    "SELECT ib_width FROM v9_day_type_history WHERE date < :d "
                                    "AND ib_width IS NOT NULL", {"d": _cls_today})
                                _cls_ctx_cache["ib_width_hist"] = [
                                    float(r["ib_width"]) for r in _hist if r.get("ib_width") is not None]
                                # Prior day levels
                                _pd = read_scalar(
                                    "SELECT max((ts AT TIME ZONE 'America/New_York')::date) "
                                    "FROM v9_bars_5min_woodies "
                                    "WHERE (ts AT TIME ZONE 'America/New_York')::date < :d AND symbol='MES'",
                                    {"d": _cls_today})
                                _pdh = _pdl = _pvah = _pval = None
                                if _pd is not None:
                                    _pd_iso = _pd.isoformat() if hasattr(_pd, "isoformat") else str(_pd)
                                    _hl = read_one(
                                        "SELECT max(high) AS h, min(low) AS l FROM v9_bars_5min_woodies "
                                        "WHERE (ts AT TIME ZONE 'America/New_York')::date = :pd AND symbol='MES'",
                                        {"pd": _pd_iso})
                                    _pdh = float((_hl or {}).get("h") or 0) or None
                                    _pdl = float((_hl or {}).get("l") or 0) or None
                                    _pv = read_one(
                                        "SELECT vah_price AS vah, val_price AS val FROM v9_tpo_sessions "
                                        "WHERE trading_date = :pd ORDER BY id DESC LIMIT 1", {"pd": _pd_iso})
                                    if _pv:
                                        _pvah = float((_pv or {}).get("vah") or 0) or None
                                        _pval = float((_pv or {}).get("val") or 0) or None
                                _cls_ctx_cache["pdh"] = _pdh
                                _cls_ctx_cache["pdl"] = _pdl
                                _cls_ctx_cache["prior_vah"] = _pvah
                                _cls_ctx_cache["prior_val"] = _pval
                                # Session volume ratio (median from prior complete RTH days)
                                _vol_rows = read_all(
                                    "SELECT sum(volume) AS vol FROM v9_bars_5min_woodies WHERE symbol='MES' "
                                    "AND (ts AT TIME ZONE 'America/New_York')::date < :d "
                                    "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
                                    "AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' "
                                    "GROUP BY (ts AT TIME ZONE 'America/New_York')::date "
                                    "HAVING count(*) >= 60", {"d": _cls_today})
                                _vols = sorted(float(r["vol"]) for r in _vol_rows if r.get("vol"))
                                _cls_ctx_cache["med_vol"] = _vols[len(_vols) // 2] if len(_vols) >= 3 else None
                                # IB median for dd narrow-IB check
                                _ibm_rows = read_all(
                                    "SELECT (ib_high - ib_low) AS w FROM v9_tpo_sessions "
                                    "WHERE session_type='CASH' AND trading_date < :d "
                                    "AND ib_high IS NOT NULL AND ib_low IS NOT NULL "
                                    "ORDER BY trading_date DESC LIMIT 20", {"d": _cls_today})
                                _ibmeds = sorted(float(r["w"]) for r in _ibm_rows if r.get("w") is not None)
                                _cls_ctx_cache["ib_median"] = _ibmeds[len(_ibmeds) // 2] if _ibmeds else None
                                _cls_ctx_cache["loaded"] = True
                                _logger.info("[S1-NEW-CLS] context loaded at IB lock: shape=%s pdh=%s pdl=%s hist=%d",
                                             _cls_ctx_cache.get("profile_shape"),
                                             _cls_ctx_cache.get("pdh"), _cls_ctx_cache.get("pdl"),
                                             len(_cls_ctx_cache.get("ib_width_hist", [])))
                            except Exception as _ctx_err:
                                _logger.warning("[S1-NEW-CLS] context load failed (continuing without): %s", _ctx_err)
                                _cls_ctx_cache["loaded"] = True  # don't retry every bar

                        if len(_cls_rth_bars) >= 12:  # only after IB lock (60min / 12 bars)
                            # Compute session volume ratio
                            _ses_vol = sum(b.get("v", 0) for b in _cls_rth_bars)
                            _med = _cls_ctx_cache.get("med_vol")
                            _vr = round(_ses_vol / _med, 3) if _med and _med > 0 else None
                            # POC now from TPO system
                            _tpo_now = getattr(app.state, 'tpo_system', None)
                            _poc_now = None
                            if _tpo_now and hasattr(_tpo_now, 'current_state'):
                                _poc_now = _tpo_now.current_state.get("poc")

                            _cls_result = classify_session(
                                bars=_cls_rth_bars,
                                ib_high=day_type_machine.ib_high,
                                ib_low=day_type_machine.ib_low,
                                open_price=_cls_rth_bars[0]["o"],
                                ib_width_hist=_cls_ctx_cache.get("ib_width_hist"),
                                profile_shape=_cls_ctx_cache.get("profile_shape"),
                                vol_ratio=_vr,
                                prior_vah=_cls_ctx_cache.get("prior_vah"),
                                prior_val=_cls_ctx_cache.get("prior_val"),
                                pdh=_cls_ctx_cache.get("pdh"),
                                pdl=_cls_ctx_cache.get("pdl"),
                                poc_now=_poc_now,
                                poc_at_ib=_cls_ctx_cache.get("poc_at_ib"),
                            )
                            _cls_dt_str = _cls_result.get("day_type", "")
                            _cls_status = _cls_result.get("status", "")

                            # Map 7-type string → DayType enum (Normal_Variation→Variation; rest direct)
                            _DT_MAP = {
                                "Trend_Normal": _DT.Trend_Normal,
                                "Trend_DD": _DT.Trend_DD,
                                "Variation": _DT.Variation,
                                "Normal_Variation": _DT.Variation,
                                "Normal": _DT.Normal,
                                "Neutral_Center": _DT.Neutral_Center if hasattr(_DT, 'Neutral_Center') else _DT.Normal,
                                "Neutral_Extreme": _DT.Neutral_Extreme if hasattr(_DT, 'Neutral_Extreme') else _DT.Normal,
                                "Nontrend": _DT.Nontrend,
                            }
                            _new_dt = _DT_MAP.get(_cls_dt_str)
                            # P1-8 Nonconviction stand-aside — NONCONVICTION_ACTIVE_V1 (default OFF).
                            # schemas.DayType has NO "Nonconviction" member, so it CANNOT be promoted as
                            # an enum (_DT.Nonconviction -> AttributeError). When the flag is ON and the
                            # classifier names a Nonconviction day, publish a dedicated NO_TRADE signal --
                            # the raw string "Nonconviction" -- on ONLY the live-promoted top-level machine
                            # attribute. Its sole readers (trade_context.get_live_day_type + the build-status
                            # day_type_inspector) use the ".value if hasattr else str" idiom, so no enum is
                            # forced and nothing crashes. state.day_type / _last_state.day_type are LEFT as
                            # the last valid enum -- they feed the UNGUARDED .value readers (get_current(),
                            # on_trigger(), DB-seed). get_live_day_type() then surfaces "Nonconviction" to
                            # day_type_at_entry, which daytype_playbook (its _VALID_DT also gated by this
                            # flag) SKIPs -> stand aside. Flag OFF -> this branch is skipped and "Nonconviction"
                            # stays absent from _DT_MAP -> .get() is None -> inert, byte-identical to today.
                            _nonconv_on = _os.environ.get("NONCONVICTION_ACTIVE_V1", "0").lower() in ("1", "true", "yes")
                            if _cls_dt_str == "Nonconviction" and _nonconv_on:
                                _prev_dt = getattr(day_type_machine, "day_type", None)
                                _prev_str = _prev_dt.value if hasattr(_prev_dt, "value") else str(_prev_dt)
                                if _prev_str != "Nonconviction":
                                    day_type_machine.day_type = "Nonconviction"  # NO_TRADE sentinel (str-safe readers only)
                                    _logger.info("[S1-NEW-CLS] NO_TRADE stand-aside: %s -> Nonconviction (%s)",
                                                 _prev_str, _cls_status)
                            if _new_dt is not None and _cls_dt_str != "FORMING":
                                _old_val = state.day_type.value if hasattr(state.day_type, 'value') else str(state.day_type)
                                if _new_dt != state.day_type:
                                    state.day_type = _new_dt
                                    # Update ALL surfaces that read day_type:
                                    # 1) machine.day_type (read by /status, cockpit, build-status)
                                    day_type_machine.day_type = _new_dt
                                    # 2) machine._last_state.day_type (read by to_classification)
                                    if hasattr(day_type_machine, '_last_state') and day_type_machine._last_state:
                                        day_type_machine._last_state.day_type = _new_dt
                                    _logger.info("[S1-NEW-CLS] promoted: %s → %s (%s, %s)",
                                                 _old_val, _new_dt.value, _cls_dt_str, _cls_status)
                                # 07-15 decision 4/6: promote the canonical CONFIDENCE too —
                                # the type came from the new brain while the persisted conf
                                # stayed the legacy machine's (frozen 0.26 all of 07-14).
                                # P0-3 (S1_CONFIDENCE_V2) emits it on every classify() call.
                                _cls_conf = _cls_result.get("confidence")
                                if _cls_conf is not None:
                                    # N1 RC#3 (S1_CONF_SMOOTH_V1, default OFF → smooth_confidence
                                    # returns raw unchanged): slew-cap the published confidence so
                                    # it cannot flap 0.12↔1.00 on adjacent bars (the persisted-conf
                                    # flapping proven on 07-16). Per-session prev on app.state.
                                    from backend.v9.systems.day_type.daytype_classifier import smooth_confidence as _smooth_conf
                                    _sm_today = now_et().date().isoformat()
                                    _sm_st = getattr(app.state, "_s1_conf_smooth", None) or {}
                                    _sm_prev = _sm_st.get("conf") if _sm_st.get("date") == _sm_today else None
                                    _sm_val = _smooth_conf(_sm_prev, float(_cls_conf), _cls_dt_str)
                                    if _sm_val != _cls_conf:
                                        _cls_result["confidence_raw"] = _cls_conf
                                        _cls_result["confidence"] = _sm_val
                                    app.state._s1_conf_smooth = {
                                        "date": _sm_today,
                                        "conf": (None if _cls_dt_str == "FORMING" else _sm_val),
                                    }
                                    state.confidence = float(_sm_val)
                                # N1 RC#4: freshness stamp so the v9_day_type_state publisher only
                                # copies direction/reason/sides/rib from TODAY's canonical result
                                # (a stale cross-session result must yield honest NULLs, Rule 1).
                                _cls_result["session_date"] = now_et().date().isoformat()
                                app.state.last_cls_result = _cls_result  # observability: full canonical result
                    except Exception as _cls_err:
                        # Fail-safe: keep old-engine value, never throw on hot path
                        _logger.debug("[S1-NEW-CLS] error (fail-safe, kept old value): %s", _cls_err)

                # P6 DAYTYPE_ACCEPTANCE_DEMOTION_V1 (Michael D2 06-30 + 07-22):
                # When live label is Trend_* and price returns inside IB for K
                # consecutive bars → demote one step to Normal_Variation.
                if _os.environ.get("DAYTYPE_ACCEPTANCE_DEMOTION_V1", "0").lower() in ("1", "true", "yes"):
                    try:
                        _cur_dt = getattr(day_type_machine, "day_type", None)
                        _cur_str = _cur_dt.value if hasattr(_cur_dt, "value") else str(_cur_dt or "")
                        if _cur_str.startswith("Trend"):
                            _ib_h = getattr(day_type_machine, "ib_high", None)
                            _ib_l = getattr(day_type_machine, "ib_low", None)
                            if _ib_h is not None and _ib_l is not None:
                                _ib_w = float(_ib_h) - float(_ib_l)
                                _dem_tol = min(max(0.25 * _ib_w, 1.0), 4.0) if _ib_w > 0 else 2.0
                                _bar_h = bar_input.high
                                _bar_l = bar_input.low
                                _inside = (_bar_h < float(_ib_h) - _dem_tol and
                                           _bar_l > float(_ib_l) + _dem_tol)
                                if not hasattr(app.state, "_dem_inside_count"):
                                    app.state._dem_inside_count = 0
                                if _inside:
                                    app.state._dem_inside_count += 1
                                else:
                                    app.state._dem_inside_count = 0
                                _dem_k = int(_os.environ.get("DAYTYPE_DEMOTION_K_BARS", "3"))
                                if app.state._dem_inside_count >= _dem_k:
                                    app.state._dem_inside_count = 0
                                    _dem_target = "Normal_Variation"
                                    from backend.v9.systems.day_type.state_machine import DayType as _DT2
                                    _dem_enum = _DT2.Variation  # Normal_Variation maps to Variation enum
                                    state.day_type = _dem_enum
                                    day_type_machine.day_type = _dem_enum
                                    if hasattr(day_type_machine, '_last_state') and day_type_machine._last_state:
                                        day_type_machine._last_state.day_type = _dem_enum
                                    _logger.warning(
                                        "[DayType] ACCEPTANCE-DEMOTION: %s → %s (K=%d bars re-accepted "
                                        "inside IB %.2f/%.2f)", _cur_str, _dem_target, _dem_k,
                                        float(_ib_h), float(_ib_l))
                    except Exception as _dem_err:
                        _logger.debug("[DayType] acceptance-demotion error (fail-safe): %s", _dem_err)

                # D-S1DYN: Legacy shadow reclassification (SKIPPED when S1_ENGINE_NEW_CLASSIFIER ON)
                elif S1_DYNAMIC_RECLASS and day_type_machine.ib_locked:
                    try:
                        if _shadow_reclass["instance"] is None:
                            from backend.v9.systems.day_type.shadow_reclass import ShadowReclassifier
                            _shadow_reclass["instance"] = ShadowReclassifier(
                                ib_high=day_type_machine.ib_high,
                                ib_low=day_type_machine.ib_low,
                                session_date=now_et().date().isoformat(),
                            )
                        _sr = _shadow_reclass["instance"]
                        _sr.process_bar(
                            session_high=day_type_machine.rth_session_h or day_type_machine.session_high,
                            session_low=day_type_machine.rth_session_l or day_type_machine.session_low,
                            bar_close=bar_input.close,
                            session_min=_session_min,
                            vah=None,
                            val=None,
                            poc=None,
                            cvd=None,
                        )
                        S1_LIVE_RECLASS = _os.environ.get("S1_LIVE_RECLASS", "").lower() in ("1", "true", "yes")
                        _logger.info("[D-S1DYN] Live reclass check: flag=%s shadow=%s live=%s",
                                     S1_LIVE_RECLASS, _sr.shadow_type,
                                     state.day_type.value if hasattr(state.day_type, 'value') else str(state.day_type))
                        if S1_LIVE_RECLASS and _sr.shadow_type != "Normal":
                            _old_type = state.day_type.value if hasattr(state.day_type, 'value') else str(state.day_type)
                            from backend.v9.systems.day_type.state_machine import DayType as _DT
                            _new_dt = None
                            if _sr.shadow_type == "Variation":
                                _new_dt = _DT.Variation
                            elif _sr.shadow_type == "Trend":
                                _new_dt = _DT.Trend_Normal
                            if _new_dt is not None and _new_dt != state.day_type:
                                state.day_type = _new_dt
                                if hasattr(day_type_machine, '_last_state') and day_type_machine._last_state:
                                    day_type_machine._last_state.day_type = _new_dt
                                _logger.info("[D-S1DYN] LIVE reclass: %s → %s (shadow=%s)",
                                             _old_type, _new_dt.value, _sr.shadow_type)
                    except Exception as _sr_err:
                        _logger.debug("[D-S1DYN] Shadow reclass error: %s", _sr_err)

                # Persist to v9_day_type_state (P5.1.2) — 07-15 decision 4/6:
                # SINGLE WRITER (the /process wrapper no longer persists) and
                # WRITE-ON-CHANGE only: a row means something moved (type/stage/
                # conf), not another copy of the same state (07-14: 288 dup rows,
                # 2-3 per timestamp). Full per-bar truth remains in memory +
                # app.state.last_cls_result.
                # K2 (2026-08-08): body extracted to state_persist.persist_state_row
                # with the ARM-AFTER-SUCCESS fix — the old inline block armed
                # _last_dts_sig BEFORE the INSERT, so one failed write silenced
                # the writer until the state next changed (Friday's 54-min gaps).
                try:
                    from backend.v9.systems.day_type.state_persist import persist_state_row
                    persist_state_row(
                        app.state, state, opening_type,
                        getattr(app.state, "last_cls_result", None),
                        now_et().date().isoformat(),
                    )
                except Exception as db_err:
                    _logger.warning("[DayType] DB persist skipped: %s", db_err, exc_info=True)

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

                # Publish day_type_classification on every bar (S2 needs opening_type always).
                # Was: only on change — S2 missed the first event and stayed at opening_type=NA.
                dt_val = state.day_type.value if hasattr(state.day_type, 'value') else str(state.day_type)
                # Get opening_type from the machine's classification (not TPO)
                _machine_opening = "UNKNOWN"
                if hasattr(day_type_machine, 'opening') and day_type_machine.opening:
                    _ot = getattr(day_type_machine.opening, 'opening_type', None)
                    if _ot:
                        _machine_opening = _ot.value if hasattr(_ot, 'value') else str(_ot)
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
                        "opening_type": _machine_opening,
                    })
                except Exception:
                    pass
            except Exception as e:
                _logger.warning("[DayType] process_bar error: %s", e, exc_info=True)

        # ── BOOT DAY-TYPE REPLAY (BOOT_DAYTYPE_REPLAY_V1, default OFF) ──────────
        # Symmetry fix (Michael 07-13): a backend booted LATE in the session feeds the
        # engine only post-boot live bars → fewer bars + a weaker/different label than a
        # machine booted at the open (the 07-13 dev-vs-iMac divergence). Reconstruct
        # today's session by replaying today's RTH bars from v9_bars_5min_woodies through
        # the SAME pure engine entry point (process_bar), using EACH BAR's real ET time
        # (not now()). Pure/in-memory: process_bar mutates only machine state — NO
        # bar_router publish, NO per-bar DB write, NO trade/phone side-effects. Idempotent
        # (bar_count==0 guard). Flag-OFF until Michael rules on the anti-tautological test.
        def _boot_replay_day_type_session():
            import os as _bos
            if _bos.environ.get("BOOT_DAYTYPE_REPLAY_V1", "0").lower() not in ("1", "true", "yes"):
                return
            if getattr(day_type_machine, "bar_count", 0) != 0:
                return  # already has a session (idempotent across restarts)
            try:
                from datetime import time as _t2, datetime as _dt2
                from zoneinfo import ZoneInfo as _ZI
                from backend.v9.db.read import read_all as _ra
                _ET = _ZI("America/New_York")
                _today = now_et().date().isoformat()
                _rows = _ra(
                    "SELECT ts, open, high, low, close, volume FROM v9_bars_5min_woodies "
                    "WHERE (ts AT TIME ZONE 'America/New_York')::date = :d "
                    "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
                    "AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' "
                    "AND symbol = 'MES' ORDER BY ts", {"d": _today})
                if not _rows:
                    _logger.info("[DayType] boot-replay: no RTH bars for %s yet", _today)
                    return
                _pd = _load_previous_day_context_for_startup()
                _ibh0 = _ibl0 = None
                try:
                    from backend.v9.api.v9.tpo_routes import _load_sierra_tpo as _lst
                    _st = _lst() or {}
                    if _st.get("ib_found"):
                        _ibh0, _ibl0 = _st.get("ib_high"), _st.get("ib_low")
                except Exception:
                    pass
                _last = None
                _n = 0
                for _r in _rows:
                    _ts = _r["ts"]
                    _bet = (_dt2.fromisoformat(_ts) if isinstance(_ts, str) else _ts).astimezone(_ET)
                    _sm = minutes_since_rth_open(_bet)
                    _rth = _t2(9, 30) <= _bet.time() < _t2(16, 0)
                    # Mimic the live path: Sierra IB is None until it locks (~session_min
                    # 60 = 10:30 ET), then the locked value — so the engine builds the
                    # opening + developing-IB sequence exactly as an early live boot would.
                    _ibh = _ibh0 if _sm >= 60 else None
                    _ibl = _ibl0 if _sm >= 60 else None
                    _bi = BarInput(
                        ts=_bet.timestamp(), session_min=_sm, is_rth=_rth,
                        open=float(_r["open"]), high=float(_r["high"]),
                        low=float(_r["low"]), close=float(_r["close"]),
                        volume=float(_r.get("volume") or 0),
                        pd_high=_pd.get("pd_high"), pd_low=_pd.get("pd_low"),
                        pd_close=_pd.get("pd_close"), ib_high=_ibh, ib_low=_ibl,
                    )
                    _last = day_type_machine.process_bar(_bi)
                    if _rth:
                        _cls_rth_bars.append({"o": _bi.open, "h": _bi.high,
                                              "l": _bi.low, "c": _bi.close, "v": _bi.volume})
                    _n += 1
                day_type_machine._opening_gate_bars = _cls_rth_bars
                _cls_session_date["value"] = _today
                _dt_v = getattr(getattr(_last, "day_type", None), "value", None) if _last else None
                _logger.info(
                    "[DayType] boot-replay reconstructed %d RTH bars → stage=%s "
                    "day_type=%s bar_count=%d (BOOT_DAYTYPE_REPLAY_V1)",
                    _n, getattr(day_type_machine, "stage", "?"), _dt_v,
                    getattr(day_type_machine, "bar_count", 0))

                # P6 DAYTYPE_BOOT_SEED_CANONICAL_V1 (2026-07-22): after replaying
                # bars through the engine, ALSO run classify_session on the replayed
                # bars and seed the canonical conclusion. This closes the gap where
                # boot-replay gives Variation/0.12 but the canonical says Normal
                # (or Trend). The canonical label overwrites the engine's replay label.
                if (_bos.environ.get("DAYTYPE_BOOT_SEED_CANONICAL_V1", "0").lower()
                        in ("1", "true", "yes") and len(_cls_rth_bars) >= 12):
                    try:
                        # ROOT-FIX 2026-08-13 (broken since c556a5bf 07-22, found live:
                        # day_type stuck UNKNOWN after every restart → S2 mode never
                        # reached DAY_TYPE_MODE on mac-2 → fhb_eligible=False → S2 dead):
                        # classify_session lives in classifier_core (as context_radar +
                        # daytype_classify_routes correctly import) — NOT in
                        # daytype_classifier. The old import raised ImportError on every
                        # boot and the except swallowed it as "non-fatal".
                        from backend.v9.systems.day_type.classifier_core import classify_session as _boot_cls
                        _bs_ibh, _bs_ibl = _ibh0, _ibl0
                        if _bs_ibh is None or _bs_ibl is None:
                            # Sierra IB not exported — same fallback as context_radar:
                            # IB = first 12 RTH 5-min bars (09:30-10:30 ET).
                            _ib_seg = _cls_rth_bars[:12]
                            _bs_ibh = max(b["h"] for b in _ib_seg)
                            _bs_ibl = min(b["l"] for b in _ib_seg)
                        _boot_result = _boot_cls(
                            bars=_cls_rth_bars,
                            ib_high=float(_bs_ibh), ib_low=float(_bs_ibl),
                            open_price=_cls_rth_bars[0]["o"],
                            pdh=_pd.get("pd_high"), pdl=_pd.get("pd_low"),
                        )
                        _boot_dt_str = _boot_result.get("day_type")
                        from backend.v9.systems.day_type.state_machine import DayType as _BDT
                        _BOOT_MAP = {
                            "Trend_Normal": _BDT.Trend_Normal, "Trend_DD": _BDT.Trend_DD,
                            "Normal": _BDT.Normal, "Normal_Variation": _BDT.Variation,
                            "Variation": _BDT.Variation, "Neutral_Center": _BDT.Neutral_Center,
                            "Neutral_Extreme": _BDT.Neutral_Extreme, "Nontrend": _BDT.Nontrend,
                        }
                        _boot_enum = _BOOT_MAP.get(_boot_dt_str)
                        if _boot_enum is not None and _boot_dt_str != "FORMING":
                            _old_boot = _dt_v or "?"
                            day_type_machine.day_type = _boot_enum
                            if hasattr(day_type_machine, '_last_state') and day_type_machine._last_state:
                                day_type_machine._last_state.day_type = _boot_enum
                            _logger.warning(
                                "[DayType] BOOT-SEED-CANONICAL: replay=%s → canonical=%s "
                                "(classify_session on %d RTH bars, conf=%.2f)",
                                _old_boot, _boot_dt_str, len(_cls_rth_bars),
                                float(_boot_result.get("confidence", 0)))
                            app.state.last_cls_result = _boot_result
                            # 13.08 (Michael: "מק-2 בכלל לא דרוך במערכת-1"): the seed
                            # updated only the in-memory machine — the S1 panel and
                            # every DB reader still said "No classification for
                            # today" after a restart. Persist the seeded state as a
                            # row through the SAME writer the live path uses.
                            try:
                                from backend.v9.systems.day_type.state_persist import (
                                    persist_state_row as _bs_persist,
                                )
                                _bs_state = getattr(day_type_machine, "_last_state", None)
                                if _bs_state is not None:
                                    _bs_status = _bs_persist(
                                        app.state, _bs_state,
                                        str(getattr(getattr(day_type_machine, "opening", None),
                                                    "opening_type", None) or "UNKNOWN"),
                                        _boot_result, _today,  # already ISO string
                                    )
                                    _logger.info("[DayType] boot-seed persisted: %s", _bs_status)
                            except Exception as _bs_persist_err:
                                _logger.warning(
                                    "[DayType] boot-seed persist failed (non-fatal): %s",
                                    _bs_persist_err)
                    except Exception as _bsc_err:
                        _logger.warning("[DayType] boot-seed-canonical failed (non-fatal): %s", _bsc_err)
            except Exception as _bre:
                _logger.warning("[DayType] boot-replay failed (non-fatal): %s", _bre)

        _boot_replay_day_type_session()

        bar_router.subscribe("5min", _day_type_on_bar)
        _logger.info("[Main] DayTypeStateMachine subscribed to 5min via BarRouter")

        # ── H15 TREND_STEP_ENTRY_V1 (Michael 13.08: "שוב מדרגה שהמערכת לא
        # זיהתה — זה בסדר?" → no). Stair-stepping sessions produced ZERO
        # candidates: S2/S4 look for their own shapes and LEG_RIDE only exempts
        # existing signals. This subscriber runs the proven causal detector
        # (backend/v9/systems/trend_step/detector.py — byte-faithful port of
        # scripts/replay_trend_step_entry.py, replay 2026-07-15..08-12:
        # NET +$2,378.75 / n=31 / 48% on 4 contracts) on each closed 5-min bar
        # and routes any step through the NORMAL gateway chain (system 4) —
        # every gate still applies. Flag default OFF; one candidate per bar.
        _ts_last_bar = {"ts": None}

        async def _trend_step_on_bar(event):
            try:
                from backend.v9.systems.trend_step import detector as _tsd
                if not _tsd.enabled():
                    return
                # BarEvent is an object on the router (not a dict) — read both.
                if isinstance(event, dict):
                    _bts = str(event.get("ts") or event.get("bar_ts") or "")
                else:
                    _bts = str(getattr(event, "ts", None)
                               or getattr(event, "bar_ts", None) or "")
                if _bts and _ts_last_bar["ts"] == _bts:
                    return  # one evaluation per closed bar
                _ts_last_bar["ts"] = _bts
                _setup = _tsd.build_setup()
                if not _setup:
                    return
                # One entry per STAIRCASE (2026-08-18). Dedup on the bar alone
                # only stops evaluating twice on the same bar; the same step
                # still qualified on the next bar, and the next — 4 entries on
                # one staircase on 14.08, -$555. The step identity is stable
                # across the bars it survives.
                _sid = (_setup.get("metadata") or {}).get("step_id")
                if _sid and _sid in _ts_last_bar.setdefault("steps", set()):
                    return
                if _sid:
                    _ts_last_bar["steps"].add(_sid)
                    # keep the set from growing without bound across a session
                    if len(_ts_last_bar["steps"]) > 200:
                        _ts_last_bar["steps"].clear()
                        _ts_last_bar["steps"].add(_sid)
                _gw = getattr(app.state, "trading_gateway", None)
                if _gw is None:
                    _logger.warning("[TrendStep] gateway not ready — candidate dropped")
                    return
                _res = _gw.route_setup(_setup, 4)
                if _res.get("blocked_by"):
                    _logger.warning("[TrendStep] gateway blocked: %s (%s)",
                                    _res.get("blocked_by"), str(_res.get("reason"))[:90])
                else:
                    _logger.warning("[TrendStep] ROUTED: %s @%s → %s",
                                    _setup["direction"], _setup["entry_price"],
                                    _res.get("trade_id") or _res.get("shadow") or "ok")
            except Exception as _ts_err:
                _logger.warning("[TrendStep] on-bar errored (non-fatal): %s", _ts_err)

        bar_router.subscribe("5min", _trend_step_on_bar)
        _logger.info("[Main] TrendStep detector subscribed to 5min (flag-gated)")

        # Missed-trade detector (observability — should-have-fired)
        try:
            from backend.v9.systems.build_status.missed_trade_detector import missed_trade_detector
            from zoneinfo import ZoneInfo as _ZI
            _CT = _ZI("America/Chicago")

            async def _missed_trade_on_bar(event):
                bar = event.payload if hasattr(event, 'payload') else event
                _ts = now_et()
                _ct = _ts.astimezone(_CT)
                s2_state = five_min_system.get_state() if five_min_system else {}
                s4_state = {}
                try:
                    _ws = getattr(app.state, 'woodies_system', None)
                    if _ws:
                        s4_state = _ws.current_state or {}
                except Exception:
                    pass
                missed_trade_detector.on_bar(
                    bar={
                        "ts_ct": _ct.strftime("%H:%M"),
                        "open": float(bar.get("open", bar.get("o", 0))),
                        "high": float(bar.get("high", bar.get("h", 0))),
                        "low": float(bar.get("low", bar.get("l", 0))),
                        "close": float(bar.get("close", bar.get("c", 0))),
                        "volume": float(bar.get("volume", bar.get("v", 0))),
                    },
                    s2_state=s2_state,
                    s4_state=s4_state,
                )

            bar_router.subscribe("5min", _missed_trade_on_bar)
            _logger.info("[Main] MissedTradeDetector subscribed to 5min via BarRouter")
        except Exception as _mtd_err:
            _logger.warning("[Main] MissedTradeDetector init failed: %s", _mtd_err)

        # IDEA-1 (Michael 07-13 "ואיך הוא מתעדכן?"): news-calendar auto-refresh —
        # the backend itself re-fetches the red-events calendar from the
        # TradingView API (FF fallback) on every boot + every 6h. Daemon thread,
        # never touches the trading path; a failed refresh keeps the last file.
        try:
            from backend.v9.services.news_blackout import start_auto_refresh as _news_ar
            _news_ar(interval_h=6.0)
            _logger.info("[Main] news-calendar auto-refresh started (boot + every 6h)")
        except Exception as _news_err:
            _logger.warning("[Main] news-calendar auto-refresh failed to start: %s", _news_err)

        # P31-B + P31-D: SessionBoundaryManager — idempotent daily reset at startup
        try:
            from backend.v9.services.session_boundary import SessionBoundaryManager
            from backend.v9.services.risk_validator import RiskValidator
            risk_validator = RiskValidator()
            app.state.risk_validator = risk_validator
            _sbm_db = os.path.join(os.path.dirname(__file__), '..', 'data', 'mems26_local.db')
            sbm = SessionBoundaryManager(
                db_path=_sbm_db,
                day_type_machine=day_type_machine,
                risk_validator=risk_validator,
            )
            rolled = sbm.check_rollover()
            sbm.subscribe_to_bar_router(bar_router)
            app.state.session_boundary_manager = sbm
            _logger.info("[Main] SessionBoundaryManager: rollover=%s (risk_validator + bar_router wired)", rolled)
        except Exception as sbm_err:
            _logger.warning("[Main] SessionBoundaryManager startup failed (non-fatal): %s", sbm_err)
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
        import os as _tg_os
        _tg_os.environ.setdefault("GATEWAY_DECISIONS_HYDRATE", "1")  # P10: enable hydration in production only
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

        # Enable trading mode for S2 and S4 (Shadow → Demo → Live progression).
        # LIVE_TRADING_V1 (Michael 2026-07-06): route S2/S4 to the LIVE account
        # (_execute_live) instead of demo — one mode at a time, live REPLACES demo.
        # Default OFF → demo (unchanged). This is the gateway registration the live
        # path needs: without it _is_live_enabled() is always False and _execute_live
        # is never called even when LIVE_EXECUTION_V1=1. Real orders additionally
        # require LIVE_EXECUTION_V1=1 (else _execute_live stays a no-Sierra stub).
        import os as _lt_os
        if _lt_os.getenv("LIVE_TRADING_V1", "0").lower() in ("1", "true", "yes"):
            trading_gateway.enable_live(2)   # S2 FiveMin patterns → LIVE
            trading_gateway.enable_live(4)   # S4 Woodies CCI → LIVE
            _logger.info("[Main] LIVE mode enabled: systems [2, 4] (LIVE_TRADING_V1)")
        else:
            trading_gateway.enable_demo(2)   # S2 FiveMin patterns
            trading_gateway.enable_demo(4)   # S4 Woodies CCI
            _logger.info("[Main] Demo mode enabled: systems [2, 4]")
        # P4 warm-start: restore demo_slot from open demo trade in DB
        trading_gateway.hydrate_demo_slot()

        # BOOT_HYDRATION_V1: restore daily PnL counters from DB (risk-surface)
        import os as _bh_os
        if _bh_os.getenv("BOOT_HYDRATION_V1", "0").lower() in ("1", "true", "yes"):
            trading_gateway.hydrate_live_pnl()
            _bv_status = trading_gateway.get_status()
            _logger.info(
                "[Boot-Verify] HYDRATION | daily_pnl=$%.2f | trades=%d | cons_losses=%d | source=v9_trades",
                _bv_status.get("daily_pnl", 0), _bv_status.get("trades_today", 0),
                _bv_status.get("consecutive_losses", 0),
            )

        # Pipeline 5 Phase B: the FillPoller starts LATER — after the TradeManager is
        # created + wired (see below). Starting it here saw trade_manager=None (ordering bug).

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
        # K2 (2026-08-08): the daytype-watchdog self-heal reads _app_state from
        # here — it was NEVER set anywhere, so the P2-7 signature reset was dead
        # code live (app_state=None on every call). The watchdog now also
        # resolves backend.main.app.state itself as a fallback; this is the belt.
        bar_level_detector._app_state = app.state
        bar_level_detector.subscribe(bar_router)
        app.state.trade_manager = trade_manager
        app.state.bar_level_detector = bar_level_detector
        _logger.info("[Main] BarLevelDetector subscribed to 5min — ALL trades (shadow+demo) will auto-close")
        gw = getattr(app.state, "trading_gateway", None)
        if gw is not None:
            if hasattr(gw, "set_trade_manager"):
                gw.set_trade_manager(trade_manager)
                _logger.info("[Main] TradingGateway → TradeManager wired for SHADOW PnL")
            bar_level_detector.set_gateway(gw)
            _logger.info("[Main] BarLevelDetector → Gateway wired for demo slot release")

        # Pipeline 5 Phase B: start the fill-poller NOW that trade_manager EXISTS + is wired.
        # Drives the SAME TradeManager the gateway creates trades in. (Moved here — starting
        # it during gateway-init saw tm=None.)
        # S-3 / caveat-A (cc-imac pre-live audit 07-14): start it when DEMO **or LIVE** execution
        # is armed. The LIVE fill-reader must NOT be keyed off a DEMO-only flag — else running
        # live with DEMO_EXECUTION_ENABLED=0 would silently stop correlating live Sierra fills
        # to v9_trades. No behavior change while DEMO_EXECUTION_ENABLED=1 (today); pure safety net.
        _fp_demo = os.getenv("DEMO_EXECUTION_ENABLED", "0").lower() in ("1", "true", "yes")
        _fp_live = os.getenv("LIVE_EXECUTION_V1", "0").lower() in ("1", "true", "yes")
        if _fp_demo or _fp_live:
            try:
                from backend.v9.services.fill_poller import FillPoller
                # I-57: pass the gateway so Sierra-driven closes free the slot
                # + count stops in cooldown/SSV (271/272 left the slot stuck without this)
                _fp = FillPoller(trade_manager=trade_manager, gateway=gw)
                app.state.fill_poller = _fp
                asyncio.create_task(_fp.run())
                _logger.info("[Main] Pipeline 5 FillPoller started (demo=%s live=%s)", _fp_demo, _fp_live)
            except Exception as _fp_err:
                _logger.error("[Main] FillPoller start failed (fail-safe): %s", _fp_err)

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

    # ── Lightweight startup hydration inventory (Postgres, no SQLite) ──
    # Counts critical table rows to verify data availability at boot.
    try:
        from backend.v9.db.read import read_scalar
        from backend.v9.services.market_clock import now_et
        _et = now_et()
        _hy_stats = {}

        # 1. CVD cumulative — session-bounded (resets 18:00 ET Sun-Fri).
        from datetime import time as _time_cls
        if _et.time() >= _time_cls(18, 0):
            _session_start = _et.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            _session_start = (_et - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
        _cvd_rows = read_scalar(
            "SELECT COUNT(*) FROM v9_bars_cumulative_delta WHERE ts >= :cutoff",
            {"cutoff": _session_start.isoformat()},
        ) or 0
        _hy_stats["cvd_rows_this_session"] = _cvd_rows

        # 2. Woodies 5min buffer: count available bars for CCI-14 warm-up.
        _w5_count = read_scalar("SELECT COUNT(*) FROM v9_bars_5min_woodies") or 0
        _hy_stats["woodies_5min_total"] = _w5_count

        # 3. 5min bars available for system buffers.
        _b5_count = read_scalar("SELECT COUNT(*) FROM v9_bars_5min") or 0
        _hy_stats["bars_5min_total"] = _b5_count

        # 4. Sessions archived (for Y IB).
        _arch_count = read_scalar("SELECT COUNT(*) FROM v9_tpo_sessions_archive") or 0
        _hy_stats["tpo_sessions_archived"] = _arch_count

        _logger.info("[Main] Startup hydration inventory (PG): %s", _hy_stats)
    except Exception as _hy_err:
        _logger.warning("[Main] Startup hydration check failed (non-fatal): %s", _hy_err)

    # Historical Replay: warm system buffers from DB (D2.2)
    # db_path is vestigial — HistoricalReplay reads via PG (read_all), not SQLite.
    from backend.v9.services.historical_replay import HistoricalReplay
    historical = HistoricalReplay(db_path="unused-pg-only", bar_router=bar_router)
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
