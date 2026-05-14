"""GET /api/v9/chart/bars5min — 5-min bars for chart rendering.

Supports cursor-based pagination via ?before=<ts> for pan-to-load (Wave A1.5).
"""
from typing import Optional
from fastapi import APIRouter, Query
import sqlite3

router = APIRouter(tags=["v9-bars-history"])

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"


@router.get("/api/v9/chart/bars5min")
def get_bars_5min(
    limit: int = Query(60, le=200),
    before: Optional[str] = Query(None, description="ISO timestamp — fetch bars BEFORE this ts"),
):
    """Return 5-min bars, oldest first.

    Without 'before': latest N bars.
    With 'before': N bars older than the given timestamp (for pan-to-load).
    """
    limit = min(max(limit, 1), 200)
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        if before:
            rows = conn.execute(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min WHERE ts < ? ORDER BY ts DESC LIMIT ?",
                (before, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ts, open, high, low, close, volume FROM v9_bars_5min ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        bars = [{"ts": r["ts"], "o": r["open"], "h": r["high"], "l": r["low"], "c": r["close"], "v": r["volume"]} for r in reversed(rows)]
        return bars
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
        result.append({
            "ts": chunk[0]["ts"],
            "o": chunk[0]["o"],
            "h": max(b["h"] for b in chunk),
            "l": min(b["l"] for b in chunk),
            "c": chunk[-1]["c"],
            "v": sum(b["v"] for b in chunk),
        })
    return result


@router.get("/api/v9/chart/bars3m")
def get_bars_3m(limit: int = Query(120, le=500)):
    """3-min bars — returns 5-min bars as proxy (3-min not stored)."""
    return get_bars_5min(limit=limit)


@router.get("/api/v9/chart/bars15m")
def get_bars_15m(limit: int = Query(60, le=200)):
    """15-min bars aggregated from 5-min."""
    raw = get_bars_5min(limit=min(limit * 3, 600))
    return _aggregate_bars(raw, 15)


@router.get("/api/v9/chart/bars30m")
def get_bars_30m(limit: int = Query(60, le=200)):
    """30-min bars aggregated from 5-min."""
    raw = get_bars_5min(limit=min(limit * 6, 600))
    return _aggregate_bars(raw, 30)


@router.get("/api/v9/chart/bars1h")
def get_bars_1h(limit: int = Query(48, le=200)):
    """1-hour bars aggregated from 5-min."""
    raw = get_bars_5min(limit=min(limit * 12, 600))
    return _aggregate_bars(raw, 60)
