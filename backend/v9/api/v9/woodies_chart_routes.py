"""GET /api/v9/woodies/chart — Sierra woodies_5min.json for Cockpit CCI panel (P30.10)."""

import json
import logging
import math
import os
import time
from datetime import datetime, timezone, timedelta
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
        # DLL TZ bug (§9): timestamps are Sierra-TZ wall-clock encoded as UTC.
        # DST-aware conversion via bridge's _chicago_to_utc (America/New_York).
        from bridge.v9_streams.base_stream import BaseV9Stream
        ts_unix = BaseV9Stream._chicago_to_utc(ts_unix)
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

    prev_ohlc = raw.get("prev_ohlc")
    prev_high = prev_low = prev_open = prev_close = None
    if isinstance(prev_ohlc, dict):
        try:
            prev_open = float(prev_ohlc["o"]) if prev_ohlc.get("o") is not None else None
            prev_high = float(prev_ohlc["h"]) if prev_ohlc.get("h") is not None else None
            prev_low = float(prev_ohlc["l"]) if prev_ohlc.get("l") is not None else None
            prev_close = float(prev_ohlc["c"]) if prev_ohlc.get("c") is not None else None
        except (KeyError, TypeError, ValueError):
            pass

    cci_6 = _f("cci_6_tcci")
    ccidiff = _f("ccidiff")
    if ccidiff is None and cci_6 is not None:
        ccidiff = round(float(cci_14) - cci_6, 2)

    return {
        "ts_unix": ts_unix,
        "ts": datetime.fromtimestamp(ts_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "cci_14": float(cci_14),
        "cci_14_prev": _f("cci_14_prev"),
        "cci_6_tcci": cci_6,
        "ccidiff": ccidiff,
        "ccidiff_h": _f("ccidiff_h"),
        "ccidiff_l": _f("ccidiff_l"),
        "trend_state": raw.get("trend_state") or "GRAY",
        "trend_color": TREND_COLORS.get(raw.get("trend_state") or "GRAY", TREND_COLORS["GRAY"]),
        "zlr_detected": bool(raw.get("zlr_detected")),
        "zlr_direction": raw.get("zlr_direction"),
        "hfe_detected": bool(raw.get("hfe_detected")),
        "close": float(ohlc.get("c")) if ohlc.get("c") is not None else None,
        "high": float(ohlc.get("h")) if ohlc.get("h") is not None else None,
        "low": float(ohlc.get("l")) if ohlc.get("l") is not None else None,
        "lsma_value": _f("lsma_value"),
        "lsma_above_price": bool(raw.get("lsma_above_price")),
        "predictor_next_cci": _f("predictor_next_cci"),
        "predictor_cci_high": _f("predictor_cci_high"),
        "predictor_cci_low": _f("predictor_cci_low"),
        "proj_hi": _f("proj_hi"),
        "proj_lo": _f("proj_lo"),
        "low_prev_angle": _f("low_prev_angle"),
        "swi_value": _f("swi_value"),
        "czi_value": _f("czi_value"),
        "ema_34": _f("ema_34"),
        "cci_14_3ago": _f("cci_14_3ago"),
        "open": float(ohlc.get("o")) if ohlc.get("o") is not None else None,
        "hfe_direction": raw.get("hfe_direction"),
        "prev_high": prev_high,
        "prev_low": prev_low,
        "prev_open": prev_open,
        "prev_close": prev_close,
    }


def _attach_prev_ohlc_from_window(bar: Dict[str, Any], prev_bar: Optional[Dict[str, Any]]) -> None:
    """Fill prev-bar OHLC when export omitted prev_ohlc but history is available."""
    if prev_bar is None or bar.get("prev_high") is not None:
        return
    for key, src in (
        ("prev_high", "high"),
        ("prev_low", "low"),
        ("prev_open", "open"),
        ("prev_close", "close"),
    ):
        if bar.get(key) is None and prev_bar.get(src) is not None:
            bar[key] = prev_bar[src]


def _enrich_bar_projections(bar: Dict[str, Any], recent: List[Dict[str, Any]]) -> None:
    """Derive ccidiff and Low-Prev/Cur angle from bar data only.

    Sierra DLL owns ProjHi/ProjLo (Pivot Points subgraphs). When the export
    omits them we leave them None so the HUD renders "—" — never invent a
    Projection value from a rolling High/Low window, which would change
    every request and mislead the trader (see P30 root-cause: 7702.75 vs
    7408.25 came from this fallback).
    """
    if bar.get("low_prev_angle") is None and len(recent) >= 2:
        cur, prev = recent[-1], recent[-2]
        if cur.get("low") is not None and prev.get("low") is not None:
            bar["low_prev_angle"] = round(
                float(math.degrees(math.atan2(cur["low"] - prev["low"], 2.0))), 1
            )
    if bar.get("ccidiff") is None:
        cci = bar.get("cci_14")
        tcci = bar.get("cci_6_tcci")
        if cci is not None and tcci is not None:
            bar["ccidiff"] = round(float(cci) - float(tcci), 2)


def _parse_sierra_payload(data: Dict[str, Any], age_s: float) -> Dict[str, Any]:
    history = data.get("history") or data.get("bars") or []
    current = data.get("current_bar")
    bar_period_s = (data.get("bar_period_minutes") or 5) * 60

    # 1. Normalize history bars
    normalized: List[Dict[str, Any]] = []
    for raw in history:
        bar = _normalize_bar(raw)
        if bar:
            normalized.append(bar)

    # 2. DLL bug: all history bars share the same ts (current export time).
    #    Reconstruct by counting backwards from the anchor before merging
    #    current_bar so the ts comparison below works correctly.
    ts_bug_detected = False
    if len(normalized) > 1:
        ts_vals = [b["ts_unix"] for b in normalized]
        if len(set(ts_vals)) == 1:
            ts_bug_detected = True
            anchor = ts_vals[-1]
            n = len(normalized)
            for i, bar in enumerate(normalized):
                reconstructed = anchor - (n - 1 - i) * bar_period_s
                bar["ts_unix"] = reconstructed
                bar["ts"] = datetime.fromtimestamp(reconstructed, tz=timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            logger.info(
                "[Woodies chart] Reconstructed %d bar timestamps (DLL ts bug): %s → %s",
                n, normalized[0]["ts"], normalized[-1]["ts"],
            )

    # 3. Merge current_bar (live building bar)
    if current:
        cur = _normalize_bar(current)
        if cur:
            if not normalized:
                normalized.append(cur)
            elif ts_bug_detected:
                # All history rows share export-time ts; current_bar is the live
                # tick of the building bar — replace tail, do not append a phantom bar.
                cur["ts_unix"] = normalized[-1]["ts_unix"]
                cur["ts"] = normalized[-1]["ts"]
                normalized[-1] = cur
            elif normalized[-1]["ts_unix"] == cur["ts_unix"]:
                # Building 5m bar: Sierra ticks update current_bar, history lag.
                normalized[-1] = cur
            elif normalized[-1]["ts_unix"] < cur["ts_unix"]:
                normalized.append(cur)

    for i, bar in enumerate(normalized):
        if i > 0:
            _attach_prev_ohlc_from_window(bar, normalized[i - 1])
        window = normalized[max(0, i - 12) : i + 1]
        _enrich_bar_projections(bar, window)
    # current_bar = enriched tail of normalized[] (not a fresh _normalize_bar(current)).
    current_out = normalized[-1] if normalized else None
    study_caption = data.get("study_caption") or data.get("study_params")
    if isinstance(study_caption, dict):
        study_caption = None
    if not study_caption:
        period = data.get("bar_period_minutes")
        period_s = f"{int(period)}m" if period is not None else "5m"
        study_caption = f"(6, 5, 14, 100, HLC Avg) · {period_s}"

    return {
        "source": "sierra_woodies_5min_json",
        "version": data.get("version"),
        "export_ts": data.get("export_ts"),
        "bar_period_minutes": data.get("bar_period_minutes"),
        "study_caption": study_caption,
        "age_s": round(age_s, 1),
        "stale": False,
        "bars": normalized,
        "current_bar": current_out,
    }


def _load_sierra_woodies(export_path: Path, max_age_s: float) -> Optional[Dict[str, Any]]:
    if not export_path.exists():
        logger.warning("[Woodies chart] %s not found", export_path)
        return None
    try:
        age_s = time.time() - export_path.stat().st_mtime
        stale = age_s > max_age_s
        with open(export_path, "r") as f:
            data = json.load(f)
        payload = _parse_sierra_payload(data, age_s)
        if stale:
            logger.warning(
                "[Woodies chart] stale export age=%.1fs > %.1fs (serving bars for display)",
                age_s,
                max_age_s,
            )
            payload["stale"] = True
            payload["error"] = f"File stale ({age_s:.0f}s > {max_age_s:.0f}s)"
        return payload
    except json.JSONDecodeError:
        logger.warning("[Woodies chart] JSON parse error")
        return None
    except Exception as e:
        logger.warning("[Woodies chart] read error: %s", e)
        return None


def _load_woodies_from_db(limit: int) -> Optional[Dict[str, Any]]:
    """Fallback: load last N bars from v9_bars_5min_woodies (Option C — OOH display).

    Used when Sierra export is stale/empty (overnight, weekend).
    Returns display-only bars with source="db_woodies_5min".
    """
    import sqlite3
    db_path = os.getenv(
        "V9_DB_PATH",
        "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db",
    )
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT ts, open, high, low, close, volume,
                      cci_14, cci_6_tcci, lsma_value, swi_value,
                      czi_value, ema_34, trend_state, predictor_next_cci,
                      zlr_detected, zlr_direction, proj_hi, proj_lo,
                      hfe_detected, hfe_direction, lsma_above_price
               FROM v9_bars_5min_woodies
               ORDER BY ts DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()
    except Exception as e:
        logger.warning("[Woodies chart] DB fallback failed: %s", e)
        return None

    if not rows:
        return None

    bars = []
    for row in reversed(rows):  # oldest first
        r = dict(row)
        try:
            ts_str = r.get("ts", "")
            # Parse ISO ts to unix
            dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ts_unix = int(dt.timestamp())
        except (ValueError, TypeError):
            continue
        bars.append({
            "ts_unix": ts_unix,
            "ts": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "cci_14": r.get("cci_14"),
            "cci_6_tcci": r.get("cci_6_tcci"),
            "ccidiff": round(float(r["cci_14"]) - float(r["cci_6_tcci"]), 2)
                if r.get("cci_14") is not None and r.get("cci_6_tcci") is not None else None,
            "trend_state": r.get("trend_state") or "GRAY",
            "trend_color": TREND_COLORS.get(r.get("trend_state") or "GRAY", TREND_COLORS["GRAY"]),
            "zlr_detected": bool(r.get("zlr_detected")),
            "zlr_direction": r.get("zlr_direction"),
            "hfe_detected": bool(r.get("hfe_detected")),
            "hfe_direction": r.get("hfe_direction"),
            "close": r.get("close"),
            "high": r.get("high"),
            "low": r.get("low"),
            "open": r.get("open"),
            "lsma_value": r.get("lsma_value"),
            "lsma_above_price": bool(r.get("lsma_above_price")),
            "predictor_next_cci": r.get("predictor_next_cci"),
            "proj_hi": r.get("proj_hi"),
            "proj_lo": r.get("proj_lo"),
            "swi_value": r.get("swi_value"),
            "czi_value": r.get("czi_value"),
            "ema_34": r.get("ema_34"),
        })

    if not bars:
        return None

    last_ts = bars[-1]["ts"]
    return {
        "source": "db_woodies_5min",
        "stale": True,
        "stale_badge": f"LAST SESSION \u00b7 {last_ts[:10]}",
        "bars": bars,
        "current_bar": bars[-1],
        "cardinality": len(bars),
    }


def _get_live_price() -> Optional[float]:
    """Get the corrected live price (bid/ask midpoint when stale) from price cache."""
    try:
        from backend.v9.api.v9.price_routes import _price_cache, _price_cache_ts
        if _price_cache and _price_cache_ts and (time.time() - _price_cache_ts) < 10.0:
            return _price_cache.get("price")
    except Exception:
        pass
    return None


@router.get("/api/v9/woodies/chart")
async def woodies_chart(limit: int = Query(50, ge=1, le=200)):
    """Return last N Woodies 5m CCI bars from Sierra export for chart panel.

    Falls back to DB (v9_bars_5min_woodies) when Sierra export is empty/stale
    (overnight, weekend). DB bars are display-only — firing gates remain RTH-locked.
    Includes `live_price` field (corrected bid/ask midpoint) for HUD display.
    """
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

    # Option C fallback: if Sierra export has no bars (overnight/weekend),
    # load from DB for display continuity.
    if not bars:
        db_payload = _load_woodies_from_db(limit)
        if db_payload:
            db_payload["requested_limit"] = limit
            live = _get_live_price()
            if live is not None:
                db_payload["live_price"] = live
                if db_payload.get("current_bar"):
                    db_payload["current_bar"]["close"] = live
            return db_payload

    tail = bars[-limit:] if len(bars) > limit else bars
    out = {**payload, "bars": tail, "requested_limit": limit, "cardinality": len(tail)}
    if tail:
        out["latest_ts_unix"] = tail[-1]["ts_unix"]

    # Content-based staleness: if latest bar is from a previous session,
    # mark studies as stale even though the file was recently written.
    # Chart 12 is RTH-only → studies freeze overnight.
    if tail:
        latest_ts = tail[-1].get("ts_unix", 0)
        content_age_s = time.time() - latest_ts if latest_ts > 0 else 0
        if content_age_s > 3600:  # >1h since last bar = previous session
            bar_date = tail[-1].get("ts", "")[:10] if tail[-1].get("ts") else "?"
            out["studies_stale"] = True
            out["studies_badge"] = f"Last RTH \u00b7 {bar_date}"

    # Inject corrected live price (bid/ask midpoint) for HUD display
    live = _get_live_price()
    if live is not None:
        out["live_price"] = live
        # Update current_bar.close to the live price so the HUD
        # shows the real market price, not the stale sc.Close
        if out.get("current_bar"):
            out["current_bar"]["close"] = live
    return out
