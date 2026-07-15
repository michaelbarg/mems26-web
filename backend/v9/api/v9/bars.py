"""V9 API: Bar data endpoints — receives Bridge pushes for all bar types.

DB Root Fix (2026-06-03): ALL writes go through safe_writer (safe_execute /
safe_executemany) — no ORM db.add/db.commit for writes.  ORM get_db() is kept
for READ-ONLY queries only (e.g. enrichment lookups).  This eliminates the
concurrent ORM-vs-raw-sqlite3 write race that caused recurring B-tree corruption.
"""

import json as _json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from fastapi import APIRouter, Body, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from zoneinfo import ZoneInfo

from backend.v9.db.session import get_db
from backend.v9.db.models import V9Bar5Min, V9BarTickReversal, V9BarFootprint, V9Bar30MinWoodies, V9TpoBar
from backend.v9.api.v9.auth import verify_bridge_token
from backend.v9.api.v9.ws_manager import (
    publish_event, CHANNEL_BARS_5MIN, CHANNEL_BARS_TICK_REVERSAL,
    CHANNEL_BARS_WOODIES, CHANNEL_LEVELS,
)
from backend.v9.services.bar_integrity import bar_is_valid
from backend.v9.db.safe_writer import safe_execute, safe_executemany

# ── RTH time-gate (B4 volume fix 2026-06-03) ──
# RTH = 09:30–16:00 America/New_York.  Bars outside this window from the RTH
# chart carry cumulative session volume (up to 1M) and must NOT enter v9_bars_5min.
_ET = ZoneInfo("America/New_York")
_RTH_START_HOUR, _RTH_START_MIN = 9, 30
_RTH_END_HOUR, _RTH_END_MIN = 17, 0  # 17:00 ET = 16:00 CT — includes post-close bars (vol=0)

# ── B-13 staleness guard (2026-06-05) ──
# Reject bars with ts older than MAX_STALE_AGE from now.  Prevents old/residual
# bars (e.g. May-6 PG-migration leftovers) from reaching pattern engines.
# Also rejects bars whose price deviates from the latest known market price by
# more than STALE_PRICE_BAND points — catches corrupt/phantom prices.
# VALUES pending Michael's sign-off; these are conservative defaults.
import os as _os
MAX_STALE_AGE = timedelta(hours=int(_os.environ.get("MAX_STALE_HOURS", "24")))
STALE_PRICE_BAND = float(_os.environ.get("STALE_PRICE_BAND", "50"))  # points

# Module-level latest-price tracker (updated on every valid 5min bar ingest)
_latest_known_price: Optional[float] = None
_latest_bar_ts: Optional[datetime] = None


def _is_within_rth(ts_utc: datetime) -> bool:
    """Check if a UTC timestamp falls within RTH 09:30–16:00 ET."""
    ts_et = ts_utc.astimezone(_ET)
    et_minutes = ts_et.hour * 60 + ts_et.minute
    return (_RTH_START_HOUR * 60 + _RTH_START_MIN) <= et_minutes < (_RTH_END_HOUR * 60 + _RTH_END_MIN)


