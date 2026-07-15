"""T1Setup — canonical output per D-041.

Constitution V3 §Part 6 · Per-System Decision Maker Principle.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


PatternName = Literal[
    'REACTIVE_LONG', 'REACTIVE_SHORT',
    'INITIATIVE_LONG', 'INITIATIVE_SHORT',
    'INVERSE_HNS_LONG', 'HNS_TOP_SHORT',
    'DOUBLE_BOTTOM_EE_LONG', 'DOUBLE_TOP_AA_SHORT',
    'BULL_FLAG_LONG', 'BEAR_FLAG_SHORT',
]


class T1Setup(BaseModel):
    """Canonical T1 setup output."""
    system_id: Literal['T1_NUMBER_BAR'] = 'T1_NUMBER_BAR'
    pattern_name: PatternName
    direction: Literal['LONG', 'SHORT']

    # Prices · per Constitution V3 §Layer 3 cluster-based (Wave 2 wires properly)
    entry_price: float = Field(gt=0)
    stop_price: float = Field(gt=0)
    t1_price: float = Field(gt=0)
    t2_price: float = Field(gt=0)
    t3_price: Optional[float] = Field(default=None, gt=0)
    time_stop_minutes: Optional[int] = Field(default=None, ge=1, le=180)
    confidence: int = Field(ge=0, le=100)

    # Pkg 3c · contract split (per D-091 §Contract Distribution)
    t1_pct: float = Field(ge=0.0, le=1.0, default=0.0)
    t2_pct: float = Field(ge=0.0, le=1.0, default=0.0)
    t3_pct: float = Field(ge=0.0, le=1.0, default=0.0)

    # Bar context
    bar_index: int = Field(ge=0)
    fired_at: datetime

    # Quality metadata (filled by Wave 2 wiring)
    quality_tier: Literal['HIGH', 'MEDIUM', 'LOW'] = 'MEDIUM'
    sizing_contracts: int = Field(ge=0, le=4, default=2)

    # Provisional flag — True when Layer 3 cluster/empty-zone not yet integrated
    provisional: bool = True
    provisional_reason: Optional[str] = None
