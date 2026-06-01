"""GET /api/v9/chart/bars* — multi-timeframe bars for chart rendering.

Supports 1m/3m/5min/15m/30m/1h with cursor-based pagination (Wave A1.5).
"""
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Query
import sqlite3

from backend.v9.services.bar_integrity import bar_is_valid

logger = logging.getLogger("mems26.bars_5min_history")

router = APIRouter(tags=["v9-bars-history"])

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"


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
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        # Primary: v9_bars_5min
        if before:
            rows_5m = conn.execute(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min WHERE ts < ? ORDER BY ts DESC LIMIT ?",
                (before, fetch_limit),
            ).fetchall()
        else:
            rows_5m = conn.execute(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min ORDER BY ts DESC LIMIT ?",
                (fetch_limit,),
            ).fetchall()

        # Fallback: v9_bars_5min_woodies (better overnight coverage)
        if before:
            rows_w = conn.execute(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min_woodies WHERE ts < ? ORDER BY ts DESC LIMIT ?",
                (before, fetch_limit),
            ).fetchall()
        else:
            rows_w = conn.execute(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT ?",
                (fetch_limit,),
            ).fetchall()
        conn.close()

        # Merge: index primary by ts, fill gaps from woodies
        by_ts = {}
        for r in rows_5m:
            by_ts[r["ts"]] = dict(r)
        for r in rows_w:
            ts = r["ts"]
            if ts not in by_ts:
                by_ts[ts] = dict(r)

        # Sort oldest first, validate, filter flat stale bars
        result = []
        filtered = 0
        for ts in sorted(by_ts.keys()):
            r = by_ts[ts]
            o, h, l, c = r["open"], r["high"], r["low"], r["close"]
            ok, reason = bar_is_valid(open=o, high=h, low=l, close=c)
            if not ok:
                filtered += 1
                continue
            # Filter flat stale bars: O=H=L=C with unreasonably high volume
            if o == h == l == c and (r.get("volume") or 0) > 10000:
                filtered += 1
                continue
            result.append({
                "ts": ts,
                "o": o, "h": h, "l": l, "c": c, "v": r.get("volume") or 0,
                "open": o, "high": h, "low": l, "close": c, "volume": r.get("volume") or 0,
            })
        if filtered:
            logger.info("[bars_5min_history] filtered %d bad/stale bars from response", filtered)
        return result[-limit:]
    except Exception:
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
