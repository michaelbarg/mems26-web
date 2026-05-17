"""V9 API: Bar data endpoints — receives Bridge pushes for all bar types."""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.v9.db.session import get_db
from backend.v9.db.models import V9Bar5Min, V9BarTickReversal, V9BarFootprint, V9Bar30MinWoodies, V9TpoBar
from backend.v9.api.v9.auth import verify_bridge_token
from backend.v9.api.v9.ws_manager import (
    publish_event, CHANNEL_BARS_5MIN, CHANNEL_BARS_TICK_REVERSAL,
    CHANNEL_BARS_WOODIES, CHANNEL_LEVELS,
)
from backend.v9.services.bar_integrity import bar_is_valid

logger = logging.getLogger(__name__)

# EventDispatcher instance — set at startup by app initialization.
# Module-level reference so all endpoint handlers can route bars.
_event_dispatcher = None

# StreamHealthService instance — set at startup.
_stream_health = None

# BarRouter instance — set at startup (D1.3)
_bar_router = None


def set_bar_router(router) -> None:
    """Called once at startup to inject the BarRouter instance."""
    global _bar_router
    _bar_router = router


def _route_bar(bar_type: str, bar_data: dict) -> None:
    """Route a bar to BarRouter if available.

    Sync wrapper that schedules async publish on the running event loop.
    D1.9.2: fixed to actually deliver bar data.
    """
    if _bar_router is not None:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            asyncio.ensure_future(_bar_router.publish(bar_type, bar_data), loop=loop)
        except RuntimeError:
            # No running event loop — fallback to thread-safe call
            try:
                import threading
                def _bg():
                    asyncio.run(_bar_router.publish(bar_type, bar_data))
                threading.Thread(target=_bg, daemon=True).start()
            except Exception:
                logger.debug("[bars] BarRouter publish skipped for %s", bar_type)


def set_event_dispatcher(dispatcher) -> None:
    """Called once at startup to inject the EventDispatcher instance."""
    global _event_dispatcher
    _event_dispatcher = dispatcher


def set_stream_health(service) -> None:
    """Called once at startup to inject the StreamHealthService instance."""
    global _stream_health
    _stream_health = service


def _dispatch(stream_name: str, bar_data: dict) -> None:
    """Route a bar to EventDispatcher if available."""
    if _event_dispatcher is not None:
        try:
            _event_dispatcher.on_bar_received(stream_name, bar_data)
        except Exception:
            logger.exception("[bars] dispatch to EventDispatcher failed for stream %s", stream_name)


def _record_push(stream_name: str) -> None:
    """Record a successful push in StreamHealthService."""
    if _stream_health is not None:
        try:
            _stream_health.record_push(stream_name)
        except Exception:
            pass


def _record_error(stream_name: str, error: str) -> None:
    """Record an error in StreamHealthService."""
    if _stream_health is not None:
        try:
            _stream_health.record_error(stream_name, error)
        except Exception:
            pass

router = APIRouter(prefix="/api/v9/bars", tags=["v9-bars"])


# ── Pydantic schemas ──

class Bar5MinIn(BaseModel):
    ts: Optional[float] = None
    symbol: str = "MES"
    o: float
    h: float
    l: float
    c: float
    vol: int = 0
    poc_vol: Optional[int] = None
    vah: Optional[float] = None
    val: Optional[float] = None
    cumulative_delta: Optional[float] = None


class TickReversalPayload(BaseModel):
    """Full DLL export payload for tick reversal bars."""
    type: str = "tick_reversal"
    tick_count: Optional[int] = 15
    version: Optional[str] = None
    bar_count: Optional[int] = None
    export_ts: Optional[float] = None
    bars: List[Dict] = []


class FootprintPayload(BaseModel):
    """Full DLL export payload for footprint data."""
    type: str = "footprint"
    version: Optional[str] = None
    bar_count: Optional[int] = None
    cumulative_delta: Optional[float] = None
    export_ts: Optional[float] = None
    bars: List[Dict] = []


class VolumeProfilePayload(BaseModel):
    type: str = "volume_profile"
    version: Optional[str] = None
    export_ts: Optional[float] = None
    bars: List[Dict] = []


class ImbalancePayload(BaseModel):
    type: str = "imbalance_flags"
    version: Optional[str] = None
    total_buy_imbalances: Optional[int] = None
    total_sell_imbalances: Optional[int] = None
    bars_with_imbalances: Optional[int] = None
    export_ts: Optional[float] = None
    bars: List[Dict] = []