def _is_stale_bar(ts_utc: datetime, close_price: float) -> Optional[str]:
    """B-13 staleness guard. Returns rejection reason or None if OK.

    Two independent checks (either triggers rejection):
    (a) ts older than now - MAX_STALE_AGE → stale timestamp
    (b) close deviates from latest known price by > STALE_PRICE_BAND → off-market
    """
    global _latest_known_price, _latest_bar_ts
    now = datetime.now(timezone.utc)

    # (a) Staleness: bar timestamp too old
    if ts_utc < now - MAX_STALE_AGE:
        return f"stale_ts (bar {ts_utc.isoformat()} older than {MAX_STALE_AGE})"

    # (b) Price band: deviation from latest known market price
    if _latest_known_price is not None and close_price > 0:
        deviation = abs(close_price - _latest_known_price)
        if deviation > STALE_PRICE_BAND:
            return (
                f"off_market (close={close_price:.2f} vs latest={_latest_known_price:.2f}, "
                f"deviation={deviation:.1f} > band={STALE_PRICE_BAND})"
            )

    return None  # OK

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
    """Route a bar to BarRouter via thread-safe publish (P27.5c fix).

    B-13: staleness guard — ts-age check applies to all bar types.
    Price-band check applies ONLY to the 5min stream that owns the
    _latest_known_price tracker. Other streams (woodies_5min, tpo,
    footprint, etc.) legitimately carry different prices from different
    chart periods and must NOT be compared to the 5min spot price.
    """
    if _bar_router is None:
        # 07-15 Q1 hardening (no-silent-failures): this return starved the
        # engines invisibly — DB kept filling while dispatch was dead. Never
        # silent again (rate-limited: once per minute).
        global _no_router_warn_ts
        try:
            import time as _nr_time
            _now = _nr_time.time()
            if _now - globals().get("_no_router_warn_ts", 0) > 60:
                globals()["_no_router_warn_ts"] = _now
                logger.warning(
                    "[bars/%s] _route_bar: BarRouter NOT WIRED — bar ingested to DB "
                    "but NOT dispatched to engines (S1/S2/S4 starving!)", bar_type)
        except Exception:
            pass
        return
    # B-13: guard routing for bar types that carry OHLC (not aggregate payloads)
    raw_ts = bar_data.get("ts")
    close = bar_data.get("close") or bar_data.get("c")
    if raw_ts is not None and close is not None:
        try:
            if isinstance(raw_ts, datetime):
                ts = raw_ts
            elif isinstance(raw_ts, str):
                try:
                    ts = datetime.fromisoformat(raw_ts)
                except ValueError:
                    ts = _ts_from_unix(raw_ts)
            else:
                ts = _ts_from_unix(raw_ts)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            # Ts-age check: all bar types
            now = datetime.now(timezone.utc)
            if ts < now - MAX_STALE_AGE:
                logger.warning("[bars/%s] _route_bar BLOCKED stale bar: stale_ts (bar %s older than %s)",
                               bar_type, ts.isoformat(), MAX_STALE_AGE)
                return
            # Price-band check: ONLY for 5min (the stream that owns _latest_known_price)
            if bar_type == "5min" and _latest_known_price is not None and float(close) > 0:
                deviation = abs(float(close) - _latest_known_price)
                if deviation > STALE_PRICE_BAND:
                    logger.warning("[bars/%s] _route_bar BLOCKED stale bar: off_market "
                                   "(close=%.2f vs latest=%.2f, deviation=%.1f > band=%.1f)",
                                   bar_type, float(close), _latest_known_price, deviation, STALE_PRICE_BAND)
                    return
        except (TypeError, ValueError, OSError):
            pass  # unparseable ts/close — let BarRouter handle
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
    _token: str = Depends(verify_bridge_token),
):
    """Upsert 5-min OHLC bars by (ts, symbol) via safe_writer.

    DB Root Fix (2026-06-03): all writes through safe_execute INSERT OR REPLACE.
    No ORM db.add/db.commit — eliminates concurrent write race that caused
    B-tree corruption.  The UNIQUE(ts, symbol) constraint handles dedup.
    """
    inserted = 0
    rejected = 0
    last_valid_bar = None

    def _flat_5min_for_router(bar: Bar5MinIn, ts) -> dict:
        """Flat keys for FiveMinSystem + BarLevelDetector (P31-02)."""
        return {
            "ts": str(ts),
            "o": bar.o, "h": bar.h, "l": bar.l, "c": bar.c, "vol": bar.vol,
            "open": bar.o, "high": bar.h, "low": bar.l, "close": bar.c,
            "volume": bar.vol,
        }

    rows_to_write = []
    rth_skipped = 0
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
        if ts > datetime.now(timezone.utc) + timedelta(minutes=2):
            logger.warning("[bars/5min] Rejected FUTURE bar ts=%s (now+2m guard)", ts)
            rejected += 1
            continue
        # B4 fix: RTH time-gate — only write bars within 09:30–16:00 ET.
        # Outside RTH, Sierra's RTH chart exports cumulative session volume
        # (up to 1M) which corrupts rolling_avg and VSA pattern detection.
        if not _is_within_rth(ts):
            rth_skipped += 1
            continue
        # B4 volume guard: reject cumulative session volumes (>100K for 5min MES)
        if bar.vol > 100_000:
            logger.debug("[bars/5min] Rejected cumulative vol=%d at ts=%s", bar.vol, ts)
            rejected += 1
            continue
        # B-13 write-guard: reject off-market price on FRESH bars (ts within stale window).
        # Old valid bars (historical chart data) pass through — only fresh bars are checked
        # so we don't corrupt pattern engines with phantom prices.
        if ts > datetime.now(timezone.utc) - MAX_STALE_AGE:
            stale_reason = _is_stale_bar(ts, float(bar.c))
            if stale_reason:
                logger.warning("[bars/5min] write-guard BLOCKED: %s ts=%s", stale_reason, ts)
                rejected += 1
                continue
        rows_to_write.append((
            ts.isoformat(), bar.symbol, bar.o, bar.h, bar.l, bar.c,
            bar.vol, bar.poc_vol, bar.vah, bar.val, bar.cumulative_delta,
        ))
        last_valid_bar = bar

    if rows_to_write:
        inserted = safe_executemany(
            "INSERT OR REPLACE INTO v9_bars_5min "
            "(ts, symbol, open, high, low, close, volume, poc_vol, vah, val, cumulative_delta) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows_to_write,
        )

    publish_event(CHANNEL_BARS_5MIN, {
        "count": inserted,
        "rejected": rejected,
        "last": {"o": last_valid_bar.o, "h": last_valid_bar.h, "l": last_valid_bar.l,
                 "c": last_valid_bar.c, "vol": last_valid_bar.vol} if last_valid_bar else {},
    })
    _record_push("5min")
    # B-13: update latest-price tracker for staleness guard
    if last_valid_bar is not None:
        global _latest_known_price, _latest_bar_ts
        _latest_known_price = last_valid_bar.c
        _latest_bar_ts = _ts_from_unix(last_valid_bar.ts)
        _route_bar("5min", _flat_5min_for_router(last_valid_bar, _ts_from_unix(last_valid_bar.ts)))
    if rth_skipped:
        logger.info("[bars/5min] RTH time-gate skipped %d bars outside 09:30-16:00 ET", rth_skipped)
    return {"ok": True, "inserted": inserted, "rejected": rejected, "rth_skipped": rth_skipped}


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
    per-price-level profile to ``v9_bars_volume_profile`` for backtest replay.

    DB Root Fix (2026-06-03): enrichment UPDATEs and dedicated-table INSERTs
    go through safe_execute.  ORM db.query kept for READ-ONLY positional match.
    """
    profiles = payload.profiles or payload.bars
    updated = 0
    skipped = 0
    inserted = 0

    if profiles:
        # READ-ONLY: positional match via ORM (no writes through ORM).
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
                new_poc = prof.get("poc_vol", row.poc_vol)
                new_vah = prof.get("vah", row.vah)
                new_val = prof.get("val", row.val)
                safe_execute(
                    "UPDATE v9_bars_5min SET poc_vol=?, vah=?, val=? WHERE id=?",
                    (new_poc, new_vah, new_val, row.id),
                )
                updated += 1
            else:
                skipped += 1

        # Dedicated table — persist FULL profile JSON for backtests.
        for prof in profiles:
            bar_idx = prof.get("bar_idx")
            if bar_idx is None:
                continue
            result = safe_execute(
                "INSERT OR REPLACE INTO v9_bars_volume_profile "
                "(ts, bar_id, profile, poc, vah, val, total_volume, session, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (
                    _ts_from_unix(payload.export_ts).isoformat(),
                    f"vp_{bar_idx}",
                    _json.dumps(prof.get("levels") or []),
                    prof.get("poc"),
                    prof.get("vah"),
                    prof.get("val"),
                    int(prof.get("total_vol") or 0),
                    None,
                ),
            )
            if result is not None:
                inserted += 1
            else:
                logger.warning("[VP] dedicated INSERT failed bar_idx=%s", bar_idx)

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
    _token: str = Depends(verify_bridge_token),
):
    """Store imbalance flags as system signals + dedicated v9_bars_imbalance.

    DB Root Fix (2026-06-03): all writes through safe_execute.
    """
    created = 0
    inserted = 0
    for bar in payload.bars:
        ts_iso = _ts_from_unix(bar.get("ts")).isoformat()
        signal_payload = _json.dumps({
            "bar_idx": bar.get("bar_idx"),
            "price": bar.get("price"),
            "stacked_buy": bar.get("stacked_buy"),
            "stacked_sell": bar.get("stacked_sell"),
            "levels": bar.get("levels", []),
        })
        result = safe_execute(
            "INSERT INTO v9_system_signals (ts, system_id, classification, direction, payload) "
            "VALUES (?, ?, ?, ?, ?)",
            (ts_iso, 3, "IMBALANCE", None, signal_payload),
        )
        if result is not None:
            created += 1

        bar_idx = bar.get("bar_idx")
        if bar_idx is not None:
            stacked_buy = bar.get("stacked_buy") or 0
            stacked_sell = bar.get("stacked_sell") or 0
            direction = "BUY" if stacked_buy > stacked_sell else ("SELL" if stacked_sell > stacked_buy else None)
            result = safe_execute(
                "INSERT OR REPLACE INTO v9_bars_imbalance "
                "(ts, bar_id, price, ratio, direction, bid_vol, ask_vol, session, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (
                    ts_iso, f"imb_{bar_idx}", bar.get("price"), None,
                    direction,
                    int(stacked_sell) if stacked_sell else None,
                    int(stacked_buy) if stacked_buy else None,
                    None,
                ),
            )
            if result is not None:
                inserted += 1
            else:
                logger.warning("[IMB] dedicated INSERT failed bar_idx=%s", bar_idx)
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
    _token: str = Depends(verify_bridge_token),
):
    """Persist stacked imbalances to v9_system_signals + dedicated table.

    DB Root Fix (2026-06-03): all writes through safe_execute.
    """
    stacks = payload.stacks or payload.bars
    created = 0
    inserted = 0
    for stack in stacks:
        ts_iso = _ts_from_unix(stack.get("ts")).isoformat()
        result = safe_execute(
            "INSERT INTO v9_system_signals (ts, system_id, classification, direction, payload) "
            "VALUES (?, ?, ?, ?, ?)",
            (ts_iso, 3, "STACKED_IMBALANCE", None, _json.dumps(stack)),
        )
        if result is not None:
            created += 1

        bar_idx = stack.get("bar_idx") or stack.get("idx")
        if bar_idx is not None:
            result = safe_execute(
                "INSERT OR REPLACE INTO v9_bars_stacked_imbalance "
                "(ts, bar_id, count, direction, start_price, end_price, session, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (
                    ts_iso, f"simb_{bar_idx}",
                    int(stack.get("count") or stack.get("stack_size") or 0),
                    stack.get("direction") or stack.get("side"),
                    stack.get("start_price") or stack.get("low"),
                    stack.get("end_price") or stack.get("high"),
                    None,
                ),
            )
            if result is not None:
                inserted += 1
            else:
                logger.warning("[SImb] dedicated INSERT failed bar_idx=%s", bar_idx)
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
    """Enrich 5-min bars with running delta + persist to dedicated table.

    B4 fix (2026-06-03): RTH time-gate — only process CVD points within
    09:30–16:00 ET, aligned with 5-min bars. Prevents settlement cumulative
    artifacts from leaking into CVD.
    """
    points = payload.points or payload.bars
    updated = 0
    skipped = 0
    inserted = 0
    rth_skipped = 0

    for pt in points:
        raw_ts = pt.get("t") or pt.get("ts")
        ts = _ts_from_unix(raw_ts)
        # B4: RTH time-gate for CVD (aligned with 5-min bars)
        if not _is_within_rth(ts):
            rth_skipped += 1
            continue
        window = timedelta(minutes=5)
        # READ-ONLY: find matching 5-min bar for enrichment
        row = (
            db.query(V9Bar5Min)
            .filter(V9Bar5Min.ts >= ts - window, V9Bar5Min.ts <= ts + window)
            .order_by(V9Bar5Min.ts)
            .first()
        )
        cum_value = pt.get("cum") or pt.get("cumulative_delta") or pt.get("delta") or pt.get("d")
        if row:
            safe_execute(
                "UPDATE v9_bars_5min SET cumulative_delta=? WHERE id=?",
                (cum_value, row.id),
            )
            updated += 1
        else:
            skipped += 1

        idx = pt.get("i") if "i" in pt else pt.get("bar_idx")
        delta = pt.get("d") or pt.get("delta")
        cumulative = pt.get("cum") or pt.get("cumulative_delta")
        if idx is not None:
            result = safe_execute(
                "INSERT OR REPLACE INTO v9_bars_cumulative_delta "
                "(ts, bar_id, delta, cumulative, direction, session, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (
                    ts.isoformat(), f"cvd_{idx}", delta, cumulative,
                    "UP" if (delta or 0) > 0 else ("DOWN" if (delta or 0) < 0 else "FLAT"),
                    None,
                ),
            )
            if result is not None:
                inserted += 1
            else:
                logger.warning("[CVD] dedicated INSERT failed idx=%s", idx)
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
    _token: str = Depends(verify_bridge_token),
):
    """DB Root Fix (2026-06-03): all writes through safe_executemany."""
    from backend.v9.shared.atr import flag
    if flag("WOODIES_30MIN_DISABLED"):
        if payload.all_bars:
            _dispatch("woodies_30min", payload.all_bars[-1] if isinstance(payload.all_bars[-1], dict) else {})
            _record_push("woodies_30min")
        return {"ok": True, "inserted": 0, "disabled": True}
    bars = payload.all_bars
    rows_to_write = []
    last_flat = None
    for bar in bars:
        ohlc = bar.get("ohlc", {})
        o = ohlc.get("o", bar.get("o", 0))
        h = ohlc.get("h", bar.get("h", 0))
        l = ohlc.get("l", bar.get("l", 0))
        c = ohlc.get("c", bar.get("c", 0))
        vol = ohlc.get("vol", bar.get("vol", 0))
        rows_to_write.append((
            _ts_from_unix(bar.get("ts")).isoformat(), "MES",
            o, h, l, c, vol,
            bar.get("cci_14"), bar.get("cci_6_tcci"),
            bar.get("lsma_value"), bar.get("swi_value"),
            bar.get("czi_value"), bar.get("ema_34"),
            bar.get("trend_state"), bar.get("predictor_next_cci"),
            1 if bar.get("zlr_detected") else 0,
            bar.get("zlr_direction"),
        ))
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
    created = 0
    if rows_to_write:
        created = safe_executemany(
            "INSERT INTO v9_bars_30min_woodies "
            "(ts, symbol, open, high, low, close, volume, "
            "cci_14, cci_6_tcci, lsma_value, swi_value, czi_value, ema_34, "
            "trend_state, predictor_next_cci, zlr_detected, zlr_direction) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows_to_write,
        )
    publish_event(CHANNEL_BARS_WOODIES, {"count": created})
    if bars:
        _dispatch("woodies_30min", bars[-1])
    _record_push("woodies_30min")
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
        # DB Root Fix (2026-06-03): safe_execute replaces raw sqlite3.connect
        result = safe_execute(
            "INSERT OR REPLACE INTO v9_bars_5min_woodies "
            "(ts, symbol, open, high, low, close, volume, cci_14, cci_6_tcci, "
            "lsma_value, swi_value, czi_value, ema_34, trend_state, "
            "predictor_next_cci, zlr_detected, zlr_direction, "
            "proj_hi, proj_lo, hfe_detected, hfe_direction, hfe_extreme_bars_ago, "
            "lsma_above_price) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _ts_from_unix(bar.get("ts", 0)).isoformat() if isinstance(bar.get("ts"), (int, float)) else bar.get("ts", ""),
                "MES", o, h, l, c, vol,
                bar.get("cci_14"), bar.get("cci_6_tcci"),
                bar.get("lsma_value"), bar.get("swi_value"),
                bar.get("czi_value"), bar.get("ema_34"),
                bar.get("trend_state"), bar.get("predictor_next_cci"),
                1 if bar.get("zlr_detected") else 0, bar.get("zlr_direction"),
                bar.get("proj_hi"), bar.get("proj_lo"),
                1 if bar.get("hfe_detected") else 0,
                bar.get("hfe_direction") or "NONE",
                int(bar.get("hfe_extreme_bars_ago") or 0),
                1 if bar.get("lsma_above_price") else 0,
            ),
        )
        if result is not None:
            created += 1
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

    # ZLR-TRACE (2026-06-30 Cowork): does the routed bar keep the DLL zlr flag?
    # The current_bar override above may drop zlr_detected, which is finalized on
    # the CLOSED bar (history[-1]). Rare trigger (only on a zlr bar).
    try:
        _hist_zlr = bool(bars[-1].get("zlr_detected")) if bars else False
        _cb_zlr = (bool(payload.current_bar.get("zlr_detected"))
                   if payload.current_bar else None)
        _routed_zlr = bool(last_flat.get("zlr_detected")) if last_flat else None
        if _hist_zlr or _routed_zlr:
            logger.info(
                "[woodies_5min ZLR-TRACE] closed_bar.zlr=%s current_bar.zlr=%s "
                "routed.zlr=%s (src=%s) -- closed=True+routed=False => override drops flag",
                _hist_zlr, _cb_zlr, _routed_zlr,
                "current_bar" if payload.current_bar else "history[-1]",
            )
    except Exception:
        pass

    if last_flat:
        _route_bar("woodies_5min", last_flat)
    return {"ok": True, "inserted": created, "type": "woodies_5min"}


# ── POST /api/v9/bars/5min_continuous (chart #5 24h) ──

@router.post("/5min_continuous")
def post_5min_continuous(
    payload: dict = Body(...),
    _token: str = Depends(verify_bridge_token),
):
    """Continuous 24h 5-min bars from chart #5 → v9_bars_5min_continuous.

    Writes to a DEDICATED table (not v9_bars_5min) to avoid contaminating
    the RTH-only table that S2/VSA depends on. Re-enabled 2026-06-04 after
    PG migration made concurrent writes safe (MVCC).
    """
    _record_push("bars_5min_continuous")
    bars = payload.get("bars") if isinstance(payload, dict) else payload
    if not isinstance(bars, list):
        return {"ok": True, "inserted": 0, "type": "5min_continuous"}

    inserted = 0
    rejected = 0
    for bar in bars:
        if not isinstance(bar, dict):
            continue
        ts = _ts_from_unix(bar.get("ts"))
        if ts > datetime.now(timezone.utc) + timedelta(minutes=2):
            rejected += 1
            continue
        try:
            o = float(bar.get("o", bar.get("open", 0)))
            h = float(bar.get("h", bar.get("high", 0)))
            l = float(bar.get("l", bar.get("low", 0)))
            c = float(bar.get("c", bar.get("close", 0)))
            v = int(bar.get("vol", bar.get("volume", 0)))
            delta = bar.get("delta")
        except (TypeError, ValueError):
            rejected += 1
            continue
        ok, reason = bar_is_valid(open=o, high=h, low=l, close=c)
        if not ok:
            rejected += 1
            continue
        result = safe_execute(
            "INSERT OR REPLACE INTO v9_bars_5min_continuous "
            "(ts, symbol, open, high, low, close, volume, delta) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ts.isoformat(), "MES", o, h, l, c, v,
             float(delta) if delta is not None else None),
        )
        if result is not None:
            inserted += 1

    return {"ok": True, "inserted": inserted, "rejected": rejected, "type": "5min_continuous"}


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
    _token: str = Depends(verify_bridge_token),
):
    """DB Root Fix (2026-06-03): all writes through safe_executemany."""
    rows_to_write = []
    for bar in payload.bars:
        rows_to_write.append((
            _ts_from_unix(bar.get("ts")).isoformat(),
            "MES",
            bar.get("letter", "A"),
            bar.get("price", 0),
            bar.get("level", 0),
            bar.get("period_id", 0),
        ))
    created = 0
    if rows_to_write:
        created = safe_executemany(
            "INSERT INTO v9_tpo_bars (ts, symbol, letter, price, level, period_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows_to_write,
        )
    publish_event(CHANNEL_LEVELS, {"count": created, "type": "tpo"})
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
