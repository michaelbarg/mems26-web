"""Market Clock — centralized time service with DST + 2026 NYSE holidays (D-068).

All time-aware logic should use this module. No hardcoded times elsewhere.
Uses zoneinfo (Python 3.9+) for DST-correct Eastern Time.

Prompt 26a adds Replay Clock Mode: in REPLAY, current market time is the
latest ingested Sierra/replay bar timestamp. The service never silently falls
back to the machine clock while REPLAY is enabled.
"""
from dataclasses import dataclass
from datetime import datetime, time, date, timedelta, timezone
from enum import Enum
import os
from typing import Optional, Union
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


class ClockMode(str, Enum):
    REALTIME = "REALTIME"
    REPLAY = "REPLAY"


class ClockStatus(str, Enum):
    READY = "READY"
    PENDING = "PENDING"


class MarketClockPendingError(RuntimeError):
    """Raised when REPLAY mode has no authoritative replay timestamp yet."""


@dataclass(frozen=True)
class ClockSnapshot:
    mode: ClockMode
    status: ClockStatus
    now_utc: Optional[datetime]
    now_et: Optional[datetime]
    source: str
    reason: Optional[str] = None
    updated_at_utc: Optional[datetime] = None

    def require_now_et(self) -> datetime:
        if self.now_et is None:
            raise MarketClockPendingError(self.reason or "market clock pending")
        return self.now_et

    def require_now_utc(self) -> datetime:
        if self.now_utc is None:
            raise MarketClockPendingError(self.reason or "market clock pending")
        return self.now_utc


def _normalize_mode(mode: Union[str, ClockMode]) -> ClockMode:
    if isinstance(mode, ClockMode):
        return mode
    return ClockMode(str(mode).upper())


def parse_market_timestamp(value) -> Optional[datetime]:
    """Parse Sierra/API timestamp inputs into timezone-aware UTC datetimes."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    else:
        raw = str(value)
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = datetime.fromtimestamp(float(raw), tz=timezone.utc)
            except (TypeError, ValueError):
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class MarketClock:
    """Central market clock with REALTIME and REPLAY modes."""

    def __init__(self, mode: Union[str, ClockMode, None] = None):
        self._mode = _normalize_mode(mode or os.getenv("MEMS26_CLOCK_MODE", "REALTIME"))
        self._replay_ts_utc: Optional[datetime] = None
        self._replay_source: Optional[str] = None
        self._replay_updated_at_utc: Optional[datetime] = None

    @property
    def mode(self) -> ClockMode:
        return self._mode

    def set_mode(self, mode: Union[str, ClockMode]) -> None:
        self._mode = _normalize_mode(mode)

    def reset_replay_timestamp(self) -> None:
        self._replay_ts_utc = None
        self._replay_source = None
        self._replay_updated_at_utc = None

    def update_replay_timestamp(self, ts, source: str = "bar") -> ClockSnapshot:
        parsed = parse_market_timestamp(ts)
        if parsed is None:
            return self.current()
        self._replay_ts_utc = parsed
        self._replay_source = source
        self._replay_updated_at_utc = datetime.now(UTC)
        return self.current()

    def current(self) -> ClockSnapshot:
        if self._mode == ClockMode.REALTIME:
            now = datetime.now(UTC)
            return ClockSnapshot(
                mode=self._mode,
                status=ClockStatus.READY,
                now_utc=now,
                now_et=now.astimezone(ET),
                source="system_clock",
            )

        if self._replay_ts_utc is None:
            return ClockSnapshot(
                mode=self._mode,
                status=ClockStatus.PENDING,
                now_utc=None,
                now_et=None,
                source=self._replay_source or "replay_bar",
                reason="replay_clock_enabled_but_no_replay_timestamp",
                updated_at_utc=self._replay_updated_at_utc,
            )

        return ClockSnapshot(
            mode=self._mode,
            status=ClockStatus.READY,
            now_utc=self._replay_ts_utc,
            now_et=self._replay_ts_utc.astimezone(ET),
            source=self._replay_source or "replay_bar",
            updated_at_utc=self._replay_updated_at_utc,
        )


_CLOCK = MarketClock()


def get_clock() -> MarketClock:
    return _CLOCK


def set_clock_mode(mode: Union[str, ClockMode]) -> None:
    _CLOCK.set_mode(mode)


def update_replay_timestamp(ts, source: str = "bar") -> ClockSnapshot:
    return _CLOCK.update_replay_timestamp(ts, source=source)


def reset_replay_timestamp() -> None:
    _CLOCK.reset_replay_timestamp()


def current_clock_state() -> ClockSnapshot:
    return _CLOCK.current()


def now_et() -> datetime:
    return _CLOCK.current().require_now_et()

def now_utc() -> datetime:
    return _CLOCK.current().require_now_utc()

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

def minutes_since_rth_open(dt: datetime = None) -> int:
    et = (dt or now_et()).astimezone(ET)
    rth_open = datetime.combine(et.date(), RTH_OPEN, tzinfo=ET)
    return max(0, int((et - rth_open).total_seconds() / 60))

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
