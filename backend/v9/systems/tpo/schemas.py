"""Pydantic schemas for TPO Profile system (System 5)."""

from typing import Optional, List, Dict
from enum import Enum
from pydantic import BaseModel, Field


# ── Enums ──

class SessionState(str, Enum):
    PRE_OPEN = "PRE_OPEN"
    BUILDING = "BUILDING"
    LOCKED = "LOCKED"
    CLOSED = "CLOSED"


class IBWidth(str, Enum):
    NARROW = "NARROW"    # < 15 pts
    MEDIUM = "MEDIUM"    # 15-25 pts
    WIDE = "WIDE"        # > 25 pts


class ProfileShape(str, Enum):
    D = "D"                        # Normal Day — symmetric, POC mid
    WIDE_D = "WIDE_D"              # Variation Day — spread out
    COMPACT_D = "COMPACT_D"        # Non-trend — tight
    P = "P"                        # Buy day — POC upper
    b = "b"                        # Sell day — POC lower
    DOUBLE_DIST = "DOUBLE_DIST"    # Two POCs
    THIN = "THIN"                  # Trend day — narrow elongated
    NEUTRAL = "NEUTRAL"            # Both extensions


class MigrationPattern(str, Enum):
    FAILED = "FAILED"
    ACCEPTED = "ACCEPTED"
    ROTATIONAL = "ROTATIONAL"
    STUCK = "STUCK"


class OTFClarity(str, Enum):
    BOTH_CLEAR = "BOTH_CLEAR"      # buying + selling tail
    SELLERS_CLEAR = "SELLERS_CLEAR" # selling tail only → LONG
    BUYERS_CLEAR = "BUYERS_CLEAR"  # buying tail only → SHORT
    UNCLEAR = "UNCLEAR"            # neither → no trades


class Intent(str, Enum):
    BUYER = "BUYER"
    SELLER = "SELLER"
    NONE = "NONE"


# ── Config ──

class TPOConfig(BaseModel):
    """Admin-configurable parameters per MEMS26_TPO_TREE_V2 spec."""
    tpo_period_minutes: int = 30
    value_area_pct: float = 0.70
    tick_size: float = 0.25
    naked_poc_lookback_days: int = 5
    single_print_min_letters: int = 1
    tail_min_letters: int = 2
    hvn_top_pct: float = 0.20
    lvn_bottom_pct: float = 0.10
    ib_width_narrow_max: float = 15.0
    ib_width_wide_min: float = 25.0
    poc_migration_threshold: float = 1.5
    poc_stuck_letters: int = 3
    open_pos_threshold_pts: float = 5.0
    reversal_threshold_pts: float = 3.0


# ── Data structures ──

class TPOLevel(BaseModel):
    """Single price level in TPO map."""
    price: float
    letters: List[str] = []

    @property
    def count(self) -> int:
        return len(self.letters)


class InitialBalance(BaseModel):
    """IB data (letters A+B, 09:30-10:30 ET)."""
    high: Optional[float] = None
    low: Optional[float] = None
    width: Optional[float] = None
    classification: Optional[IBWidth] = None
    locked: bool = False


class POCMigration(BaseModel):
    """POC migration tracking (Stage C6)."""
    history: List[float] = []       # POC price per letter
    velocity: float = 0.0           # pts per letter
    stuck_count: int = 0            # letters at same price
    distance_from_open: float = 0.0
    pattern: MigrationPattern = MigrationPattern.ROTATIONAL


class OpeningBehavior(BaseModel):
    """Stage B: opening behavior 09:30-09:45 ET."""
    open_price: Optional[float] = None
    open_vs_pd_va: Optional[str] = None    # INSIDE, AT_EDGE, OUT_VA, OUT_RANGE
    gap_size_pts: float = 0.0
    direction_5min: Optional[str] = None
    distance_pts: float = 0.0
    reversal_detected: bool = False
    behavior_type: str = "UNKNOWN"
    classification: str = "UNKNOWN"


class TPOProfile(BaseModel):
    """Full TPO profile state — the main output of System 5."""
    # Session
    session_state: SessionState = SessionState.PRE_OPEN
    data_quality: str = "OK"  # OK or DEGRADED

    # Map
    current_letter: str = "A"
    letter_count: int = 0
    levels: Dict[str, TPOLevel] = {}  # price_key → TPOLevel

    # Levels (SG1=POC, SG2=VAH, SG3=VAL — 1-indexed per ACSIL)
    poc: Optional[float] = None
    poc_vol: int = 0
    vah: Optional[float] = None
    val: Optional[float] = None
    session_high: Optional[float] = None
    session_low: Optional[float] = None

    # IB
    ib: InitialBalance = Field(default_factory=InitialBalance)

    # Features (Stages C4-C7)
    single_prints: List[float] = []
    buying_tail_count: int = 0
    selling_tail_count: int = 0
    poc_migration: POCMigration = Field(default_factory=POCMigration)

    # Opening behavior (Stage B)
    opening: OpeningBehavior = Field(default_factory=OpeningBehavior)

    # Classification (Stage D)
    shape: Optional[ProfileShape] = None
    shape_confidence: float = 0.0
    shape_locked: bool = False

    # Volume nodes (Stage D3-D4)
    hvn_prices: List[float] = []
    lvn_prices: List[float] = []
    naked_pocs: List[float] = []
    naked_poc_touched_today: List[float] = []
    naked_poc_status: Dict[str, str] = {}
    incomplete_letters: List[str] = []

    # Intent (Stage E)
    intent: Intent = Intent.NONE
    otf_clarity: OTFClarity = OTFClarity.UNCLEAR
    migration_pattern: MigrationPattern = MigrationPattern.ROTATIONAL


class TPOLevels(BaseModel):
    """Lightweight levels output for WebSocket /ws/v9/levels."""
    poc: Optional[float] = None
    vah: Optional[float] = None
    val: Optional[float] = None
    session_high: Optional[float] = None
    session_low: Optional[float] = None
    ib_high: Optional[float] = None
    ib_low: Optional[float] = None
    naked_pocs: List[float] = []
    hvn_prices: List[float] = []
    lvn_prices: List[float] = []
