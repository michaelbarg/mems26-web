"""Tick Reversal / Footprint observer — Pydantic schemas."""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Configuration (12 params from spec Section 5) ──

class TickReversalConfig(BaseModel):
    tick_reversal_size: int = Field(15, ge=10, le=20)
    accumulation_min_bars: int = Field(5, ge=3, le=10)
    accumulation_range_ticks: int = Field(15, ge=10, le=25)
    jumps_required: int = Field(3, ge=2, le=4)
    cluster_poc_threshold_pct: int = Field(30, ge=20, le=50)
    empty_zone_threshold_pct: int = Field(5, ge=2, le=10)
    imbalance_ratio: int = Field(250, ge=200, le=400)
    stacked_imbalance_count: int = Field(3, ge=2, le=5)
    volume_drop_pct: int = Field(90, ge=80, le=95)
    belly_dominance_ratio: float = Field(1.5, ge=1.2, le=2.0)
    confluence_tactical_min: int = Field(4, ge=3, le=5)
    confluence_strategic_min: int = Field(6, ge=5, le=8)


# ── Bar input (from bridge / DLL export) ──

class BarInput(BaseModel):
    ts: str
    o: float
    h: float
    l: float
    c: float
    vol: int = 0
    ask_vol: int = 0
    bid_vol: int = 0
    delta: Optional[float] = None
    dir: Optional[int] = None
    tick_size: int = 15
    footprint: Optional[dict] = None
    cluster: Optional[dict] = None


# ── Analysis sub-results ──

class ClusterResult(BaseModel):
    detected: bool = False
    yellow_poc: Optional[float] = None
    boundaries: Optional[List[float]] = None
    volume_pct: Optional[float] = None


class EmptyZoneResult(BaseModel):
    detected: bool = False
    boundaries: Optional[List[float]] = None
    volume_pct: Optional[float] = None


class ContextResult(BaseModel):
    accumulation_active: bool = False
    accumulation_bars: int = 0
    accumulation_range_ticks: int = 0
    jumps_count: int = 0
    jumps_direction: Optional[str] = None  # "UP" / "DOWN"
    otf_state: int = 4  # 1-4, default 4 = unclear


class ZoharSignals(BaseModel):
    belly_comparison: bool = False
    volume_drop_90: bool = False
    cot_above_amt: bool = False
    tick_breach_ok: bool = False
    poc_jumping: bool = False


class IndustrySignals(BaseModel):
    imbalance_250: bool = False
    stacked_imbalance: bool = False
    cumulative_delta_aligned: bool = False
    exhaustion: bool = False
    liquidity_sweep: bool = False


class ConfluenceResult(BaseModel):
    zohar_count: int = 0
    industry_count: int = 0
    boosters: int = 0
    penalties: int = 0
    total: int = 0


class PatternResult(BaseModel):
    detected: Optional[str] = None
    completion: float = 0.0


# ── Micro-pattern detection result ──

class MicroPatternResult(BaseModel):
    """Result from a single micro-pattern detector."""
    pattern_id: str
    detected: bool = False
    direction: Optional[str] = None  # "LONG" / "SHORT"
    strength: float = 0.0  # 0.0 - 1.0
    trigger_price: Optional[float] = None
    invalidation_price: Optional[float] = None
    metadata: Optional[dict] = None


# ── Signal result (actionable output) ──

class SignalResult(BaseModel):
    """Actionable signal generated from pattern + signal combinations."""
    signal_id: str
    direction: str  # "LONG" / "SHORT"
    confidence: float  # 0.0 - 1.0
    trigger_price: float
    invalidation_price: float
    pattern_ids: List[str] = []
    signal_ids: List[str] = []
    metadata: Optional[dict] = None


# ── Full per-bar journal entry (output) ──

class BarAnalysis(BaseModel):
    ts: str
    bar_id: str
    tick_reversal_size: int = 15
    bar: BarInput
    cluster: ClusterResult = ClusterResult()
    empty_zone: EmptyZoneResult = EmptyZoneResult()
    context: ContextResult = ContextResult()
    pattern: PatternResult = PatternResult()
    signals_zohar: ZoharSignals = ZoharSignals()
    signals_industry: IndustrySignals = IndustrySignals()
    confluence: ConfluenceResult = ConfluenceResult()
    classification: str = "NO_SETUP"
    direction_inferred: Optional[str] = None
    would_be_entry_price: Optional[float] = None
    would_be_stop_price: Optional[float] = None
    stop_distance_ticks: Optional[int] = None
    visual_marker_drawn: bool = False


# ── API response ──

class SignalResponse(BaseModel):
    id: int
    ts: str
    system_id: int = 3
    classification: Optional[str] = None
    direction: Optional[str] = None
    confluence_total: Optional[int] = None
    pattern: Optional[str] = None
    payload: Optional[dict] = None
