"""Killzone API — GET /v9/killzone/active, GET /v9/killzone/zones."""

from fastapi import APIRouter, Query

from .detector import get_killzone_status
from .zones import ZONES
from .schemas import KillzoneStatus, ZoneInfo, ZoneListResponse

router = APIRouter(prefix="/v9/killzone", tags=["v9-killzone"])


@router.get("/active", response_model=KillzoneStatus)
def get_active_killzone(
    trade_in_lunch: bool = Query(False),
    trade_in_close: bool = Query(True),
    block_first_15min: bool = Query(False),
    block_last_15min: bool = Query(True),
    is_trading_day: bool = Query(True),
    is_holiday_half_day: bool = Query(False),
):
    """Return current killzone status. Pure time math, no DB."""
    return get_killzone_status(
        trade_in_lunch=trade_in_lunch,
        trade_in_close=trade_in_close,
        block_first_15min=block_first_15min,
        block_last_15min=block_last_15min,
        is_trading_day=is_trading_day,
        is_holiday_half_day=is_holiday_half_day,
    )


@router.get("/zones", response_model=ZoneListResponse)
def list_zones():
    """Return all 11 killzone definitions."""
    return ZoneListResponse(
        zones=[
            ZoneInfo(
                name=z.name,
                start=z.start.strftime("%H:%M"),
                end=z.end.strftime("%H:%M"),
                quality=z.quality,
                volatility=z.volatility,
                sizing_modifier=z.sizing_modifier,
                is_blocked_default=z.is_blocked_default,
                session_phase=z.session_phase,
                notes=z.notes,
            )
            for z in ZONES
        ],
        count=len(ZONES),
    )
