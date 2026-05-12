"""Killzone gate — simple boolean: should trading be allowed right now?"""

from datetime import datetime, timezone
from typing import Optional

from .detector import get_killzone_status


def is_gate_open(
    now_utc: Optional[datetime] = None,
    *,
    trade_in_lunch: bool = False,
    trade_in_close: bool = True,
    block_first_15min: bool = False,
    block_last_15min: bool = True,
    is_trading_day: bool = True,
    is_holiday_half_day: bool = False,
    min_quality: str = "LOW",
) -> bool:
    """Return True if trading is allowed right now.

    Checks: not blocked, quality >= min_quality, sizing > 0.
    """
    status = get_killzone_status(
        now_utc,
        trade_in_lunch=trade_in_lunch,
        trade_in_close=trade_in_close,
        block_first_15min=block_first_15min,
        block_last_15min=block_last_15min,
        is_trading_day=is_trading_day,
        is_holiday_half_day=is_holiday_half_day,
    )

    if status["is_blocked"]:
        return False
    if status["sizing_modifier"] <= 0.0:
        return False

    # Quality gate
    quality_order = {"OFF": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    current_q = quality_order.get(status["quality"], 0)
    min_q = quality_order.get(min_quality, 1)

    return current_q >= min_q