class StackedImbalancePayload(BaseModel):
    type: str = "stacked_imbalances"
    version: Optional[str] = None
    export_ts: Optional[float] = None
    bars: List[Dict] = []


class CumulativeDeltaPayload(BaseModel):
    type: str = "cumulative_delta"
    version: Optional[str] = None
    export_ts: Optional[float] = None
    bars: List[Dict] = []


class WoodiesPayload(BaseModel):
    type: str = "woodies_30min"
    version: Optional[str] = None
    export_ts: Optional[float] = None
    bars: List[Dict] = []
    history: List[Dict] = []  # DLL uses "history" key

    @property
    def all_bars(self) -> List[Dict]:
        """DLL exports 'history', Bridge may send 'bars'. Accept both."""
        return self.bars if self.bars else self.history


class TpoPayload(BaseModel):
    bars: List[Dict] = []
    export_ts: Optional[float] = None


# ── Helpers ──

def _ts_from_unix(unix_ts) -> datetime:
    if unix_ts is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(float(unix_ts), tz=timezone.utc)


# ── POST /api/v9/bars/5min ──

@router.post("/5min")
def post_bars_5min(
    bars: List[Bar5MinIn],
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    created = []
    rejected = 0
    last_valid_bar = None
    for bar in bars:
        ok, reason = bar_is_valid(open=bar.o, high=bar.h, low=bar.l, close=bar.c)
        if not ok:
            logger.warning(
                "[bars/5min] rejected bar: o=%.2f h=%.2f l=%.2f c=%.2f reason=%s",
                bar.o, bar.h, bar.l, bar.c, reason,
            )
            rejected += 1
            continue
        row = V9Bar5Min(
            ts=_ts_from_unix(bar.ts),
            symbol=bar.symbol,
            open=bar.o, high=bar.h, low=bar.l, close=bar.c,
            volume=bar.vol,
            poc_vol=bar.poc_vol, vah=bar.vah, val=bar.val,
            cumulative_delta=bar.cumulative_delta,
        )
        db.add(row)
        created.append(row)
        last_valid_bar = bar
    db.commit()
    publish_event(CHANNEL_BARS_5MIN, {
        "count": len(created),
        "rejected": rejected,
        "last": {"o": last_valid_bar.o, "h": last_valid_bar.h, "l": last_valid_bar.l,
                 "c": last_valid_bar.c, "vol": last_valid_bar.vol} if last_valid_bar else {},
    })
    # Route last bar to EventDispatcher (5min bars derive from cumulative_delta)
    if last_valid_bar:
        _dispatch("cumulative_delta", last_valid_bar.dict())
    _record_push("5min")
    if last_valid_bar:
        _route_bar("5min", last_valid_bar.dict() if hasattr(last_valid_bar, 'dict') else {"ts": str(last_valid_bar.ts)})
    return {"ok": True, "inserted": len(created), "rejected": rejected}


# ── POST /api/v9/bars/tick_reversal?tick_count=15 ──

@router.post("/tick_reversal")
def post_tick_reversal(
    payload: TickReversalPayload,
    tick_count: int = Query(15),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    created = 0
    for bar in payload.bars:
        row = V9BarTickReversal(
            ts=_ts_from_unix(bar.get("ts")),
            tick_size=tick_count,
            open=bar["o"], high=bar["h"], low=bar["l"], close=bar["c"],
            volume=bar.get("vol", 0),
            ask_vol=bar.get("ask_vol"),
            bid_vol=bar.get("bid_vol"),
            delta=bar.get("delta"),
            direction=bar.get("dir"),
        )
        db.add(row)
        created += 1
    db.commit()
    publish_event(CHANNEL_BARS_TICK_REVERSAL, {
        "count": created, "tick_count": tick_count,
    })
    # Route last bar to EventDispatcher
    if payload.bars:
        stream = "tick_reversal_%d" % tick_count
        _dispatch(stream, payload.bars[-1])
        _record_push(stream)
        _route_bar(stream, payload.bars[-1] if isinstance(payload.bars[-1], dict) else {"ts": ""})
    return {"ok": True, "inserted": created, "tick_count": tick_count}


# ── POST /api/v9/bars/footprint ──

@router.post("/footprint")
def post_footprint(
    payload: FootprintPayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    created = 0
    for bar in payload.bars:
        row = V9BarFootprint(
            ts=_ts_from_unix(bar.get("ts")),
            open=bar["o"], high=bar["h"], low=bar["l"], close=bar["c"],
            volume=bar.get("vol", 0),
            delta=bar.get("delta"),
            poc_price=bar.get("poc_price"),
            poc_vol=bar.get("poc_vol"),
            levels=bar.get("levels", []),
            stacked_buy=bar.get("stacked_buy"),
            stacked_sell=bar.get("stacked_sell"),
        )
        db.add(row)
        created += 1
    db.commit()
    # Route last bar to EventDispatcher
    if payload.bars:
        _dispatch("footprint", payload.bars[-1])
    _record_push("footprint")
    _route_bar("footprint", payload.dict() if hasattr(payload, "dict") else {"ts": ""})
    return {"ok": True, "inserted": created, "type": "footprint"}


# ── POST /api/v9/bars/volume_profile ──

@router.post("/volume_profile")
def post_volume_profile(
    payload: VolumeProfilePayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    # Enrich existing 5-min bars with profile data (UPDATE, not INSERT).
    # Match by closest ts within a 5-minute window.
    from datetime import timedelta
    updated = 0
    skipped = 0
    for bar in payload.bars:
        ts = _ts_from_unix(bar.get("ts"))
        window = timedelta(minutes=5)
        row = db.query(V9Bar5Min).filter(
            V9Bar5Min.ts >= ts - window,
            V9Bar5Min.ts <= ts + window,
        ).order_by(V9Bar5Min.ts).first()
        if row:
            row.poc_vol = bar.get("poc_vol", row.poc_vol)
            row.vah = bar.get("vah", row.vah)
            row.val = bar.get("val", row.val)
            updated += 1
        else:
            skipped += 1
    db.commit()
    # Route last bar to EventDispatcher
    if payload.bars:
        _dispatch("volume_profile", payload.bars[-1])
    _record_push("volume_profile")
    _route_bar("volume_profile", payload.dict() if hasattr(payload, "dict") else {"ts": ""})
    return {"ok": True, "updated": updated, "skipped": skipped, "type": "volume_profile"}


# ── POST /api/v9/bars/imbalance ──

@router.post("/imbalance")
def post_imbalance(
    payload: ImbalancePayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    # Store imbalance flags as system signals (system_id=3, footprint observer)
    from backend.v9.db.models import V9SystemSignal
    created = 0
    for bar in payload.bars:
        signal = V9SystemSignal(
            ts=_ts_from_unix(bar.get("ts")),
            system_id=3,
            classification="IMBALANCE",
            direction=None,
            payload={
                "bar_idx": bar.get("bar_idx"),
                "price": bar.get("price"),
                "stacked_buy": bar.get("stacked_buy"),
                "stacked_sell": bar.get("stacked_sell"),
                "levels": bar.get("levels", []),
            },
        )
        db.add(signal)
        created += 1
    db.commit()
    _record_push("imbalance_flags")
    _route_bar("imbalance", payload.dict() if hasattr(payload, "dict") else {"ts": ""})
    return {"ok": True, "inserted": created, "type": "imbalance",
            "total_buy": payload.total_buy_imbalances,
            "total_sell": payload.total_sell_imbalances}


# ── POST /api/v9/bars/stacked_imbalance ──

@router.post("/stacked_imbalance")
def post_stacked_imbalance(
    payload: StackedImbalancePayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    from backend.v9.db.models import V9SystemSignal
    created = 0
    for bar in payload.bars:
        signal = V9SystemSignal(
            ts=_ts_from_unix(bar.get("ts")),
            system_id=3,
            classification="STACKED_IMBALANCE",
            direction=None,
            payload=bar,
        )
        db.add(signal)
        created += 1
    db.commit()
    _record_push("stacked_imbalances")
    _route_bar("stacked_imbalance", payload.dict() if hasattr(payload, "dict") else {"ts": ""})
    return {"ok": True, "inserted": created, "type": "stacked_imbalance"}


# ── POST /api/v9/bars/cumulative_delta ──

@router.post("/cumulative_delta")
def post_cumulative_delta(
    payload: CumulativeDeltaPayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    # Enrich existing 5-min bars with cumulative delta (UPDATE, not INSERT).
    from datetime import timedelta
    updated = 0
    skipped = 0
    for bar in payload.bars:
        ts = _ts_from_unix(bar.get("ts"))
        window = timedelta(minutes=5)
        row = db.query(V9Bar5Min).filter(
            V9Bar5Min.ts >= ts - window,
            V9Bar5Min.ts <= ts + window,
        ).order_by(V9Bar5Min.ts).first()
        if row:
            row.cumulative_delta = bar.get("cumulative_delta") or bar.get("delta")
            updated += 1
        else:
            skipped += 1
    db.commit()
    # Route last bar to EventDispatcher
    if payload.bars:
        _dispatch("cumulative_delta", payload.bars[-1])
    _record_push("cumulative_delta")
    _route_bar("cumulative_delta", payload.dict() if hasattr(payload, "dict") else {"ts": ""})
    return {"ok": True, "updated": updated, "skipped": skipped, "type": "cumulative_delta"}


# ── POST /api/v9/bars/woodies ──

@router.post("/woodies")
def post_woodies(
    payload: WoodiesPayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    bars = payload.all_bars  # Fix 2: accept both "history" and "bars" keys
    created = 0
    last_flat = None
    for bar in bars:
        ohlc = bar.get("ohlc", {})
        o = ohlc.get("o", bar.get("o", 0))
        h = ohlc.get("h", bar.get("h", 0))
        l = ohlc.get("l", bar.get("l", 0))
        c = ohlc.get("c", bar.get("c", 0))
        vol = ohlc.get("vol", bar.get("vol", 0))
        row = V9Bar30MinWoodies(
            ts=_ts_from_unix(bar.get("ts")),
            open=o, high=h, low=l, close=c, volume=vol,
            cci_14=bar.get("cci_14"),
            cci_6_tcci=bar.get("cci_6_tcci"),
            lsma_value=bar.get("lsma_value"),
            swi_value=bar.get("swi_value"),
            czi_value=bar.get("czi_value"),
            ema_34=bar.get("ema_34"),
            trend_state=bar.get("trend_state"),
            predictor_next_cci=bar.get("predictor_next_cci"),
            zlr_detected=bar.get("zlr_detected", False),
            zlr_direction=bar.get("zlr_direction"),
        )
        db.add(row)
        created += 1
        # Fix 4: build flat bar dict for BarRouter (process_bar expects flat keys)
        last_flat = {
            "ts": bar.get("ts"), "open": o, "high": h, "low": l, "close": c,
            "volume": vol, "cci_14": bar.get("cci_14"),
            "cci_6_tcci": bar.get("cci_6_tcci"), "ema_34": bar.get("ema_34"),
            "lsma_value": bar.get("lsma_value"), "swi_value": bar.get("swi_value"),
            "czi_value": bar.get("czi_value"), "trend_state": bar.get("trend_state"),
            "predictor_next_cci": bar.get("predictor_next_cci"),
        }
    db.commit()
    publish_event(CHANNEL_BARS_WOODIES, {"count": created})
    # Route last bar to EventDispatcher
    if bars:
        _dispatch("woodies_30min", bars[-1])
    _record_push("woodies_30min")
    # Fix 3: topic "woodies_30min" (was "woodies") + Fix 4: flat bar dict
    if last_flat:
        _route_bar("woodies_30min", last_flat)
    return {"ok": True, "inserted": created, "type": "woodies"}


# ── POST /api/v9/bars/woodies_5min (D-074: primary S4 path) ──

@router.post("/woodies_5min")
def post_woodies_5min(
    payload: WoodiesPayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    """D-074: Woodies 5-min bars — primary S4 data path.

    Same payload shape as /woodies (legacy 30-min) but persisted to
    v9_bars_5min_woodies and routed as topic 'woodies_5min'.
    """
    bars = payload.all_bars
    if not bars:
        return {"ok": True, "inserted": 0, "type": "woodies_5min"}
    created = 0
    last_flat = None
    for bar in bars:
        ohlc = bar.get("ohlc", {})
        o = ohlc.get("o", bar.get("o", bar.get("open", 0)))
        h = ohlc.get("h", bar.get("h", bar.get("high", 0)))
        l = ohlc.get("l", bar.get("l", bar.get("low", 0)))
        c = ohlc.get("c", bar.get("c", bar.get("close", 0)))
        vol = ohlc.get("vol", bar.get("vol", bar.get("volume", 0)))
        # Persist to v9_bars_5min_woodies (dedicated table per D-074)
        import sqlite3 as _sql
        try:
            conn = _sql.connect("/Users/michael/Downloads/mems26_web_git/data/mems26_local.db")
            conn.execute(
                """INSERT INTO v9_bars_5min_woodies
                (ts, open, high, low, close, volume, cci_14, cci_6_tcci,
                 lsma_value, swi_value, czi_value, ema_34, trend_state,
                 predictor_next_cci, zlr_detected, zlr_direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    bar.get("ts", ""), o, h, l, c, vol,
                    bar.get("cci_14"), bar.get("cci_6_tcci"),
                    bar.get("lsma_value"), bar.get("swi_value"),
                    bar.get("czi_value"), bar.get("ema_34"),
                    bar.get("trend_state"), bar.get("predictor_next_cci"),
                    bar.get("zlr_detected", False), bar.get("zlr_direction"),
                ),
            )
            conn.commit()
            conn.close()
            created += 1
        except Exception:
            pass
        last_flat = {
            "ts": bar.get("ts"), "open": o, "high": h, "low": l, "close": c,
            "volume": vol, "cci_14": bar.get("cci_14"),
            "cci_6_tcci": bar.get("cci_6_tcci"), "ema_34": bar.get("ema_34"),
            "lsma_value": bar.get("lsma_value"), "swi_value": bar.get("swi_value"),
            "czi_value": bar.get("czi_value"), "trend_state": bar.get("trend_state"),
            "predictor_next_cci": bar.get("predictor_next_cci"),
        }
    _record_push("woodies_5min")
    if last_flat:
        _route_bar("woodies_5min", last_flat)
    return {"ok": True, "inserted": created, "type": "woodies_5min"}


# ── POST /api/v9/bars/tpo ──

@router.post("/tpo")
def post_tpo(
    payload: TpoPayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    created = 0
    for bar in payload.bars:
        row = V9TpoBar(
            ts=_ts_from_unix(bar.get("ts")),
            letter=bar.get("letter", "A"),
            price=bar.get("price", 0),
            level=bar.get("level", 0),
            period_id=bar.get("period_id", 0),
        )
        db.add(row)
        created += 1
    db.commit()
    publish_event(CHANNEL_LEVELS, {"count": created, "type": "tpo"})
    # Route last bar to EventDispatcher (TPO shares volume_profile stream)
    if payload.bars:
        _dispatch("volume_profile", payload.bars[-1])
    _record_push("tpo")
    _route_bar("tpo", payload.dict() if hasattr(payload, "dict") else {"ts": ""})
    return {"ok": True, "inserted": created, "type": "tpo"}


# ── GET endpoints ──

@router.get("/5min")
def get_bars_5min(
    limit: int = Query(100, le=500),
    symbol: str = Query("MES"),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    rows = db.query(V9Bar5Min).filter(
        V9Bar5Min.symbol == symbol
    ).order_by(V9Bar5Min.ts.desc()).limit(limit).all()
    return {"bars": [
        {"id": r.id, "ts": r.ts.isoformat(), "o": r.open, "h": r.high,
         "l": r.low, "c": r.close, "vol": r.volume,
         "poc_vol": r.poc_vol, "vah": r.vah, "val": r.val,
         "cumulative_delta": r.cumulative_delta}
        for r in rows
    ]}


@router.get("/tick_reversal")
def get_tick_reversal(
    tick_count: int = Query(15),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    rows = db.query(V9BarTickReversal).filter(
        V9BarTickReversal.tick_size == tick_count
    ).order_by(V9BarTickReversal.ts.desc()).limit(limit).all()
    return {"bars": [
        {"id": r.id, "ts": r.ts.isoformat(), "tick_size": r.tick_size,
         "o": r.open, "h": r.high, "l": r.low, "c": r.close,
         "vol": r.volume, "ask_vol": r.ask_vol, "bid_vol": r.bid_vol,
         "delta": r.delta, "dir": r.direction,
         "footprint": r.footprint_json, "cluster": r.cluster_data}
        for r in rows
    ]}


@router.get("/woodies")
def get_woodies(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    rows = db.query(V9Bar30MinWoodies).order_by(
        V9Bar30MinWoodies.ts.desc()
    ).limit(limit).all()
    return {"bars": [
        {"id": r.id, "ts": r.ts.isoformat(),
         "o": r.open, "h": r.high, "l": r.low, "c": r.close, "vol": r.volume,
         "cci_14": r.cci_14, "cci_6_tcci": r.cci_6_tcci,
         "lsma_value": r.lsma_value, "swi_value": r.swi_value,
         "czi_value": r.czi_value, "ema_34": r.ema_34,
         "trend_state": r.trend_state, "predictor_next_cci": r.predictor_next_cci,
         "zlr_detected": r.zlr_detected, "zlr_direction": r.zlr_direction}
        for r in rows
    ]}


@router.get("/tpo")
def get_tpo(
    limit: int = Query(200, le=1000),
    period_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    q = db.query(V9TpoBar)
    if period_id is not None:
        q = q.filter(V9TpoBar.period_id == period_id)
    rows = q.order_by(V9TpoBar.ts.desc()).limit(limit).all()
    return {"bars": [
        {"id": r.id, "ts": r.ts.isoformat(), "letter": r.letter,
         "price": r.price, "level": r.level, "period_id": r.period_id}
        for r in rows
    ]}
