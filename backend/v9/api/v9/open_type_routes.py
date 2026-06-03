"""Open Type endpoint — /api/v9/open_type/current (D-072)."""
from fastapi import APIRouter
from backend.v9.services.market_clock import now_et, is_rth_open, ET
from backend.v9.systems.day_type.open_type import classify_open_type, TRIGGER_TIME
from datetime import time

router = APIRouter(tags=["open-type"])

_cached_open_type = None
_cached_date = None


@router.get("/api/v9/open_type/current")
async def open_type_current():
    """Current open type classification. Pending before 10:00 ET, classified after."""
    global _cached_open_type, _cached_date
    import requests
    from datetime import date

    et = now_et()
    today = et.date().isoformat()

    # Clear cache on new day
    if _cached_date != today:
        _cached_open_type = None
        _cached_date = today

    # Return cached if available
    if _cached_open_type:
        return _cached_open_type

    # Before trigger time: pending
    if et.time() < TRIGGER_TIME:
        return {
            "type": None,
            "status": "pending",
            "trigger_time": "10:00 ET",
            "seconds_until_trigger": max(0, int((
                et.replace(hour=10, minute=0, second=0) - et
            ).total_seconds())),
            "reasoning": ["Awaiting 10:00 ET (full 30-min RTH window)"],
        }

    # After trigger: classify (direct DB read — no self-referential HTTP)
    try:
        from backend.v9.db.read import read_all, read_one
        from backend.v9.services.market_clock import get_previous_trading_day

        bars_rows = read_all(
            "SELECT ts, open, high, low, close, volume FROM v9_bars_5min WHERE date(ts)=:today ORDER BY ts LIMIT 12",
            {"today": today},
        )
        rth_bars = [{"ts": r["ts"], "o": r["open"], "h": r["high"], "l": r["low"], "c": r["close"], "v": r["volume"]} for r in bars_rows]

        open_price = rth_bars[0]["o"] if rth_bars else 0

        # Previous day VA
        prev_date = get_previous_trading_day()
        prev_row = read_one(
            "SELECT poc_price, vah_price, val_price FROM v9_tpo_sessions WHERE trading_date=:prev_date AND session_type='CASH' ORDER BY id DESC LIMIT 1",
            {"prev_date": prev_date.isoformat()},
        )

        prev_vah = float(prev_row["vah_price"]) if prev_row and prev_row["vah_price"] else None
        prev_val = float(prev_row["val_price"]) if prev_row and prev_row["val_price"] else None

        result = classify_open_type(rth_bars[:6], open_price, prev_vah, prev_val)
        result["status"] = "classified"
        _cached_open_type = result
        return result

    except Exception as e:
        return {"type": None, "status": "error", "reasoning": [str(e)]}
