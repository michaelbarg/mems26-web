"""Pydantic schemas for Day Type Engine."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────

class DayType(str, Enum):
    Trend_Normal = "Trend_Normal"
    Trend_DD = "Trend_DD"
    Variation = "Variation"
    Normal = "Normal"
    Neutral = "Neutral"
    Nontrend = "Nontrend"
    UNKNOWN = "UNKNOWN"


class OpeningType(str, Enum):
    OPEN_DRIVE = "OPEN_DRIVE"
    OPEN_TEST_DRIVE = "OPEN_TEST_DRIVE"
    OPEN_REJECTION_REVERSE = "OPEN_REJECTION_REVERSE"
    OPEN_AUCTION_IN = "OPEN_AUCTION_IN"
    OPEN_AUCTION_OUT = "OPEN_AUCTION_OUT"
    UNKNOWN = "UNKNOWN"


class IBWidth(str, Enum):
    NARROW = "NARROW"      # <15 pt
    MEDIUM = "MEDIUM"      # 15-20 pt
    WIDE = "WIDE"          # >20 pt
    UNKNOWN = "UNKNOWN"


class Stage(str, Enum):
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    B1 = "B1"
    B2 = "B2"
    B3 = "B3"
    B4 = "B4"
    B5 = "B5"
    B6 = "B6"
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"


class LockState(str, Enum):
    PENDING = "PENDING"
    LOCKED = "LOCKED"
    LOCKED_LOW_CONF = "LOCKED_LOW_CONF"


class Behavior(str, Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    FAILED_EXTENSION = "FAILED_EXTENSION"
    COMPRESSED = "COMPRESSED"
    DEVELOPING = "DEVELOPING"


class RangeCategory(str, Enum):
    COMPRESSED = "COMPRESSED"    # <0.7 ATR
    NORMAL = "NORMAL"            # 0.7-1.3 ATR
    EXPANDED = "EXPANDED"        # 1.3-2.0 ATR
    EXTREME = "EXTREME"          # >=2.0 ATR


class FailedExtensionType(str, Enum):
    NONE = "NONE"
    STRONG_FAILED_UP = "STRONG_FAILED_UP"
    STRONG_FAILED_DOWN = "STRONG_FAILED_DOWN"
    DOUBLE_FAILED = "DOUBLE_FAILED"


# ── Input ────────────────────────────────────────────────────────────────

class BarInput(BaseModel):
    """Single bar input to the Day Type Engine."""
    ts: float                                   # epoch seconds
    session_min: int                            # minutes since 09:30 ET
    open: float
    high: float
    low: float
    close: float
    volume: float = 0
    # Previous day context (A1)
    pd_high: Optional[float] = None
    pd_low: Optional[float] = None
    pd_close: Optional[float] = None
    pd_settle: Optional[float] = None
    overnight_high: Optional[float] = None
    overnight_low: Optional[float] = None
    # ATR for range comparison (B5)
    atr: Optional[float] = None
    # IB data (fed in after IB closes, or accumulated)
    ib_high: Optional[float] = None
    ib_low: Optional[float] = None
    # Extension tracking
    extensions_up: int = 0
    extensions_down: int = 0
    returned_to_range: bool = False


# ── Stage Outputs ────────────────────────────────────────────────────────

class PreOpenContext(BaseModel):
    """A1 output: pre-open context analysis."""
    gap_size: float = 0.0
    gap_direction: str = "FLAT"          # UP, DOWN, FLAT
    location_vs_pd: str = "INSIDE"       # ABOVE, BELOW, INSIDE
    overnight_bias: str = "NEUTRAL"      # BULLISH, BEARISH, NEUTRAL


class OpeningDetection(BaseModel):
    """A2 output: opening type detection."""
    opening_type: OpeningType = OpeningType.UNKNOWN
    drive_direction: str = "NEUTRAL"     # UP, DOWN, NEUTRAL
    confidence: float = 0.0


class IBClassification(BaseModel):
    """A4 output: IB lock & width classification."""
    ib_high: float = 0.0
    ib_low: float = 0.0
    ib_range: float = 0.0
    ib_width: IBWidth = IBWidth.UNKNOWN


class VoteRecord(BaseModel):
    """A single day-type vote with confidence."""
    day_type: DayType = DayType.UNKNOWN
    confidence: float = 0.0
    stage: Stage = Stage.B1
    reason: str = ""


class PlaybookOutput(BaseModel):
    """C3 output: tactical playbook for the classified day."""
    day_type: DayType = DayType.UNKNOWN
    strategy: str = ""                   # e.g. "TREND_FOLLOW", "FADE_EXTREMES"
    sizing: str = "STANDARD"            # SMALL, STANDARD, AGGRESSIVE
    time_stop_min: int = 0
    key_rules: List[str] = Field(default_factory=list)
    notes: str = ""


# ── Main State ───────────────────────────────────────────────────────────

class DayTypeState(BaseModel):
    """Full state output of the Day Type Engine."""
    stage: Stage = Stage.A1
    day_type: DayType = DayType.UNKNOWN
    confidence: float = 0.0
    lock_state: LockState = LockState.PENDING
    opening_type: OpeningType = OpeningType.UNKNOWN
    ib_width: IBWidth = IBWidth.UNKNOWN
    behavior: Behavior = Behavior.DEVELOPING
    range_category: RangeCategory = RangeCategory.NORMAL
    failed_extension: FailedExtensionType = FailedExtensionType.NONE
    vote_history: List[VoteRecord] = Field(default_factory=list)
    pre_open: Optional[PreOpenContext] = None
    opening: Optional[OpeningDetection] = None
    ib_class: Optional[IBClassification] = None
    playbook: Optional[PlaybookOutput] = None
    session_min: int = 0
    meta: Dict[str, Any] = Field(default_factory=dict)


# ── API Response Wrappers ────────────────────────────────────────────────

class DayTypeStateResponse(BaseModel):
    """GET /v9/day_type/state response."""
    state: DayTypeState


class DayTypeHistoryResponse(BaseModel):
    """GET /v9/day_type/history response."""
    items: List[DayTypeState]
    count: int


class ProcessBarResponse(BaseModel):
    """POST /v9/day_type/process response."""
    state: DayTypeState
    stage_changed: bool = False
