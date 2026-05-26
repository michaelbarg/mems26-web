"""Pydantic schemas for /api/v9/build/pattern-status response."""

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


StatusEnum = Literal["fired", "armed", "blocked", "vetoed", "not_applicable", "unknown"]


class Component(BaseModel):
    stage: str
    key: str
    spec: str
    present: bool
    value: Optional[str] = None


class DataFreshness(BaseModel):
    last_bar_ts: Optional[str] = None
    lag_seconds: Optional[float] = None
    fresh: bool = False
    threshold_seconds: int = 360


class GlobalGate(BaseModel):
    key: str
    spec: str
    present: bool
    value: Optional[str] = None


class PatternStatus(BaseModel):
    id: str
    name: str
    status: StatusEnum = "unknown"
    label: str = ""
    reason: Optional[str] = None
    fired_today: bool = False
    last_fire_ts: Optional[str] = None
    components: List[Component] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)


class SystemStatus(BaseModel):
    id: str
    name: str
    running: bool = False
    hydrated: bool = False
    mode: Optional[str] = None
    data_freshness: DataFreshness = Field(default_factory=DataFreshness)
    global_gates: List[GlobalGate] = Field(default_factory=list)
    patterns: List[PatternStatus] = Field(default_factory=list)


class RTBSession(BaseModel):
    in_session: bool = False
    minutes_to_open: Optional[int] = None
    minutes_to_close: Optional[int] = None


class BuildStatusResponse(BaseModel):
    ts: str
    build_version: str = "v1"
    session_date: str
    rtb_session: RTBSession = Field(default_factory=RTBSession)
    systems: List[SystemStatus] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
