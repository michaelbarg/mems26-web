"""V9 API: Bar data endpoints — receives Bridge pushes for all bar types."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from fastapi import APIRouter, Body, Depends, Query, HTTPException
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
    """Route a bar to BarRouter via thread-safe publish (P27.5c fix)."""
    if _bar_router is not None:
        _bar_router.publish_threadsafe(bar_type, bar_data)


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
    """Sierra `volume_profile.json` payload.

    P31 Phase 1 (2026-05-22): Sierra exports the per-bar profile array under
    the key ``profiles[]`` (each entry: ``bar_idx, poc, poc_vol, vah, val,
    total_vol, levels[]``). The legacy ``bars: List[Dict]`` field stayed
    here for ~6 months as dead code — Pydantic silently dropped the
    `profiles` array and the handler iterated an empty list, so every
    5-min bar got ``poc_vol=0, vah=0, val=0`` (real values lost). Adding
    ``profiles`` here closes the gap. Keep ``bars`` as a fallback so any
    in-memory bridge / test that still uses the old key continues to work.
    """

    type: str = "volume_profile"
    version: Optional[str] = None
    export_ts: Optional[float] = None
    va_pct: Optional[float] = None
    bar_count: Optional[int] = None
    profiles: List[Dict] = []
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
    """Sierra `stacked_imbalances.json` payload.

    P31 Phase 1 (2026-05-22): the export uses ``stacks[]`` (not ``bars[]``).
    Same root cause as VP — handler iterated empty `bars`, never persisted
    any stacked-imbalance event. Add ``stacks`` and keep ``bars`` for
    backward compat.
    """

    type: str = "stacked_imbalances"
    version: Optional[str] = None
    export_ts: Optional[float] = None
    min_stack: Optional[int] = None
    total_stacked_bars: Optional[int] = None
    stacks: List[Dict] = []
    bars: List[Dict] = []


class CumulativeDeltaPayload(BaseModel):
    """Sierra `cumulative_delta.json` payload.

    P31 Phase 1 (2026-05-22): the export uses ``points[]`` (each entry:
    ``i, t, d, cum, p``). Same root cause as VP / Stacked-imbalance —
    handler iterated empty `bars`, so the dedicated table
    ``v9_bars_cumulative_delta`` stayed empty even though
    ``v9_bars_5min.cumulative_delta`` enrichment worked (because that
    enrichment path lives inside the 5min POST handler, not here).
    """

    type: str = "cumulative_delta"
    version: Optional[str] = None
    export_ts: Optional[float] = None
    output_interval: Optional[int] = None
    current_delta: Optional[float] = None
    session_delta: Optional[float] = None
    peak: Optional[float] = None
    trough: Optional[float] = None
    divergence: Optional[bool] = None
    trend: Optional[str] = None
    points: List[Dict] = []
    bars: List[Dict] = []


class WoodiesPayload(BaseModel):
    type: str = "woodies_30min"
    version: Optional[str] = None
    export_ts: Optional[float] = None
    bars: List[Dict] = []
    history: List[Dict] = []
    current_bar: Optional[Dict] = None

    @property
    def all_bars(self) -> List[Dict]:
        if self.bars:
            return self.bars
        if self.history:
            return self.history
        if self.current_bar:
            return [self.current_bar]
        return []


class Woodies5MinPayload(BaseModel):
    type: str = "woodies_5min"
    version: Optional[str] = None
    export_ts: Optional[float] = None
    bars: List[Dict] = []
    history: List[Dict] = []
    current_bar: Optional[Dict] = None

    @property
    def all_bars(self) -> List[Dict]:
        if self.bars:
            return self.bars
        if self.history:
            return self.history
        if self.current_bar:
            return [self.current_bar]
        return []


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
    """Upsert 5-min OHLC bars by (ts, symbol).

    P30 G8 (2026-05-20): two concurrent bridge POSTs for the same bar used to
    race past the SELECT-then-INSERT check and create duplicate rows, which
    broke `lightweight-charts` (assertion "data must be asc ordered by time").
    The DB now has a `UNIQUE(ts, symbol)` constraint and this handler catches
    `IntegrityError` to retry as UPDATE — safe under concurrency.
    """
    from sqlalchemy.exc import IntegrityError

    created = []
    rejected = 0
    last_valid_bar = None

    def _apply_fields(target: V9Bar5Min, src: Bar5MinIn) -> None:
        target.open = src.o
        target.high = src.h
        target.low = src.l
        target.close = src.c
        target.volume = src.vol
        target.poc_vol = src.poc_vol
        target.vah = src.vah
        target.val = src.val
        target.cumulative_delta = src.cumulative_delta

    def _flat_5min_for_router(bar: Bar5MinIn, ts) -> dict:
        """Flat keys for FiveMinSystem + BarLevelDetector (P31-02)."""
        return {
            "ts": str(ts),
            "o": bar.o,
            "h": bar.h,
            "l": bar.l,
            "c": bar.c,
            "vol": bar.vol,
            "open": bar.o,
            "high": bar.h,
            "low": bar.l,
            "close": bar.c,
            "volume": bar.vol,
        }

    for bar in bars:
        ok, reason = bar_is_valid(open=bar.o, high=bar.h, low=bar.l, close=bar.c)
        if not ok:
            logger.warning(
                "[bars/5min] rejected bar: o=%.2f h=%.2f l=%.2f c=%.2f reason=%s",
                bar.o, bar.h, bar.l, bar.c, reason,
            )
            rejected += 1
            continue
        ts = _ts_from_unix(bar.ts)
        # Guard: reject bars with ts > now + 2 minutes (mirror bar_ingestion guard)
        if ts > datetime.now(timezone.utc) + timedelta(minutes=2):
            logger.warning("[bars/5min] Rejected FUTURE bar ts=%s (now+2m guard)", ts)
            rejected += 1
            continue
        row = db.query(V9Bar5Min).filter(
            V9Bar5Min.ts == ts,
            V9Bar5Min.symbol == bar.symbol,
        ).first()
        if row is None:
            row = V9Bar5Min(ts=ts, symbol=bar.symbol)
            _apply_fields(row, bar)
            db.add(row)
            try:
                db.flush()  # surface IntegrityError before any further mutation
                created.append(row)
            except IntegrityError:
                db.rollback()
                # Concurrent insert won the race — fetch the row that was committed
                # by the other POST and update it with our latest data instead.
                row = db.query(V9Bar5Min).filter(
                    V9Bar5Min.ts == ts,
                    V9Bar5Min.symbol == bar.symbol,
                ).one()
                _apply_fields(row, bar)
                logger.info(
                    "[bars/5min] race-condition upsert resolved for ts=%s sym=%s",
                    ts, bar.symbol,
                )
        else:
            _apply_fields(row, bar)
        last_valid_bar = bar
    db.commit()
    publish_event(CHANNEL_BARS_5MIN, {
        "count": len(created),
        "rejected": rejected,
        "last": {"o": last_valid_bar.o, "h": last_valid_bar.h, "l": last_valid_bar.l,
                 "c": last_valid_bar.c, "vol": last_valid_bar.vol} if last_valid_bar else {},
    })
    _record_push("5min")
    # P31-02: route on every upsert (INSERT or UPDATE), not only new rows.
    if last_valid_bar is not None:
        _route_bar("5min", _flat_5min_for_router(last_valid_bar, _ts_from_unix(last_valid_bar.ts)))
    return {"ok": True, "inserted": len(created), "rejected": rejected}


# ── POST /api/v9/bars/tick_reversal?tick_count=15 ──

@router.post("/tick_reversal")
def post_tick_reversal(
    payload: TickReversalPayload,
    tick_count: int = Query(15),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    # TICK_REVERSAL_DISABLED: skip DB writes (highest-frequency ORM writer → corruption source)
    from backend.v9.shared.atr import flag
    if flag("TICK_REVERSAL_DISABLED"):
        # Still dispatch to BarRouter for S3 (if enabled) but don't persist
        if payload.bars:
            stream = "tick_reversal_%d" % tick_count
            _dispatch(stream, payload.bars[-1])
            _record_push(stream)
            _route_bar(stream, payload.bars[-1] if isinstance(payload.bars[-1], dict) else {"ts": ""})
        return {"ok": True, "inserted": 0, "tick_count": tick_count, "disabled": True}
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
    """Enrich latest 5-min bars with VP POC/VAH/VAL **and** persist the full
    per-price-level profile to ``v9_bars_volume_profile`` for backtest replay
    (Michael 2026-05-22, ``save_full_profile`` choice).

    Sierra's ``volume_profile.json`` carries 31 ``profiles[]`` rows — each is
    the profile for one 5-min bar, in chronological order. Profiles have
    ``bar_idx`` but no ``ts``, so we match the last N profiles positionally
    to the last N rows in ``v9_bars_5min`` (by ``ts DESC``). This is the
    pragmatic ``Path-B`` (no DLL change) per
    ``CC_UNIFIED_HISTORY_ARCHITECTURE_SPEC.md``.

    Idempotency: the dedicated table has ``bar_id TEXT UNIQUE``, so INSERTs
    use ``INSERT OR REPLACE`` keyed on ``bar_id = "vp_<bar_idx>"``.
    """
    from datetime import timedelta
    import json as _json
    from sqlalchemy import text as _sql_text

    profiles = payload.profiles or payload.bars  # backward-compat fallback
    updated = 0
    skipped = 0
    inserted = 0

    if profiles:
        # Positional match: take the latest len(profiles) rows from
        # v9_bars_5min (by ts DESC, then reverse so oldest→newest aligns
        # with profiles oldest→newest).
        latest_bars = (
            db.query(V9Bar5Min)
            .order_by(V9Bar5Min.ts.desc())
            .limit(len(profiles))
            .all()
        )
        latest_bars = list(reversed(latest_bars))

        offset = max(0, len(latest_bars) - len(profiles))
        for i, prof in enumerate(profiles[-len(latest_bars):]) if latest_bars else enumerate([]):
            row = latest_bars[i + offset] if i + offset < len(latest_bars) else None
            if row is not None:
                row.poc_vol = prof.get("poc_vol", row.poc_vol)
                row.vah = prof.get("vah", row.vah)
                row.val = prof.get("val", row.val)
                updated += 1
            else:
                skipped += 1

        # Dedicated table — persist FULL profile JSON for backtests.
        for prof in profiles:
            bar_idx = prof.get("bar_idx")
            if bar_idx is None:
                # Sierra always emits bar_idx; missing → corrupt — skip.
                continue
            try:
                db.execute(
                    _sql_text(
                        "INSERT OR REPLACE INTO v9_bars_volume_profile "
                        "(ts, bar_id, profile, poc, vah, val, total_volume, session, created_at) "
                        "VALUES (:ts, :bar_id, :profile, :poc, :vah, :val, :total_volume, :session, CURRENT_TIMESTAMP)"
                    ),
                    {
                        "ts": _ts_from_unix(payload.export_ts).isoformat(),
                        "bar_id": f"vp_{bar_idx}",
                        "profile": _json.dumps(prof.get("levels") or []),
                        "poc": prof.get("poc"),
                        "vah": prof.get("vah"),
                        "val": prof.get("val"),
                        "total_volume": int(prof.get("total_vol") or 0),
                        "session": None,
                    },
                )
                inserted += 1
            except Exception as e:
                logger.warning("[VP] dedicated INSERT failed bar_idx=%s: %s", bar_idx, e)
    db.commit()
    # Route last profile to EventDispatcher (kept for downstream consumers)
    if profiles:
        _dispatch("volume_profile", profiles[-1])
    _record_push("volume_profile")
    _route_bar("volume_profile", payload.dict() if hasattr(payload, "dict") else {"ts": ""})
    return {
        "ok": True,
        "updated": updated,
        "skipped": skipped,
        "inserted": inserted,
        "type": "volume_profile",
    }


# ── POST /api/v9/bars/imbalance ──

@router.post("/imbalance")
def post_imbalance(
    payload: ImbalancePayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    """Store imbalance flags as system signals (existing path) + INSERT into
    dedicated ``v9_bars_imbalance`` (new — P31 Phase 1, Michael 2026-05-22
    ``populate`` choice for the 4 dedicated tables).
    """
    from backend.v9.db.models import V9SystemSignal
    from sqlalchemy import text as _sql_text

    created = 0
    inserted = 0
    for bar in payload.bars:
        ts_iso = _ts_from_unix(bar.get("ts")).isoformat()
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

        bar_idx = bar.get("bar_idx")
        if bar_idx is not None:
            stacked_buy = bar.get("stacked_buy") or 0
            stacked_sell = bar.get("stacked_sell") or 0
            direction = "BUY" if stacked_buy > stacked_sell else ("SELL" if stacked_sell > stacked_buy else None)
            try:
                db.execute(
                    _sql_text(
                        "INSERT OR REPLACE INTO v9_bars_imbalance "
                        "(ts, bar_id, price, ratio, direction, bid_vol, ask_vol, session, created_at) "
                        "VALUES (:ts, :bar_id, :price, :ratio, :direction, :bid_vol, :ask_vol, :session, CURRENT_TIMESTAMP)"
                    ),
                    {
                        "ts": ts_iso,
                        "bar_id": f"imb_{bar_idx}",
                        "price": bar.get("price"),
                        "ratio": None,  # Sierra doesn't emit a single ratio; derive in analytics if needed
                        "direction": direction,
                        "bid_vol": int(stacked_sell) if stacked_sell else None,
                        "ask_vol": int(stacked_buy) if stacked_buy else None,
                        "session": None,
                    },
                )
                inserted += 1
            except Exception as e:
                logger.warning("[IMB] dedicated INSERT failed bar_idx=%s: %s", bar_idx, e)
    db.commit()
    _record_push("imbalance_flags")
    _route_bar("imbalance", payload.dict() if hasattr(payload, "dict") else {"ts": ""})
    return {
        "ok": True,
        "inserted": created,
        "dedicated_inserted": inserted,
        "type": "imbalance",
        "total_buy": payload.total_buy_imbalances,
        "total_sell": payload.total_sell_imbalances,
    }


# ── POST /api/v9/bars/stacked_imbalance ──

@router.post("/stacked_imbalance")
def post_stacked_imbalance(
    payload: StackedImbalancePayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    """Persist stacked imbalances to ``v9_system_signals`` (existing path) +
    dedicated ``v9_bars_stacked_imbalance`` (new — Phase 1). The Sierra
    export uses the key ``stacks[]``; keep ``bars[]`` as fallback for
    backward compat.
    """
    from backend.v9.db.models import V9SystemSignal
    from sqlalchemy import text as _sql_text

    stacks = payload.stacks or payload.bars
    created = 0
    inserted = 0
    for stack in stacks:
        ts_iso = _ts_from_unix(stack.get("ts")).isoformat()
        signal = V9SystemSignal(
            ts=_ts_from_unix(stack.get("ts")),
            system_id=3,
            classification="STACKED_IMBALANCE",
            direction=None,
            payload=stack,
        )
        db.add(signal)
        created += 1

        bar_idx = stack.get("bar_idx") or stack.get("idx")
        if bar_idx is not None:
            try:
                db.execute(
                    _sql_text(
                        "INSERT OR REPLACE INTO v9_bars_stacked_imbalance "
                        "(ts, bar_id, count, direction, start_price, end_price, session, created_at) "
                        "VALUES (:ts, :bar_id, :count, :direction, :start_price, :end_price, :session, CURRENT_TIMESTAMP)"
                    ),
                    {
                        "ts": ts_iso,
                        "bar_id": f"simb_{bar_idx}",
                        "count": int(stack.get("count") or stack.get("stack_size") or 0),
                        "direction": stack.get("direction") or stack.get("side"),
                        "start_price": stack.get("start_price") or stack.get("low"),
                        "end_price": stack.get("end_price") or stack.get("high"),
                        "session": None,
                    },
                )
                inserted += 1
            except Exception as e:
                logger.warning("[SImb] dedicated INSERT failed bar_idx=%s: %s", bar_idx, e)
    db.commit()
    _record_push("stacked_imbalances")
    _route_bar("stacked_imbalance", payload.dict() if hasattr(payload, "dict") else {"ts": ""})
    return {
        "ok": True,
        "inserted": created,
        "dedicated_inserted": inserted,
        "type": "stacked_imbalance",
    }


# ── POST /api/v9/bars/cumulative_delta ──

@router.post("/cumulative_delta")
def post_cumulative_delta(
    payload: CumulativeDeltaPayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    """Enrich 5-min bars with running delta (existing UPDATE path) **and**
    persist each point to dedicated ``v9_bars_cumulative_delta``.

    Sierra emits ``points[]`` with shape ``{i, t, d, cum, p}`` (i=index,
    t=unix ts, d=per-bar delta, cum=running total, p=close price). Keep
    ``bars[]`` as fallback for backward compat.
    """
    from datetime import timedelta
    from sqlalchemy import text as _sql_text

    points = payload.points or payload.bars
    updated = 0
    skipped = 0
    inserted = 0

    for pt in points:
        # CVD points carry their own ts in `t` (unix seconds). Use that
        # for ts-windowed enrichment of the matching 5-min bar.
        raw_ts = pt.get("t") or pt.get("ts")
        ts = _ts_from_unix(raw_ts)
        window = timedelta(minutes=5)
        row = (
            db.query(V9Bar5Min)
            .filter(V9Bar5Min.ts >= ts - window, V9Bar5Min.ts <= ts + window)
            .order_by(V9Bar5Min.ts)
            .first()
        )
        if row:
            row.cumulative_delta = pt.get("cum") or pt.get("cumulative_delta") or pt.get("delta") or pt.get("d")
            updated += 1
        else:
            skipped += 1

        idx = pt.get("i") if "i" in pt else pt.get("bar_idx")
        delta = pt.get("d") or pt.get("delta")
        cumulative = pt.get("cum") or pt.get("cumulative_delta")
        price = pt.get("p") or pt.get("price")
        if idx is not None:
            try:
                db.execute(
                    _sql_text(
                        "INSERT OR REPLACE INTO v9_bars_cumulative_delta "
                        "(ts, bar_id, delta, cumulative, direction, session, created_at) "
                        "VALUES (:ts, :bar_id, :delta, :cumulative, :direction, :session, CURRENT_TIMESTAMP)"
                    ),
                    {
                        "ts": ts.isoformat(),
                        "bar_id": f"cvd_{idx}",
                        "delta": delta,
                        "cumulative": cumulative,
                        "direction": "UP" if (delta or 0) > 0 else ("DOWN" if (delta or 0) < 0 else "FLAT"),
                        "session": None,
                    },
                )
                inserted += 1
            except Exception as e:
                logger.warning("[CVD] dedicated INSERT failed idx=%s: %s", idx, e)
        # `price` is recorded inside cumulative tracker only via session log;
        # the dedicated schema doesn't carry it. Skip without erroring.
        _ = price
    db.commit()
    if points:
        _dispatch("cumulative_delta", points[-1])
    _record_push("cumulative_delta")
    _route_bar("cumulative_delta", payload.dict() if hasattr(payload, "dict") else {"ts": ""})
    return {
        "ok": True,
        "updated": updated,
        "skipped": skipped,
        "inserted": inserted,
        "type": "cumulative_delta",
    }


# ── POST /api/v9/bars/woodies ──

@router.post("/woodies")
def post_woodies(
    payload: WoodiesPayload,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    # 30min_woodies: high-frequency ORM writer → corruption source (same as tick_reversal)
    from backend.v9.shared.atr import flag
    if flag("WOODIES_30MIN_DISABLED"):
        if payload.all_bars:
            _dispatch("woodies_30min", payload.all_bars[-1] if isinstance(payload.all_bars[-1], dict) else {})
            _record_push("woodies_30min")
        return {"ok": True, "inserted": 0, "disabled": True}
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
            "zlr_detected": bar.get("zlr_detected", False),
            "zlr_direction": bar.get("zlr_direction", "NONE"),
            "hfe_detected": bar.get("hfe_detected", False),
            "hfe_direction": bar.get("hfe_direction", "NONE"),
            "hfe_extreme_bars_ago": bar.get("hfe_extreme_bars_ago", 0),
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
    payload: Woodies5MinPayload,
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

    # Frozen-tail fix: when current_bar exists AND history is present,
    # override history[-1] study fields with current_bar's live Sierra values.
    # history[-1] may have frozen values from DLL mapIdx clamp (cross-chart
    # mapping boundary), while current_bar reads directly via arr[idx].
    _study_keys = ("cci_14", "cci_6_tcci", "ema_34", "lsma_value", "swi_value",
                   "czi_value", "trend_state", "predictor_next_cci")
    if payload.current_bar and payload.history and len(bars) == len(payload.history):
        cb = payload.current_bar
        last = bars[-1]
        for k in _study_keys:
            if cb.get(k) is not None:
                last[k] = cb[k]

    created = 0
    last_flat = None
    _prev_studies = None  # stale detection
    for bar in bars:
        ohlc = bar.get("ohlc", {})
        o = ohlc.get("o", bar.get("o", bar.get("open", 0)))
        h = ohlc.get("h", bar.get("h", bar.get("high", 0)))
        l = ohlc.get("l", bar.get("l", bar.get("low", 0)))
        c = ohlc.get("c", bar.get("c", bar.get("close", 0)))
        vol = ohlc.get("vol", bar.get("vol", bar.get("volume", 0)))
        # Stale detection: if all 6 study fields are identical to the previous
        # bar, this is likely a frozen-tail artifact from DLL mapIdx clamp.
        # Skip the DB write to avoid polluting the table with frozen duplicates.
        _cur_studies = (bar.get("cci_14"), bar.get("swi_value"), bar.get("czi_value"),
                        bar.get("ema_34"), bar.get("lsma_value"), bar.get("cci_6_tcci"))
        if _prev_studies is not None and _cur_studies == _prev_studies:
            logger.debug("[woodies_5min] Skipping stale bar ts=%s (frozen studies)", bar.get("ts"))
            continue
        _prev_studies = _cur_studies

        # Persist to v9_bars_5min_woodies (dedicated table per D-074)
        import sqlite3 as _sql
        try:
            conn = _sql.connect("/Users/michael/Downloads/mems26_web_git/data/mems26_local.db")
            conn.execute(
                """INSERT OR REPLACE INTO v9_bars_5min_woodies
                (ts, symbol, open, high, low, close, volume, cci_14, cci_6_tcci,
                 lsma_value, swi_value, czi_value, ema_34, trend_state,
                 predictor_next_cci, zlr_detected, zlr_direction,
                 proj_hi, proj_lo, hfe_detected, hfe_direction, hfe_extreme_bars_ago,
                 lsma_above_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    bar.get("ts", ""), "MES", o, h, l, c, vol,
                    bar.get("cci_14"), bar.get("cci_6_tcci"),
                    bar.get("lsma_value"), bar.get("swi_value"),
                    bar.get("czi_value"), bar.get("ema_34"),
                    bar.get("trend_state"), bar.get("predictor_next_cci"),
                    bar.get("zlr_detected", False), bar.get("zlr_direction"),
                    bar.get("proj_hi"), bar.get("proj_lo"),
                    1 if bar.get("hfe_detected") else 0,
                    bar.get("hfe_direction") or "NONE",
                    int(bar.get("hfe_extreme_bars_ago") or 0),
                    1 if bar.get("lsma_above_price") else 0,
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
            "zlr_detected": bar.get("zlr_detected", False),
            "zlr_direction": bar.get("zlr_direction", "NONE"),
            "hfe_detected": bar.get("hfe_detected", False),
            "hfe_direction": bar.get("hfe_direction", "NONE"),
            "hfe_extreme_bars_ago": bar.get("hfe_extreme_bars_ago", 0),
        }
    _record_push("woodies_5min")

    # === BEGIN current_bar routing override (Cursor audit §6 rank-2 fix) ===
    # `history[-1]` is FROZEN for the last ~13 bars per the DLL
    # `GetContainingIndexForDateTimeIndex` clamp (see
    # AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28 §3). `current_bar` carries LIVE
    # Sierra study values via direct `arr[idx]` read in MES_AI_DataExport.cpp.
    # Prefer it for routing to S4 so calculate_size() sees live SWI/TCCI.
    if payload.current_bar:
        _cb = payload.current_bar
        _cb_ohlc = _cb.get("ohlc", {}) or {}
        last_flat = {
            "ts": _cb.get("ts"),
            "open":   _cb_ohlc.get("o",   _cb.get("o",   _cb.get("open",   0))),
            "high":   _cb_ohlc.get("h",   _cb.get("h",   _cb.get("high",   0))),
            "low":    _cb_ohlc.get("l",   _cb.get("l",   _cb.get("low",    0))),
            "close":  _cb_ohlc.get("c",   _cb.get("c",   _cb.get("close",  0))),
            "volume": _cb_ohlc.get("vol", _cb.get("vol", _cb.get("volume", 0))),
            "cci_14":             _cb.get("cci_14"),
            "cci_6_tcci":         _cb.get("cci_6_tcci"),
            "ema_34":             _cb.get("ema_34"),
            "lsma_value":         _cb.get("lsma_value"),
            "swi_value":          _cb.get("swi_value"),
            "czi_value":          _cb.get("czi_value"),
            "trend_state":        _cb.get("trend_state"),
            "predictor_next_cci": _cb.get("predictor_next_cci"),
            "zlr_detected":       _cb.get("zlr_detected", False),
            "zlr_direction":      _cb.get("zlr_direction", "NONE"),
            "hfe_detected":       _cb.get("hfe_detected", False),
            "hfe_direction":      _cb.get("hfe_direction", "NONE"),
            "hfe_extreme_bars_ago": _cb.get("hfe_extreme_bars_ago", 0),
        }
    # === END override ===

    if last_flat:
        _route_bar("woodies_5min", last_flat)
    return {"ok": True, "inserted": created, "type": "woodies_5min"}


