"""V9 API: Bar data endpoints — receives Bridge pushes for all bar types."""

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
    for bar in bars:
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
    db.commit()
    publish_event(CHANNEL_BARS_5MIN, {
        "count": len(created),
        "last": {"o": bars[-1].o, "h": bars[-1].h, "l": bars[-1].l,
                 "c": bars[-1].c, "vol": bars[-1].vol} if bars else {},
    })
    return {"ok": True, "inserted": len(created)}


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
    return {"ok": True, "updated": updated, "skipped": skipped, "type": "cumulative_delta"}


# ── POST /api/v9/bars/woodies ──

@router.post("/woodies")
def post_woodies(
    payload: WoodiesPayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    created = 0
    for bar in payload.bars:
        ohlc = bar.get("ohlc", {})
        row = V9Bar30MinWoodies(
            ts=_ts_from_unix(bar.get("ts")),
            open=ohlc.get("o", bar.get("o", 0)),
            high=ohlc.get("h", bar.get("h", 0)),
            low=ohlc.get("l", bar.get("l", 0)),
            close=ohlc.get("c", bar.get("c", 0)),
            volume=ohlc.get("vol", bar.get("vol", 0)),
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
    db.commit()
    publish_event(CHANNEL_BARS_WOODIES, {"count": created})
    return {"ok": True, "inserted": created, "type": "woodies"}


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
