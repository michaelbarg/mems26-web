"""Pydantic schemas for Woodies CCI data."""

from typing import Optional, List
from pydantic import BaseModel


class WoodiesBar(BaseModel):
    """Single 30-min bar with all 11 studies computed."""
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


class PatternSignal(BaseModel):
    """A detected Woodies pattern."""
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