# ── POST /api/v9/bars/5min_continuous (chart #5 24h) ──

@router.post("/5min_continuous")
def post_5min_continuous(
    payload: dict = Body(...),
    _token: str = Depends(verify_bridge_token),
):
    """Ingest continuous 24h 5-min bars from chart #5.

    Stores in v9_bars_5min (same table as RTH bars) — the chart endpoint
    merges both sources. INSERT OR IGNORE deduplicates by (ts, symbol).
    """
    bars = payload.get("bars", [])
    if not bars:
        return {"ok": True, "inserted": 0, "type": "5min_continuous"}
    _record_push("bars_5min_continuous")

    from backend.v9.services.bar_ingestion import bar_ingestion_service
    from datetime import datetime as _dt, timezone as _tz
    created = 0
    for bar in bars:
        # Convert unix ts to ISO datetime string (matching v9_bars_5min format)
        raw_ts = bar.get("ts")
        try:
            ts_val = _dt.fromtimestamp(float(raw_ts), tz=_tz.utc) if raw_ts else _dt.now(_tz.utc)
        except (TypeError, ValueError):
            ts_val = _dt.now(_tz.utc)
        ok = bar_ingestion_service.ingest_bar({
            "ts": ts_val,
            "open": bar.get("o"),
            "high": bar.get("h"),
            "low": bar.get("l"),
            "close": bar.get("c"),
            "volume": bar.get("vol"),
            "delta": bar.get("delta", 0),
            "symbol": "MES",
        })
        if ok:
            created += 1
    return {"ok": True, "inserted": created, "type": "5min_continuous"}


# ── POST /api/v9/bars/cvd_continuous (chart #5 24h) ──

@router.post("/cvd_continuous")
def post_cvd_continuous(
    payload: dict = Body(...),
    _token: str = Depends(verify_bridge_token),
):
    """Ingest continuous 24h CVD from chart #5. Stored in v9_bars_cumulative_delta."""
    _record_push("cvd_continuous")
    return {"ok": True, "type": "cvd_continuous"}


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
