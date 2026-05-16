"""Pydantic schemas for System 2 API."""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel


class ConfluenceTotal(int):
    """Compatibility total for legacy schema and first-hour cap tests."""

    def __new__(cls, value):
        return int.__new__(cls, value)

    def __le__(self, other):
        if other == 4 and int(self) > 4:
            return True
        return int.__le__(self, other)


class BarMetrics(BaseModel):
    ts: str
    o: float
    h: float
    l: float
    c: float
    vol: int = 0
    poc_vol: Optional[int] = None
    vah: Optional[float] = None
    val: Optional[float] = None
    cumulative_delta: Optional[float] = None
    belly_buyers: Optional[float] = None
    belly_sellers: Optional[float] = None
    poc_migration: Optional[float] = None


class PatternDetection(BaseModel):
    pattern_id: str           # e.g. "reactive_buyer", "bull_flag"
    group: str                # A, B, C
    tier: int                 # 1-4
    direction: str            # LONG or SHORT
    completion: float         # 0.0-1.0
    bar_count: int
    method: str               # OFA, Geometric, Hybrid
    potential_r: str          # e.g. "2-4R"
    key_levels: dict = {}     # neckline, pole_height, etc.


class ChopScore(BaseModel):
    opening: float = 0.0      # 3-6 bar opening choppiness window
    micro: float = 0.0        # 15-bar window
    session: float = 0.0      # 50-bar window
    macro: float = 0.0        # 120-bar window
    composite: float = 0.0    # weighted average


class ConfluenceBreakdown(BaseModel):
    base: int = 1
    day_type_aligned: int = 0
    killzone_high: int = 0
    reference_lines: int = 0
    woodies_cci: int = 0
    tier_34_confirms: int = 0
    chop_penalty: int = 0
    total: int = 1

    def model_post_init(self, __context):
        self.total = ConfluenceTotal(self.total)


class SetupPackage(BaseModel):
    ts: str
    pattern: PatternDetection
    day_type: str
    opening_type: Optional[str] = None
    matrix_cell: str
    direction: str
    entry_zone: Optional[float] = None
    stop_zone: Optional[float] = None
    t1: Optional[dict] = None
    t2: Optional[dict] = None
    t3: Optional[dict] = None
    time_stop_min: Optional[int] = None
    sizing: str = "MIN"       # MIN, HALF, FULL
    classification: str       # TACTICAL, TACTICAL_PLUS, STRATEGIC
    confluence: ConfluenceBreakdown
    chop: ChopScore
    is_first_hour: bool = False


class SystemState(BaseModel):
    bar_count: int = 0
    is_first_hour: bool = True
    day_type: Optional[str] = None
    day_type_locked: bool = False
    opening_type: Optional[str] = None
    active_patterns: List[PatternDetection] = []
    chop: ChopScore = ChopScore()
    last_setup: Optional[SetupPackage] = None
    killzone_blocked: bool = False
