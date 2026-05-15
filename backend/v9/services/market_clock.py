"""Market Clock — centralized time service with DST + 2026 NYSE holidays (D-068).

All time-aware logic should use this module. No hardcoded times elsewhere.
Uses zoneinfo (Python 3.9+) for DST-correct Eastern Time.
"""
from datetime import datetime, time, date, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# RTH constants (Eastern Time)
RTH_OPEN = time(9, 30, 0)
RTH_CLOSE = time(16, 0, 0)
IB_END = time(10, 30, 0)
HALF_DAY_CLOSE = time(13, 0, 0)

# 2026 NYSE holidays (D-073 verified against CME calendar)
HOLIDAYS_2026 = {
    date(2026, 1, 1):   "New Year's Day",
    date(2026, 1, 19):  "MLK Day",
    date(2026, 2, 16):  "Presidents Day",
    date(2026, 4, 3):   "Good Friday",
    date(2026, 5, 25):  "Memorial Day",
    date(2026, 6, 19):  "Juneteenth",
    date(2026, 7, 3):   "Independence Day (observed)",
    date(2026, 9, 7):   "Labor Day",
    date(2026, 11, 26): "Thanksgiving",
    date(2026, 12, 25): "Christmas Day",
}

HALF_DAYS_2026 = {
    date(2026, 11, 27): "Black Friday",
    date(2026, 12, 24): "Christmas Eve",
}


def now_et() -> datetime:
    return datetime.now(ET)

def now_utc() -> datetime:
    return datetime.now(UTC)

def is_rth_open(dt: datetime = None) -> bool:
    et = (dt or now_et()).astimezone(ET)
    if et.weekday() >= 5:
        return False
    if et.date() in HOLIDAYS_2026:
        return False
    close = HALF_DAY_CLOSE if et.date() in HALF_DAYS_2026 else RTH_CLOSE
    return RTH_OPEN <= et.time() < close

def is_ib_window(dt: datetime = None) -> bool:
    et = (dt or now_et()).astimezone(ET)
    if et.weekday() >= 5 or et.date() in HOLIDAYS_2026:
        return False
    return RTH_OPEN <= et.time() < IB_END

def is_market_holiday(d: date) -> bool:
    return d in HOLIDAYS_2026

def is_half_day(d: date) -> bool:
    return d in HALF_DAYS_2026

def get_session_date(dt: datetime = None) -> date:
    return (dt or now_et()).astimezone(ET).date()

def get_previous_trading_day(d: date = None) -> date:
    d = d or now_et().date()
    while True:
        d = d - timedelta(days=1)
        if d.weekday() < 5 and d not in HOLIDAYS_2026:
            return d

def get_session_info(dt: datetime = None):
    et = (dt or now_et()).astimezone(ET)
    d = et.date()
    close_time = HALF_DAY_CLOSE if d in HALF_DAYS_2026 else RTH_CLOSE
    rth_open_et = datetime.combine(d, RTH_OPEN, tzinfo=ET)
    rth_close_et = datetime.combine(d, close_time, tzinfo=ET)
    ib_end_et = datetime.combine(d, IB_END, tzinfo=ET)
    return {
        "session_date": d,
        "is_holiday": d in HOLIDAYS_2026,
        "is_half_day": d in HALF_DAYS_2026,
        "is_weekend": et.weekday() >= 5,
        "rth_open_utc": rth_open_et.astimezone(UTC),
        "rth_close_utc": rth_close_et.astimezone(UTC),
        "ib_end_utc": ib_end_et.astimezone(UTC),
    }
