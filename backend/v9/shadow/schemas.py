"""P29.5 — SHADOW data collection schemas.

Defines the 6 event categories that SHADOW mode will log:
  1. BarRecord + StreamHealthSnapshot — bars and stream health
  2. SystemStateSnapshot — S1-S6 state at a point in time
  3. PreFireDecision — pre_fire_validator results
  4. GatewayDecision — route_setup results (shadow/demo/live slots)
  5. ReasonTree — auditable decision tree trace
  6. LifecycleEvent — trade state transitions

These are Pydantic models for offline validation.
No SHADOW activation, no runtime wiring, no Redis writes.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── 1. Bars + Stream Health ──────────────────────────────────────

class BarRecord(BaseModel):
    """A single 5-min OHLCV bar as stored by the aggregator."""
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    session: str = ""
    is_partial: bool = False

    @model_validator(mode="after")
    def high_gte_low(self):
        if self.high < self.low:
            raise ValueError(f"high ({self.high}) < low ({self.low})")
        return self


class StreamStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GREY = "grey"


class StreamHealthEntry(BaseModel):
    """Health of a single bridge stream."""
    name: str
    status: StreamStatus
    age_sec: float
    push_count: int
    error_count: int = 0
    subscribed_systems: List[int] = Field(default_factory=list)
    last_push_ts: Optional[float] = None


class StreamHealthSnapshot(BaseModel):
    """Point-in-time snapshot of all stream health metrics."""
    ts: str
    streams: List[StreamHealthEntry]
    summary: Dict[str, int]  # {green: N, yellow: N, red: N, grey: N}


# ── 2. System State Snapshots ────────────────────────────────────

class S1DayTypeState(BaseModel):
    """S1 Day Type — OBSERVING system state."""
    day_type: str = "UNKNOWN"
    confidence: int = 0
    classified: bool = False
    stage: Optional[str] = None
    opening_type: Optional[str] = None
    ib_range: Optional[float] = None
    ib_width_class: Optional[str] = None


class S2FiveMinState(BaseModel):
    """S2 Five-Min T1 — FIRING system state."""
    running: bool = False
    hydrated: bool = False
    mode: str = "WEEKEND"
    buffer_size: int = 0
    last_pattern: Optional[str] = None
    last_confluence: int = 0
    last_classification: Optional[str] = None
    opening_type: Optional[str] = None


class S3FootprintState(BaseModel):
    """S3 Footprint T3 — FIRING system state."""
    running: bool = False
    hydrated: bool = False
    last_pattern: Optional[str] = None
    last_confluence: int = 0
    buffer_size: int = 0
    bars_processed_today: int = 0
    last_fire: Optional[Dict[str, Any]] = None


class S4WoodiesState(BaseModel):
    """S4 Woodies T2 — FIRING system state."""
    running: bool = False
    hydrated: bool = False
    timeframe: str = "5min"
    trend_state: str = "GRAY"
    cci_14: Optional[float] = None
    cci_6_tcci: Optional[float] = None
    buffer_size: int = 0
    classification: str = "NO_SETUP"
    ready_to_route: bool = False
    decision_tree: Dict[str, Any] = Field(default_factory=dict)


class S5TPOState(BaseModel):
    """S5 TPO — OBSERVING system state."""
    running: bool = False
    hydrated: bool = False
    poc: Optional[float] = None
    vah: Optional[float] = None
    val: Optional[float] = None
    session: Optional[str] = None
    bars_processed_today: int = 0


class S6KillzoneState(BaseModel):
    """S6 Killzone — OBSERVING + GATE system state."""
    running: bool = False
    hydrated: bool = False
    current_zone: Optional[Dict[str, Any]] = None
    next_zone: Optional[Dict[str, Any]] = None
    clock_status: Optional[str] = None
    clock_mode: Optional[str] = None


# Maps system_id to its state model
SYSTEM_STATE_MODELS = {
    1: S1DayTypeState,
    2: S2FiveMinState,
    3: S3FootprintState,
    4: S4WoodiesState,
    5: S5TPOState,
    6: S6KillzoneState,
}


class SystemStateSnapshot(BaseModel):
    """Cross-system snapshot at a trade event."""
    captured_ts: str
    trigger: str  # entry|t1_hit|t2_hit|t3_hit|stop_hit|close
    firing_system_id: Optional[int] = None
    systems: Dict[str, Any]  # {"1": {...}, "2": {...}, ...}
    market: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("trigger")
    @classmethod
    def valid_trigger(cls, v):
        allowed = {"entry", "t1_hit", "t2_hit", "t3_hit", "stop_hit", "close"}
        if v not in allowed:
            raise ValueError(f"trigger must be one of {allowed}, got {v!r}")
        return v


# ── 3. Pre-Fire Decisions ────────────────────────────────────────

class PreFireDecision(BaseModel):
    """Result of pre_fire_validator for a proposed trade setup."""
    ts: str
    system_id: str  # T1_NUMBER_BAR | T2_WOODIES | T3_FOOTPRINT
    direction: str  # LONG | SHORT
    entry_price: float
    stop_price: float
    t1_price: float
    t2_price: float
    confidence: int
    time_stop_minutes: int
    valid: bool
    fail_reason: Optional[str] = None

    @field_validator("direction")
    @classmethod
    def valid_direction(cls, v):
        if v not in ("LONG", "SHORT"):
            raise ValueError(f"direction must be LONG or SHORT, got {v!r}")
        return v


# ── 4. Gateway Dry-Run Decisions ─────────────────────────────────

class GatewayRejection(BaseModel):
    """A single mode rejection from route_setup."""
    mode: str  # shadow | demo | live
    reason: str


class GatewayDecision(BaseModel):
    """Result of TradingGateway.route_setup()."""
    ts: str
    system_id: int  # 2, 3, or 4
    shadow_trade_id: int
    demo_trade_id: Optional[int] = None
    live_trade_id: Optional[int] = None
    rejections: List[GatewayRejection] = Field(default_factory=list)

    @field_validator("system_id")
    @classmethod
    def valid_firing_system(cls, v):
        if v not in (2, 3, 4):
            raise ValueError(f"system_id must be 2, 3, or 4, got {v}")
        return v


# ── 5. Reason Trees ─────────────────────────────────────────────

class StageStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    DELEGATED = "DELEGATED"
    PENDING = "PENDING"


class ReasonTreeStage(BaseModel):
    """One stage in a decision tree evaluation."""
    stage_id: str  # A1, A2, ..., B14
    status: StageStatus
    message: str = ""
    owner: str = ""  # woodies | touchpoint_api | pre_fire_validator | ...
    details: Dict[str, Any] = Field(default_factory=dict)


class ReasonTree(BaseModel):
    """Full decision tree trace for one fire/block decision."""
    ts: str
    system_id: int  # 2, 3, or 4
    stages: List[ReasonTreeStage]
    outcome: str  # fire | block | skip
    classification: Optional[str] = None
    direction: Optional[str] = None

    @field_validator("outcome")
    @classmethod
    def valid_outcome(cls, v):
        if v not in ("fire", "block", "skip"):
            raise ValueError(f"outcome must be fire/block/skip, got {v!r}")
        return v


# ── 6. Lifecycle Events ─────────────────────────────────────────

class TradeState(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CLOSED = "CLOSED"


class LifecycleEvent(BaseModel):
    """Trade state transition event."""
    ts: str
    trade_id: int
    event_type: str  # trade.opened | trade.filled | trade.t1_hit | ...
    from_state: Optional[TradeState] = None
    to_state: TradeState
    mode: str = "shadow"  # shadow | demo | live
    data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("mode")
    @classmethod
    def valid_mode(cls, v):
        if v not in ("shadow", "demo", "live"):
            raise ValueError(f"mode must be shadow/demo/live, got {v!r}")
        return v


# ── Retention Policy ─────────────────────────────────────────────

RETENTION_POLICY = {
    "bars":             {"sink": "sqlite:v9_bars_5min",         "ttl_days": 90},
    "stream_health":    {"sink": "memory + sqlite:v9_stream_health", "ttl_days": 30},
    "system_snapshots": {"sink": "sqlite:v9_trade.cross_context (JSON)", "ttl_days": 180},
    "pre_fire":         {"sink": "sqlite:v9_pre_fire_log",      "ttl_days": 90},
    "gateway":          {"sink": "sqlite:v9_trade (mode columns)", "ttl_days": 180},
    "reason_trees":     {"sink": "sqlite:v9_reason_trees",      "ttl_days": 180},
    "lifecycle":        {"sink": "redis:v9:trades:events + sqlite:v9_trade_events", "ttl_days": 90},
}
