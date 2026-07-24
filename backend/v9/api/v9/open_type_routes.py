"""Open Type endpoint — /api/v9/open_type/current

Phase 5.1 (2026-07-24): uses opening_detector_v2 (7-type Dalton taxonomy)
with v9_bars_5min_woodies (canonical SoT). Progressive display from 16:35 IL
(09:35 ET) — updates every bar until 17:30 IL (10:30 ET), then locks.
"""
from fastapi import APIRouter
from backend.v9.services.market_clock import now_et, ET
from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type
from datetime import time

router = APIRouter(tags=["open-type"])

_cached_open_type = None
_cached_date = None
_cached_lock = False

# 09:35 ET = 16:35 IL — first bar after RTH open at 09:30
_FIRST_BAR_ET = time(9, 35)
# 10:30 ET = 17:30 IL — lock after 60 min of RTH (12 bars)
_LOCK_TIME_ET = time(10, 30)


@router.get("/api/v9/open_type/current")
async def open_type_current():
    """Progressive opening type classification.

    - Before 09:35 ET: PENDING
    - 09:35–10:30 ET: live re-classification on each poll (up to 12 bars)
    - After 10:30 ET: locked (cached)
    """
    global _cached_open_type, _cached_date, _cached_lock

    et = now_et()
    today = et.date().isoformat()

    # Clear cache on new day
    if _cached_date != today:
        _cached_open_type = None
        _cached_date = today
        _cached_lock = False

    # Before first bar: pending
    if et.time() < _FIRST_BAR_ET:
        return {
            "opening_type": None,
            "direction": None,
            "confidence": 0.0,
            "status": "PENDING",
            "trigger_time": "09:35 ET (16:35 IL)",
            "reasoning": ["Awaiting first RTH bar"],
        }

    # After lock time: return cached (don't re-query)
    if _cached_lock and _cached_open_type:
        return _cached_open_type

    # Classify from live bars
    try:
        from backend.v9.db.read import read_all, read_one
        from backend.v9.services.market_clock import get_previous_trading_day

        bars_rows = read_all(
            "SELECT ts, open, high, low, close, volume "
            "FROM v9_bars_5min_woodies "
            "WHERE ts::date = current_date AND ts::time >= '16:30' "
            "ORDER BY ts ASC LIMIT 12",
            {},
        )
        rth_bars = [
            {"ts": r["ts"], "o": r["open"], "h": r["high"],
             "l": r["low"], "c": r["close"], "v": r["volume"]}
            for r in bars_rows
        ]

        if not rth_bars:
            return {
                "opening_type": None,
                "direction": None,
                "confidence": 0.0,
                "status": "PENDING",
                "reasoning": ["No RTH bars yet in v9_bars_5min_woodies"],
            }

        open_price = float(rth_bars[0]["o"]) if rth_bars[0]["o"] is not None else None

        # Previous day VA levels
        prev_date = get_previous_trading_day()
        prev_row = read_one(
            "SELECT poc_price, vah_price, val_price "
            "FROM v9_tpo_sessions "
            "WHERE trading_date = :prev_date AND session_type = 'CASH' "
            "ORDER BY id DESC LIMIT 1",
            {"prev_date": prev_date.isoformat()},
        )
        prev_vah = float(prev_row["vah_price"]) if prev_row and prev_row.get("vah_price") else None
        prev_val = float(prev_row["val_price"]) if prev_row and prev_row.get("val_price") else None

        result = detect_opening_type(
            rth_bars,
            open_price,
            prior_vah=prev_vah,
            prior_val=prev_val,
        )

        # Lock after 10:30 ET
        locked = et.time() >= _LOCK_TIME_ET
        result["status"] = "LOCKED" if locked else "LIVE"
        result["bars_used"] = len(rth_bars)

        if locked:
            _cached_open_type = result
            _cached_lock = True
        else:
            _cached_open_type = result

        return result

    except Exception as e:
        return {
            "opening_type": None,
            "direction": None,
            "confidence": 0.0,
            "status": "error",
            "reasoning": [str(e)],
        }
