"""Internal data models for pattern detection."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Bar:
    """Single 5-min bar with all metrics needed for pattern detection."""
    ts: float = 0.0
    o: float = 0.0
    h: float = 0.0
    l: float = 0.0
    c: float = 0.0
    vol: int = 0
    poc_vol: int = 0
    vah: float = 0.0
    val: float = 0.0
    cumulative_delta: float = 0.0
    belly_buyers: float = 0.0
    belly_sellers: float = 0.0
    poc_price: float = 0.0

    @property
    def is_bullish(self) -> bool:
        return self.c > self.o

    @property
    def is_bearish(self) -> bool:
        return self.c < self.o

    @property
    def body(self) -> float:
        return abs(self.c - self.o)

    @property
    def range(self) -> float:
        return self.h - self.l

    @property
    def mid(self) -> float:
        return (self.h + self.l) / 2


@dataclass
class Pivot:
    """Swing high/low point."""
    index: int
    price: float
    is_high: bool
    bar: Bar


@dataclass
class PatternResult:
    """Result from a pattern detector."""
    detected: bool = False
    pattern_id: str = ""
    group: str = ""
    direction: str = ""         # LONG or SHORT
    completion: float = 0.0
    bar_count: int = 0
    method: str = ""
    potential_r: str = ""
    key_levels: dict = field(default_factory=dict)
    confidence: float = 0.0
    entry_price: float = 0.0
    stop: float = 0.0
    targets: List[float] = field(default_factory=list)


@dataclass
class TierConfig:
    """Configuration for a detection tier."""
    tier: int
    buffer_size: int
    run_every_n_bars: int = 1
    max_ms: int = 10
    patterns: List[str] = field(default_factory=list)


# Tier definitions per V3.1 spec
TIER_1 = TierConfig(
    tier=1, buffer_size=30, run_every_n_bars=1, max_ms=10,
    patterns=[
        "reactive_buyer", "reactive_seller",
        "initiative_buyer", "initiative_seller",
        "bull_flag", "bear_flag",
        "bull_pennant", "bear_pennant",
    ],
)

TIER_2 = TierConfig(
    tier=2, buffer_size=80, run_every_n_bars=1, max_ms=30,
    patterns=[
        "double_bottom", "double_top",
        "ascending_triangle", "descending_triangle",
        "inverse_head_shoulders", "head_shoulders",
        "falling_wedge", "rising_wedge",
        "symmetrical_triangle",
    ],
)

TIER_3 = TierConfig(
    tier=3, buffer_size=200, run_every_n_bars=3, max_ms=100,
    patterns=[
        "cup_handle", "inverse_cup_handle",
        "inverse_head_shoulders", "head_shoulders",
    ],
)

TIER_4 = TierConfig(
    tier=4, buffer_size=500, run_every_n_bars=6, max_ms=300,
    patterns=[],  # Wyckoff phases — future
)

ALL_TIERS = [TIER_1, TIER_2, TIER_3, TIER_4]

# First hour pattern eligibility (V3.3)
FIRST_HOUR_ELIGIBILITY = {
    4: ["reactive_buyer", "reactive_seller", "initiative_buyer", "initiative_seller"],
    6: ["reactive_buyer", "reactive_seller", "initiative_buyer", "initiative_seller",
        "bull_flag", "bear_flag", "bull_pennant", "bear_pennant"],
    10: ["reactive_buyer", "reactive_seller", "initiative_buyer", "initiative_seller",
         "bull_flag", "bear_flag", "bull_pennant", "bear_pennant",
         "double_bottom", "double_top"],
}

# Day types from System 1
DAY_TYPES = [
    "TREND_NORMAL", "TREND_DD", "VARIATION", "NORMAL", "NEUTRAL", "NONTREND",
]

# Opening types from V3.3
OPENING_TYPES = [
    "OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE",
    "OPEN_AUCTION_IN_RANGE", "OPEN_AUCTION_OUT_OF_RANGE",
]
