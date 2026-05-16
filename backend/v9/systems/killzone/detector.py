"""Killzone detector — O(1) zone lookup from UTC datetime."""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from typing import Optional

from .zones import ZONES, Zone, ZONE_BY_NAME

ET = ZoneInfo("America/New_York")


def _time_in_range(t, start, end) -> bool:
    """Check if time t is in [start, end). Handles midnight wrap for AFTER_HOURS."""
    if start <= end:
        return start <= t < end
    # Wraps midnight: e.g. 16:00 -> 05:00
    return t >= start or t < end


def get_current_zone(now_utc: Optional[datetime] = None) -> Zone:
    """Return the active Zone for the given UTC time (default: now).

    Converts UTC to ET (America/New_York) — DST-aware.
    Always returns exactly one zone (no gaps, no overlaps).
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    # Convert to ET
    now_et = now_utc.astimezone(ET)
    t = now_et.time()

    for zone in ZONES:
        if _time_in_range(t, zone.start, zone.end):
            return zone

    # Fallback (should never reach — AFTER_HOURS covers the gap)
    return ZONE_BY_NAME["AFTER_HOURS"]


def get_killzone_status(
    now_utc: Optional[datetime] = None,
    *,
    trade_in_lunch: bool = False,
    trade_in_close: bool = True,
    block_first_15min: bool = False,
    block_last_15min: bool = True,
    is_trading_day: bool = True,
    is_holiday_half_day: bool = False,
    news_events: Optional[list] = None,
    news_block_minutes: int = 15,
) -> dict:
    """Full killzone status output per spec Section 4.

    Returns the output schema dict.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    now_et = now_utc.astimezone(ET)
    zone = _get_half_day_zone(now_et) if is_holiday_half_day else get_current_zone(now_utc)

    # Calculate time_in_zone and time_to_next
    from datetime import timedelta

    zone_start_dt = now_et.replace(
        hour=zone.start.hour, minute=zone.start.minute, second=0, microsecond=0,
    )
    # Handle AFTER_HOURS: if current time < start (i.e. after midnight, before 05:00)
    if zone.name == "AFTER_HOURS" and now_et.time() < zone.start:
        zone_start_dt -= timedelta(days=1)

    time_in_zone = now_et - zone_start_dt
    time_in_zone_min = max(0, int(time_in_zone.total_seconds() / 60))

    # Find next zone
    zone_idx = next(i for i, z in enumerate(ZONES) if z.name == zone.name)
    next_zone = ZONES[(zone_idx + 1) % len(ZONES)]

    # Time to next zone
    next_start_dt = now_et.replace(
        hour=next_zone.start.hour, minute=next_zone.start.minute, second=0, microsecond=0,
    )
    if next_start_dt <= now_et:
        next_start_dt += timedelta(days=1)
    time_to_next_min = max(0, int((next_start_dt - now_et).total_seconds() / 60))

    # Blocked logic
    is_blocked = zone.is_blocked_default
    block_reason = None

    if not is_trading_day:
        is_blocked = True
        block_reason = "holiday"
    elif _is_near_news(now_utc, news_events, news_block_minutes):
        is_blocked = True
        block_reason = "news_block"
    elif zone.name == "LUNCH" and not trade_in_lunch:
        is_blocked = True
        block_reason = "lunch_blocked"
    elif zone.name == "LUNCH" and trade_in_lunch:
        is_blocked = False
    elif zone.name in ("CLOSE_APPROACH", "CLOSE_FINAL") and not trade_in_close:
        is_blocked = True
        block_reason = "close_blocked"
    elif zone.name == "CLOSE_FINAL" and trade_in_close:
        # trade_in_close=True allows CLOSE_APPROACH but CLOSE_FINAL stays blocked
        is_blocked = True
        block_reason = "close_final"

    # First/last 15-min blocks within any zone
    if block_first_15min and time_in_zone_min < 15 and zone.name == "NY_OPEN_VOLATILITY":
        is_blocked = True
        block_reason = "first_15min_blocked"
    if block_last_15min and time_to_next_min <= 15 and zone.name == "CLOSE_APPROACH":
        is_blocked = True
        block_reason = "last_15min_blocked"

    # Half-day hard close at 13:00 ET. Earlier in the day, zones are scaled by
    # _get_half_day_zone rather than just using normal RTH times.
    if is_holiday_half_day and now_et.hour >= 13:
        is_blocked = True
        block_reason = "half_day_closed"

    # Sizing
    sizing = 0.0 if is_blocked else zone.sizing_modifier

    return {
        "current_killzone": zone.name,
        "killzone_id": zone.name,
        "time_in_zone_min": time_in_zone_min,
        "time_to_next_zone_min": time_to_next_min,
        "next_zone": next_zone.name,
        "quality": zone.quality,
        "volatility": zone.volatility,
        "sizing_modifier": sizing,
        "is_blocked": is_blocked,
        "block_reason": block_reason,
        "is_trading_day": is_trading_day,
        "session_phase": zone.session_phase,
    }


def _get_half_day_zone(now_et: datetime) -> Zone:
    """Scaled half-day zones for 09:30-13:00 ET sessions.

    This intentionally keeps the same 11-zone vocabulary while compressing the
    regular cash-session progression into the early close.
    """
    t = now_et.time()
    if t < time(9, 30):
        return ZONE_BY_NAME["PRE_MARKET"]
    if time(9, 30) <= t < time(9, 38):
        return ZONE_BY_NAME["NY_OPEN_VOLATILITY"]
    if time(9, 38) <= t < time(10, 0):
        return ZONE_BY_NAME["NY_OPEN_IB"]
    if time(10, 0) <= t < time(10, 30):
        return ZONE_BY_NAME["NY_PRIME"]
    if time(10, 30) <= t < time(11, 0):
        return ZONE_BY_NAME["PRE_LUNCH"]
    if time(11, 0) <= t < time(11, 30):
        return ZONE_BY_NAME["LUNCH"]
    if time(11, 30) <= t < time(12, 15):
        return ZONE_BY_NAME["PM_PRIME"]
    if time(12, 15) <= t < time(13, 0):
        return ZONE_BY_NAME["CLOSE_APPROACH"]
    return ZONE_BY_NAME["AFTER_HOURS"]


def _is_near_news(now_utc: datetime, news_events: Optional[list], window_min: int) -> bool:
    if not news_events:
        return False
    for event in news_events:
        event_ts = None
        if isinstance(event, datetime):
            event_ts = event
        elif isinstance(event, dict):
            event_ts = event.get("ts") or event.get("timestamp") or event.get("time")
        if isinstance(event_ts, str):
            try:
                event_ts = datetime.fromisoformat(event_ts.replace("Z", "+00:00"))
            except ValueError:
                event_ts = None
        if isinstance(event_ts, datetime):
            if event_ts.tzinfo is None:
                event_ts = event_ts.replace(tzinfo=timezone.utc)
            delta_min = abs((now_utc - event_ts.astimezone(timezone.utc)).total_seconds()) / 60
            if delta_min <= window_min:
                return True
    return False
