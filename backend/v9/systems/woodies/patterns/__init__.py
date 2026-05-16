"""Woodies CCI pattern detectors -- 4 continuation + 4 reversal.

Two interfaces:
  1. New: detect(bars: list[WoodiesBar], context) -> PatternResult
  2. Legacy: detect_<name>(cci_history, bar_index, ts, **kwargs) -> PatternSignal
"""

from .zlr import detect_zlr, detect as detect_zlr_v2
from .tlb import detect_tlb, detect as detect_tlb_v2
from .tt import detect_tt, detect as detect_tt_v2
from .gb100 import detect_gb100, detect as detect_gb100_v2
from .vegas import detect_vegas, detect as detect_vegas_v2
from .ghost import detect_ghost, detect as detect_ghost_v2
from .famir import detect_famir, detect as detect_famir_v2
from .htlb import detect_htlb, detect as detect_htlb_v2
from .hfe import detect as detect_hfe_v2

# Legacy list (used by detector.py)
ALL_DETECTORS = [
    detect_zlr,
    detect_tlb,
    detect_tt,
    detect_gb100,
    detect_vegas,
    detect_ghost,
    detect_famir,
    detect_htlb,
]

# New WoodiesBar-based detectors (9 patterns — HFE added per Decision Tree V1)
ALL_PATTERN_DETECTORS = [
    detect_zlr_v2,
    detect_tlb_v2,
    detect_tt_v2,
    detect_gb100_v2,
    detect_vegas_v2,
    detect_ghost_v2,
    detect_famir_v2,
    detect_htlb_v2,
    detect_hfe_v2,
]

__all__ = [
    "detect_zlr", "detect_tlb", "detect_tt", "detect_gb100",
    "detect_vegas", "detect_ghost", "detect_famir", "detect_htlb",
    "detect_hfe_v2",
    "ALL_DETECTORS", "ALL_PATTERN_DETECTORS",
]
