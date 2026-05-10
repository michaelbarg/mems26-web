"""Signal detectors for tick_reversal observer.

10 signal detectors organized as:
- 5 Zohar signals (Zohar's proprietary methodology)
- 5 Industry signals (standard order-flow metrics)

Each detector: evaluate(bar, bars, footprint_data) -> bool + metadata
"""

from .zohar_signals import (
    detect_belly_comparison,
    detect_volume_drop_90,
    detect_cot_vs_amt,
    detect_tick_breach,
    detect_poc_migration,
)
from .industry_signals import (
    detect_imbalance_250,
    detect_stacked_imbalance,
    detect_cumulative_delta,
    detect_exhaustion,
    detect_liquidity_sweep,
)

ALL_SIGNAL_DETECTORS = [
    ("belly_comparison", detect_belly_comparison),
    ("volume_drop_90", detect_volume_drop_90),
    ("cot_vs_amt", detect_cot_vs_amt),
    ("tick_breach", detect_tick_breach),
    ("poc_migration", detect_poc_migration),
    ("imbalance_250", detect_imbalance_250),
    ("stacked_imbalance", detect_stacked_imbalance),
    ("cumulative_delta", detect_cumulative_delta),
    ("exhaustion", detect_exhaustion),
    ("liquidity_sweep", detect_liquidity_sweep),
]

__all__ = [
    "ALL_SIGNAL_DETECTORS",
    "detect_belly_comparison",
    "detect_volume_drop_90",
    "detect_cot_vs_amt",
    "detect_tick_breach",
    "detect_poc_migration",
    "detect_imbalance_250",
    "detect_stacked_imbalance",
    "detect_cumulative_delta",
    "detect_exhaustion",
    "detect_liquidity_sweep",
]
