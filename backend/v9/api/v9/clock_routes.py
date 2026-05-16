"""Market Clock endpoint — /api/v9/clock/now (D-068)."""
from fastapi import APIRouter
from backend.v9.services import market_clock as mc

router = APIRouter(tags=["clock"])


@router.get("/api/v9/clock/now")
def get_clock_now():
    """Current market time with session info, DST, holidays."""
    clock = mc.current_clock_state()
    if clock.status != mc.ClockStatus.READY:
        return {
            "mode": clock.mode.value,
            "status": clock.status.value,
            "source": clock.source,
            "reason": clock.reason,
            "now_utc": None,
            "now_et": None,
            "updated_at_utc": clock.updated_at_utc.isoformat() if clock.updated_at_utc else None,
        }

    now_et = clock.require_now_et()
    now_utc = clock.require_now_utc()
    s = mc.get_session_info(now_et)

    sec_ib = max(0, int((s["ib_end_utc"] - now_utc).total_seconds()))
    sec_close = max(0, int((s["rth_close_utc"] - now_utc).total_seconds()))

    return {
        "mode": clock.mode.value,
        "status": clock.status.value,
        "source": clock.source,
        "now_utc": now_utc.isoformat(),
        "now_et": now_et.isoformat(),
        "tz_offset_hours": now_et.utcoffset().total_seconds() / 3600,
        "tz_name": now_et.tzname(),
        "is_dst": bool(now_et.dst()),
        "session_date": s["session_date"].isoformat(),
        "is_holiday": s["is_holiday"],
        "is_half_day": s["is_half_day"],
        "is_weekend": s["is_weekend"],
        "is_rth_open": mc.is_rth_open(),
        "is_ib_window": mc.is_ib_window(),
        "rth_open_utc": s["rth_open_utc"].isoformat(),
        "rth_close_utc": s["rth_close_utc"].isoformat(),
        "ib_end_utc": s["ib_end_utc"].isoformat(),
        "seconds_until_ib_close": sec_ib,
        "seconds_until_rth_close": sec_close,
    }
