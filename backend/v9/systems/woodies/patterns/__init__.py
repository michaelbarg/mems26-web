"""Woodies CCI pattern detectors — 4 continuation + 4 reversal."""

from .zlr import detect_zlr
from .tlb import detect_tlb
from .tt import detect_tt
from .gb100 import detect_gb100
from .vegas import detect_vegas
from .ghost import detect_ghost
from .famir import detect_famir
from .htlb import detect_htlb

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

__all__ = [
    "detect_zlr", "detect_tlb", "detect_tt", "detect_gb100",
    "detect_vegas", "detect_ghost", "detect_famir", "detect_htlb",
    "ALL_DETECTORS",
]
