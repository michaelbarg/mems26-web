"""GET /api/v9/chart/bars* — multi-timeframe bars for chart rendering.

Supports 1m/3m/5min/15m/30m/1h with cursor-based pagination (Wave A1.5).
"""
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Query

from backend.v9.db.read import read_all
from backend.v9.services.bar_integrity import bar_is_valid

logger = logging.getLogger("mems26.bars_5min_history")

router = APIRouter(tags=["v9-bars-history"])


def _fetch_bars_5min(limit: int = 60, before: Optional[str] = None) -> list:
    """Internal: fetch 5-min bars from DB. Used by all timeframe routes.

    Merges two sources for continuity (Option C):
      1. v9_bars_5min (primary — ingested from bridge 5min.json)
      2. v9_bars_5min_woodies (fallback — has overnight/24-6 coverage)

    When v9_bars_5min has gaps (backend downtime, RTH-only export),
    fills from Woodies. Filters flat stale bars (O=H=L=C with high volume).
    """
    fetch_limit = min(max(limit, 1), 600) + 20
    try:
        # Primary: v9_bars_5min_continuous (Sierra chart#5, 24h coverage, no gaps)
        # Falls back to v9_bars_5min (RTH) + woodies if continuous is empty.
        rows_cont = []
        try:
            if before:
                rows_cont = read_all(
                    "SELECT ts, open, high, low, close, volume FROM v9_bars_5min_continuous WHERE ts < :before ORDER BY ts DESC LIMIT :limit",
                    {"before": before, "limit": fetch_limit},
                )
            else:
                rows_cont = read_all(
                    "SELECT ts, open, high, low, close, volume FROM v9_bars_5min_continuous ORDER BY ts DESC LIMIT :limit",
                    {"limit": fetch_limit},
                )
        except Exception as e:
            logger.debug("[bars_5min_history] continuous table not available: %s", e)

        # Fallback sources (used when continuous is empty or for gap-fill)
        if before:
            rows_5m = read_all(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min WHERE ts < :before ORDER BY ts DESC LIMIT :limit",
                {"before": before, "limit": fetch_limit},
            )
        else:
            rows_5m = read_all(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min ORDER BY ts DESC LIMIT :limit",
                {"limit": fetch_limit},
            )

        rows_w = []
        try:
            if before:
                rows_w = read_all(
                    "SELECT ts, open, high, low, close, volume FROM v9_bars_5min_woodies WHERE ts < :before ORDER BY ts DESC LIMIT :limit",
                    {"before": before, "limit": fetch_limit},
                )
            else:
                rows_w = read_all(
                    "SELECT ts, open, high, low, close, volume FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT :limit",
                    {"limit": fetch_limit},
                )
        except Exception as e:
            logger.debug("[bars_5min_history] woodies fallback not available: %s", e)

        # Merge: index primary by epoch (instant), fill gaps from woodies.
        # Using epoch (not str(ts)) avoids format-dependent dedup failures.
        from datetime import datetime, timezone
        def _to_epoch(ts_val) -> int:
            """Convert any ts value to UTC epoch for dedup."""
            if isinstance(ts_val, datetime):
                return int(ts_val.timestamp())
            s = str(ts_val).replace(" ", "T")
            try:
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
            except (ValueError, TypeError):
                return hash(s)  # fallback — unique but won't collide

        by_epoch = {}
        # Priority: continuous (best coverage) > 5min (RTH) > woodies (fallback)
        for r in rows_cont:
            by_epoch[_to_epoch(r["ts"])] = dict(r)
        for r in rows_5m:
            ep = _to_epoch(r["ts"])
            if ep not in by_epoch:
                by_epoch[ep] = dict(r)
        for r in rows_w:
            ep = _to_epoch(r["ts"])
            if ep not in by_epoch:
                rd = dict(r)
                try:
                    float(rd["open"]); float(rd["high"]); float(rd["low"]); float(rd["close"])
                except (TypeError, ValueError):
                    continue
                by_epoch[ep] = rd

        # Sort oldest first, validate, filter flat stale bars
        result = []
        filtered = 0
        for ep in sorted(by_epoch.keys()):
            r = by_epoch[ep]
            o, h, l, c = r["open"], r["high"], r["low"], r["close"]
            ok, reason = bar_is_valid(open=o, high=h, low=l, close=c)
            if not ok:
                filtered += 1
                continue
            if o == h == l == c and (r.get("volume") or 0) > 10000:
                filtered += 1
                continue
            result.append({
                "ts": str(r["ts"]),
                "o": o, "h": h, "l": l, "c": c, "v": r.get("volume") or 0,
                "open": o, "high": h, "low": l, "close": c, "volume": r.get("volume") or 0,
            })
        if filtered:
            logger.info("[bars_5min_history] filtered %d bad/stale bars from response", filtered)

        # Display filter: RTH-only per session (09:30–16:00 ET), matching
        # Sierra chart#5 which shows RTH sessions back-to-back without overnight.
        # Data stays in DB (continuous table has overnight); this is display-only.
        if result:
            try:
                from zoneinfo import ZoneInfo
                et = ZoneInfo("America/New_York")
            except ImportError:
                et = None
            if et:
                # FIX 3B: filter by date AND time. Without date check,
                # Globex bars with tomorrow's date pass the time filter
                # and render as "+" markers past today's candles.
                now_et = datetime.now(tz=et)
                today_et_date = now_et.date()
                # During Globex (after 16:00 ET), show today's RTH only
                # During RTH, show today's bars
                filtered_rth = []
                for bar in result:
                    bar_epoch = _to_epoch(bar["ts"])
                    bar_et = datetime.fromtimestamp(bar_epoch, tz=et)
                    et_min = bar_et.hour * 60 + bar_et.minute
                    if 570 <= et_min < 960 and bar_et.date() <= today_et_date:
                        filtered_rth.append(bar)
                if filtered_rth:
                    result = filtered_rth

        return result[-limit:]
    except Exception as e:
        logger.warning("[bars_5min_history] _fetch_bars_5min failed: %s", e)
        return []


