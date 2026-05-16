"""Woodies CCI unified pattern detection -- 8 CCI pattern detectors.

Entry point: detect_all_patterns(bars, context) -> list[PatternResult]

8 patterns:
  Continuation (Group A): ZLR, TLB, TT, GB100
  Reversal (Group B):     VEGAS, GHOST, FAMIR, HTLB

Each pattern uses CCI-14, TCCI (CCI-6), and optionally EMA-34
from Woodies methodology per MEMS26_WOODIES_SPEC_V1_DERIVED.
"""

from typing import List, Optional

from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult
from backend.v9.systems.woodies.patterns import zlr, tlb, tt, gb100
from backend.v9.systems.woodies.patterns import vegas, ghost, famir, htlb, hfe

# All 9 detector functions: detect(bars, context) -> PatternResult
_DETECTORS = [
    zlr.detect,
    tlb.detect,
    tt.detect,
    gb100.detect,
    vegas.detect,
    ghost.detect,
    famir.detect,
    htlb.detect,
    hfe.detect,
]

PATTERN_IDS = ["ZLR", "TLB", "TT", "GB100", "VEGAS", "GHOST", "FAMIR", "HTLB", "HFE"]
CONTINUATION_PATTERNS = {"ZLR", "TLB", "TT", "GB100"}
REVERSAL_PATTERNS = {"VEGAS", "GHOST", "FAMIR", "HTLB", "HFE"}


def detect_all_patterns(
    bars: List[WoodiesBar],
    context: Optional[dict] = None,
) -> List[PatternResult]:
    """Run all 8 pattern detectors on the bar history.

    Args:
        bars: List of WoodiesBar objects (oldest first).
        context: Optional dict with additional context (e.g. session info).

    Returns:
        List of PatternResult where detected=True. Empty list if none found.
    """
    if not bars or len(bars) < 3:
        return []

    results = []
    for detector in _DETECTORS:
        result = detector(bars, context)
        if result is not None and result.detected:
            results.append(result)

    return results
