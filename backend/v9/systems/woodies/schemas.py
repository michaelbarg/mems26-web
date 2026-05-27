"""Pydantic schemas for Woodies CCI data."""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class PatternId(str, Enum):
    """All 9 Woodies CCI patterns per Decision Tree V1."""
    ZLR = "ZLR"
    TLB = "TLB"
    TT = "TT"
    GB100 = "GB100"
    VEGAS = "VEGAS"
    GHOST = "GHOST"
    FAMIR = "FAMIR"
    HTLB = "HTLB"
    HFE = "HFE"


class WoodiesBar(BaseModel):
    """Single 30-min bar with all 11 studies computed.

    Fields o/h/l/c/vol are aliases for open/high/low/close/volume
    to support both flat and nested OHLC formats from the DLL JSON.
    """
    ts: float
    open: float
    high: float
    low: float
    close: float
    volume: float = 0
    cci_14: float = 0
    cci_6_tcci: float = 0
    ema_34: float = 0
    lsma_value: float = 0
    lsma_above_price: bool = False
    swi_value: float = 0
    czi_value: float = 0
    trend_state: str = "GRAY"
    predictor_next_cci: float = 0
    zlr_detected: bool = False
    zlr_direction: str = "NONE"
    hfe_detected: bool = False
    hfe_direction: str = "NONE"
    hfe_extreme_bars_ago: int = 0

    @property
    def o(self) -> float:
        return self.open

    @property
    def h(self) -> float:
        return self.high

    @property
    def l(self) -> float:
        return self.low

    @property
    def c(self) -> float:
        return self.close

    @property
    def vol(self) -> float:
        return self.volume


class PatternResult(BaseModel):
    """Result of a pattern detection — includes trading fields."""
    detected: bool
    pattern_id: str         # ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE
    direction: str = "NEUTRAL"  # LONG, SHORT, NEUTRAL
    confidence: float = 0.0     # 0.0-1.0
    raw_confidence: Optional[float] = None  # alias — same value as confidence
    r_t1: Optional[float] = None  # R_t1 = (t1 - entry) / (entry - stop), always positive
    entry_price: float = 0.0
    stop: float = 0.0
    targets: List[float] = []
    group: str = ""             # CONTINUATION or REVERSAL
    cci_at_signal: float = 0.0
    bar_index: int = 0
    ts: float = 0.0
    details: Optional[dict] = None


class PatternSignal(BaseModel):
    """A detected Woodies pattern (legacy interface)."""
    pattern: str           # ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB
    group: str             # CONTINUATION or REVERSAL
    direction: str         # LONG or SHORT
    confidence: float      # 0.0-1.0
    cci_at_signal: float
    bar_index: int
    ts: float
    details: Optional[dict] = None


class WoodiesState(BaseModel):
    """Current state of the Woodies system."""
    trend_state: str
    cci_14: float
    cci_6_tcci: float
    swi_value: float
    czi_value: float
    ema_34: float
    lsma_value: float
    predictor_next_cci: float
    active_patterns: List[PatternSignal] = []
    classification: str = "NO_SETUP"  # NO_SETUP, TACTICAL, STRATEGIC
    direction: str = "NEUTRAL"        # LONG, SHORT, NEUTRAL