def _aggregate_bars(bars_5m: list, period_minutes: int) -> list:
    """Aggregate 5-min bars into larger timeframes."""
    if not bars_5m or period_minutes <= 5:
        return bars_5m
    factor = period_minutes // 5
    result = []
    for i in range(0, len(bars_5m), factor):
        chunk = bars_5m[i:i + factor]
        if not chunk:
            continue
        agg_h = max(b["h"] for b in chunk)
        agg_l = min(b["l"] for b in chunk)
        agg_o = chunk[0]["o"]
        agg_c = chunk[-1]["c"]
        agg_v = sum(b["v"] for b in chunk)
        result.append({
            "ts": chunk[0]["ts"],
            "o": agg_o, "h": agg_h, "l": agg_l, "c": agg_c, "v": agg_v,
            "open": agg_o, "high": agg_h, "low": agg_l, "close": agg_c, "volume": agg_v,
        })
    return result


# ── Endpoints ──

@router.get("/api/v9/chart/bars5min")
async def get_bars_5min(
    limit: int = Query(60, le=600),
    before: Optional[str] = Query(None, description="ISO timestamp — fetch bars BEFORE this ts"),
):
    """Return 5-min bars, oldest first."""
    return await asyncio.to_thread(_fetch_bars_5min, limit, before)


@router.get("/api/v9/chart/bars1m")
async def get_bars_1m(limit: int = Query(120, le=600), before: Optional[str] = Query(None)):
    """1-min bars — returns 5-min as finest available."""
    return await asyncio.to_thread(_fetch_bars_5min, limit, before)


@router.get("/api/v9/chart/bars3m")
async def get_bars_3m(limit: int = Query(120, le=600), before: Optional[str] = Query(None)):
    """3-min bars — returns 5-min as proxy."""
    return await asyncio.to_thread(_fetch_bars_5min, limit, before)


@router.get("/api/v9/chart/bars15m")
async def get_bars_15m(limit: int = Query(60, le=200), before: Optional[str] = Query(None)):
    """15-min bars aggregated from 5-min."""
    raw = await asyncio.to_thread(_fetch_bars_5min, limit * 3, before)
    return _aggregate_bars(raw, 15)


@router.get("/api/v9/chart/bars30m")
async def get_bars_30m(limit: int = Query(48, le=200), before: Optional[str] = Query(None)):
    """30-min bars aggregated from 5-min."""
    raw = await asyncio.to_thread(_fetch_bars_5min, limit * 6, before)
    return _aggregate_bars(raw, 30)


@router.get("/api/v9/chart/bars1h")
async def get_bars_1h(limit: int = Query(24, le=200), before: Optional[str] = Query(None)):
    """1-hour bars aggregated from 5-min."""
    raw = await asyncio.to_thread(_fetch_bars_5min, limit * 12, before)
    return _aggregate_bars(raw, 60)
