"""GET /api/v9/woodies/chart — Sierra woodies_5min.json for Cockpit CCI panel (P30.10)."""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

router = APIRouter(tags=["woodies-chart"])
logger = logging.getLogger(__name__)

EXPORT_PATH = Path(
    os.getenv(
        "V9_WOODIES_5MIN_EXPORT_PATH",
        "/Users/michael/SierraChart_Data/v9_export/woodies_5min.json",
    )
)
MAX_AGE_S = float(os.getenv("V9_WOODIES_5MIN_MAX_AGE_S", "30"))

TREND_COLORS = {
    "BLUE": "#1E54E8",
    "RED": "#E03030",
    "YELLOW": "#DDDD20",
    "GRAY": "#888888",
}


def _normalize_bar(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    ts = raw.get("ts")
    if ts is None:
        return None
    try:
        ts_unix = int(float(ts))
    except (TypeError, ValueError):
        return None
    ohlc = raw.get("ohlc") or {}
    cci_14 = raw.get("cci_14")
    if cci_14 is None:
        return None
    def _f(key: str) -> Optional[float]:
        v = raw.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return {
        "ts_unix": ts_unix,
        "ts": datetime.fromtimestamp(ts_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "cci_14": float(cci_14),
        "cci_14_prev": _f("cci_14_prev"),
        "cci_6_tcci": _f("cci_6_tcci"),
        "trend_state": raw.get("trend_state") or "GRAY",
        "trend_color": TREND_COLORS.get(raw.get("trend_state") or "GRAY", TREND_COLORS["GRAY"]),
        "zlr_detected": bool(raw.get("zlr_detected")),
        "zlr_direction": raw.get("zlr_direction"),
        "hfe_detected": bool(raw.get("hfe_detected")),
        "close": float(ohlc.get("c")) if ohlc.get("c") is not None else None,
        "high": float(ohlc.get("h")) if ohlc.get("h") is not None else None,
        "low": float(ohlc.get("l")) if ohlc.get("l") is not None else None,
        "lsma_value": _f("lsma_value"),
        "predictor_next_cci": _f("predictor_next_cci"),
        "swi_value": _f("swi_value"),
    }


def _load_sierra_woodies(export_path: Path, max_age_s: float) -> Optional[Dict[str, Any]]:
    if not export_path.exists():
        logger.warning("[Woodies chart] %s not found", export_path)
        return None
    try:
        age_s = time.time() - export_path.stat().st_mtime
        if age_s > max_age_s:
            logger.warning(
                "[Woodies chart] stale export age=%.1fs > %.1fs", age_s, max_age_s
            )
            return {
                "source": "sierra_woodies_5min_json",
                "stale": True,
                "age_s": round(age_s, 1),
                "error": f"File stale ({age_s:.0f}s > {max_age_s:.0f}s)",
                "bars": [],
            }
        with open(export_path, "r") as f:
            data = json.load(f)
        history = data.get("history") or data.get("bars") or []
        current = data.get("current_bar")
        normalized: List[Dict[str, Any]] = []
        for raw in history:
            bar = _normalize_bar(raw)
            if bar:
                normalized.append(bar)
        if current:
            cur = _normalize_bar(current)
            if cur and (not normalized or normalized[-1]["ts_unix"] != cur["ts_unix"]):
                normalized.append(cur)
        return {
            "source": "sierra_woodies_5min_json",
            "version": data.get("version"),
            "export_ts": data.get("export_ts"),
            "age_s": round(age_s, 1),
            "stale": False,
            "bars": normalized,
            "current_bar": _normalize_bar(current) if current else (normalized[-1] if normalized else None),
        }
    except json.JSONDecodeError:
        logger.warning("[Woodies chart] JSON parse error")
        return None
    except Exception as e:
        logger.warning("[Woodies chart] read error: %s", e)
        return None


@router.get("/api/v9/woodies/chart")
async def woodies_chart(limit: int = Query(30, ge=1, le=120)):
    """Return last N Woodies 5m CCI bars from Sierra export for chart panel."""
    payload = _load_sierra_woodies(EXPORT_PATH, MAX_AGE_S)
    if payload is None:
        return {
            "source": "missing",
            "error": "woodies_5min.json not found",
            "bars": [],
            "requested_limit": limit,
        }
    if payload.get("error") and not payload.get("bars"):
        payload["requested_limit"] = limit
        return payload

    bars = payload.get("bars") or []
    tail = bars[-limit:] if len(bars) > limit else bars
    out = {**payload, "bars": tail, "requested_limit": limit, "cardinality": len(tail)}
    if tail:
        out["latest_ts_unix"] = tail[-1]["ts_unix"]
    return out
