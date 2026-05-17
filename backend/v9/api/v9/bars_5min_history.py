"""GET /api/v9/chart/bars* — multi-timeframe bars for chart rendering.

Supports 1m/3m/5min/15m/30m/1h with cursor-based pagination (Wave A1.5).
"""
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

    Defense-in-depth: filters out any bar that fails bar_is_valid() so
    bad data never reaches the client even if it slipped past ingestion.
    """
    # Over-fetch to account for filtered rows
    fetch_limit = min(max(limit, 1), 600) + 20
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        if before:
            rows = conn.execute(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min WHERE ts < ? ORDER BY ts DESC LIMIT ?",
                (before, fetch_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min ORDER BY ts DESC LIMIT ?",
                (fetch_limit,),
            ).fetchall()
        conn.close()
        result = []
        filtered = 0
        for r in reversed(rows):
            o, h, l, c = r["open"], r["high"], r["low"], r["close"]
            ok, reason = bar_is_valid(open=o, high=h, low=l, close=c)
            if not ok:
                filtered += 1
                logger.debug("[bars_5min_history] filtered bar ts=%s reason=%s", r["ts"], reason)
                continue
            result.append({
                "ts": r["ts"],
                "o": o, "h": h, "l": l, "c": c, "v": r["volume"],
                "open": o, "high": h, "low": l, "close": c, "volume": r["volume"],
            })
        if filtered:
            logger.info("[bars_5min_history] filtered %d bad bars from response", filtered)
        return result[:limit]
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
def get_bars_5min(
    limit: int = Query(60, le=600),
    before: Optional[str] = Query(None, description="ISO timestamp — fetch bars BEFORE this ts"),
):
    """Return 5-min bars, oldest first."""
    return _fetch_bars_5min(limit=limit, before=before)


@router.get("/api/v9/chart/bars1m")
def get_bars_1m(limit: int = Query(120, le=600), before: Optional[str] = Query(None)):
    """1-min bars — returns 5-min as finest available."""
    return _fetch_bars_5min(limit=limit, before=before)


@router.get("/api/v9/chart/bars3m")
def get_bars_3m(limit: int = Query(120, le=600), before: Optional[str] = Query(None)):
    """3-min bars — returns 5-min as proxy."""
    return _fetch_bars_5min(limit=limit, before=before)


@router.get("/api/v9/chart/bars15m")
def get_bars_15m(limit: int = Query(60, le=200), before: Optional[str] = Query(None)):
    """15-min bars aggregated from 5-min."""
    raw = _fetch_bars_5min(limit=limit * 3, before=before)
    return _aggregate_bars(raw, 15)


@router.get("/api/v9/chart/bars30m")
def get_bars_30m(limit: int = Query(48, le=200), before: Optional[str] = Query(None)):
    """30-min bars aggregated from 5-min."""
    raw = _fetch_bars_5min(limit=limit * 6, before=before)
    return _aggregate_bars(raw, 30)


@router.get("/api/v9/chart/bars1h")
def get_bars_1h(limit: int = Query(24, le=200), before: Optional[str] = Query(None)):
    """1-hour bars aggregated from 5-min."""
    raw = _fetch_bars_5min(limit=limit * 12, before=before)
    return _aggregate_bars(raw, 60)
