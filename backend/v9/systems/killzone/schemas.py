"""Pydantic schemas for Killzone API responses."""

from pydantic import BaseModel
from typing import Optional


class KillzoneStatus(BaseModel):
    current_killzone: str
    killzone_id: str
    time_in_zone_min: int
    time_to_next_zone_min: int
    next_zone: str
    quality: str
    volatility: str
    sizing_modifier: float
    is_blocked: bool
    block_reason: Optional[str] = None
    is_trading_day: bool
    session_phase: str


class ZoneInfo(BaseModel):
    name: str
    start: str        # HH:MM ET
    end: str          # HH:MM ET
    quality: str
    volatility: str
    sizing_modifier: float
    is_blocked_default: bool
    session_phase: str
    notes: str


class ZoneListResponse(BaseModel):
    zones: list[ZoneInfo]
    count: int
