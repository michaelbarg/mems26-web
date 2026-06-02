"""Pydantic schemas for /api/v9/build/pattern-status response."""

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


StatusEnum = Literal["fired", "armed", "blocked", "vetoed", "not_applicable", "unknown"]

# Tracks where a row's `live` value came from so the UI can flag stale sources.
FreshnessSource = Literal["sierra_export", "db", "in_memory", "inspector_eval"]


class Freshness(BaseModel):
    """When the `live` value backing a row was sampled.

    `ts`     — ISO8601 of the underlying data point (e.g. the bar that
               drove a CCI value, or `last_updated_at` of a DB row, or
               the inspector wall-clock for synthesized values).
    `lag_s`  — seconds between `ts` and the time the inspector evaluated
               the row. Always >= 0 when populated; None when the source
               timestamp was missing or could not be reconciled (e.g. a
               future ts indicating corrupt data — see
               build_status/row_helpers.parse_ts_to_utc).
    `source` — provenance tag, used for UI tooltip and debugging.
    """

    ts: Optional[str] = None
    lag_s: Optional[float] = None
    source: Optional[FreshnessSource] = None


class Component(BaseModel):
    stage: str
    key: str
    spec: str
    present: bool
    value: Optional[str] = None
    # New (additive): machine-friendly value/threshold pair + per-row freshness.
    # All three are Optional to keep older consumers / tests working unchanged.
    live: Optional[str] = None
    required: Optional[str] = None
    freshness: Optional[Freshness] = None


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
    # Same additive shape as Component so the bridge stream rows render
    # identically to per-pattern component rows.
    live: Optional[str] = None
    required: Optional[str] = None
    freshness: Optional[Freshness] = None


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


# D-OBS: Live input field for observability
class LiveInput(BaseModel):
    """Single live data field consumed by a system."""
    field: str
    value: Optional[str] = None
    source: Optional[str] = None  # stream/chart/db
    age_s: Optional[float] = None
    fresh: bool = True


# D-OBS: Interpretation — what the system derived from inputs
class Interpretation(BaseModel):
    """A derived conclusion from live inputs."""
    key: str
    value: Optional[str] = None
    from_input: Optional[str] = None  # which input(s) it was derived from
    detail: Optional[str] = None


class SystemStatus(BaseModel):
    id: str
    name: str
    running: bool = False
    hydrated: bool = False
    mode: Optional[str] = None
    data_freshness: DataFreshness = Field(default_factory=DataFreshness)
    # D-OBS: Live inputs + interpretation
    live_inputs: List[LiveInput] = Field(default_factory=list)
    interpretations: List[Interpretation] = Field(default_factory=list)
    global_gates: List[GlobalGate] = Field(default_factory=list)
    patterns: List[PatternStatus] = Field(default_factory=list)
    # System-level aggregate of today's fires, derived from v9_trades by
    # the inspector. UI uses these for the "S4 fired 2× today, last 13:45 ET"
    # header without scanning every pattern. Pre-LIVE: source-of-truth is the
    # DB, not the in-memory dedup dict — see row_helpers.fires_today().
    fired_today_count: int = 0
    last_fire_ts: Optional[str] = None


class RTBSession(BaseModel):
    in_session: bool = False
    minutes_to_open: Optional[int] = None
    minutes_to_close: Optional[int] = None


# D-RDY: Operator readiness verdict (observability only — does NOT gate firing)
ReadinessVerdict = Literal["READY", "DEGRADED", "BLOCKED"]


class ReadinessCheck(BaseModel):
    """Single PRE_TRADE_PROTOCOL check result."""
    key: str
    passed: bool
    severity: Literal["block", "degrade", "info"]
    detail: Optional[str] = None


class Readiness(BaseModel):
    """Aggregate readiness derived from PRE_TRADE_PROTOCOL checks."""
    verdict: ReadinessVerdict = "BLOCKED"
    reason: str = ""
    checks: List[ReadinessCheck] = Field(default_factory=list)


class BuildStatusResponse(BaseModel):
    ts: str
    build_version: str = "v1"
    session_date: str
    rtb_session: RTBSession = Field(default_factory=RTBSession)
    systems: List[SystemStatus] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    readiness: Readiness = Field(default_factory=Readiness)  # D-RDY
