"""direction_context_live — fetch TODAY's RTH bars + CVD + TPO and run the pure
`direction_context` model. Cached ~20s. Used by the live strip endpoint and (flag-gated,
default-OFF) the trading gate. READ-ONLY; honest (Rule 1): NEUTRAL when data/IB missing.
"""
from __future__ import annotations

import os
import time as _time
from datetime import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo

_CT = ZoneInfo("America/Chicago")
_CACHE: Dict[str, Any] = {}


def _fetch_live_bars(today: str):
    """Return (bars, source). Prefer v9_bars_5min (carries CVD); but if the raw-bars
    stream stalls (e.g. 2026-06-22 stuck at 08:55) while the Woodies stream stays
    live, fall back to v9_bars_5min_woodies (correct OHLC, no CVD). Picks whichever
    table has the FRESHER last bar so the strip/gate never reads a dead stream.
    """
    from backend.v9.db.read import read_all
    q = ("SELECT (ts AT TIME ZONE 'America/Chicago')::time ct, high, low, close, %s "
         "FROM %s WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d "
         "AND (ts AT TIME ZONE 'America/Chicago')::time BETWEEN '08:30' AND '15:00' ORDER BY ts")
    try:
        main = read_all(q % ("cumulative_delta", "v9_bars_5min"), {"d": today}) or []
    except Exception:
        main = []
    try:
        wood = read_all(q % ("NULL::numeric AS cumulative_delta", "v9_bars_5min_woodies"), {"d": today}) or []
    except Exception:
        wood = []
    lm = main[-1]["ct"] if main else None
    lw = wood[-1]["ct"] if wood else None
    # Prefer woodies when it is FRESHER, OR equally-fresh but the 5min(cvd) series is
    # gapped/sparse (fewer bars over the same window). A sparse 5min series makes the CVD
    # 3-bar lookback misread (2026-06-22: gap 09:00-09:35 → cvd_slope read +1 off a trough and
    # flipped a real DOWN to NEUTRAL). Use 5min(cvd) only when it is at least as fresh AND at
    # least as complete; otherwise fall to contiguous woodies (location+breakout, no CVD).
    if wood and (lm is None or (lw is not None and (lw > lm or (lw == lm and len(wood) > len(main))))):
        rows, source = wood, "woodies(live,no-cvd)"
    else:
        rows, source = main, "5min(cvd)"
    bars = [{"high": float(b["high"]), "low": float(b["low"]), "close": float(b["close"]),
             "cumulative_delta": (float(b["cumulative_delta"]) if b["cumulative_delta"] is not None else None)}
            for b in rows]
    return bars, source


def current() -> Dict[str, Any]:
    """Current direction-context for today's RTH session (cached ~20s)."""
    today = datetime.now(_CT).date().isoformat()
    if _CACHE.get("date") == today and (_time.time() - _CACHE.get("ts", 0.0)) < 20:
        return _CACHE["val"]

    from backend.v9.db.read import read_one
    from backend.v9.systems.direction_context import compute_direction

    bars, source = _fetch_live_bars(today)

    tpo = None
    try:
        tpo = read_one(
            "SELECT ib_high, ib_low, poc_price FROM v9_tpo_sessions "
            "WHERE trading_date = :d AND session_type='CASH' ORDER BY id DESC LIMIT 1",
            {"d": today})
    except Exception:
        tpo = None
    ibh = tpo.get("ib_high") if tpo else None
    ibl = tpo.get("ib_low") if tpo else None
    poc = tpo.get("poc_price") if tpo else None

    # day_type for the trend-day override (06-16 fix) — cheap latest-state read
    day_type = None
    try:
        _dt = read_one(
            "SELECT day_type FROM v9_day_type_state "
            "WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d ORDER BY id DESC LIMIT 1",
            {"d": today})
        day_type = _dt.get("day_type") if _dt else None
    except Exception:
        day_type = None

    # --- DIRECTION_LSMA_VETO flag: LSMA-lead + CVD-veto direction override ---
    lsma_veto = os.getenv("DIRECTION_LSMA_VETO", "0").lower() in ("1", "true", "yes")
    lsma_side_val = None
    if lsma_veto:
        try:
            _lsma_row = read_one(
                "SELECT close, lsma_value FROM v9_bars_5min_woodies "
                "WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d "
                "AND lsma_value IS NOT NULL "
                "ORDER BY ts DESC LIMIT 1",
                {"d": today})
            if _lsma_row and _lsma_row.get("lsma_value") is not None:
                lsma_side_val = 1 if float(_lsma_row["close"]) > float(_lsma_row["lsma_value"]) else -1
        except Exception:
            lsma_side_val = None  # fail-safe: fall through to existing engine

    res = compute_direction(bars=bars, ib_high=ibh, ib_low=ibl, poc=poc, day_type=day_type,
                            lsma_side=lsma_side_val, lsma_veto=lsma_veto)
    out = {
        **res, "n_bars": len(bars), "source": source, "day_type": day_type,
        "ib_high": float(ibh) if ibh is not None else None,
        "ib_low": float(ibl) if ibl is not None else None,
        "poc": float(poc) if poc is not None else None,
    }
    if lsma_veto:
        out["lsma_side"] = lsma_side_val
        out["mode"] = "lsma_cvd_veto" if lsma_side_val is not None else "fallback(lsma_missing)"
    if not bars:
        out["reason"] = "no RTH bars yet (pre-open / forming)"
    _CACHE.update({"date": today, "ts": _time.time(), "val": out})
    return out
