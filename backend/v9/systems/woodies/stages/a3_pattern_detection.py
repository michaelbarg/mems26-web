"""Stage A3 — Pattern Detection (PROMPT 3 · 3.2).

Purpose: Detect if any of the 9 Woodies patterns is currently triggered.
Reference: Decision Tree V1 § Section 4 · A3
Type: Woodies Core (independent decision)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from backend.v9.systems.woodies.pattern_engine import (
    CONTINUATION_PATTERNS,
    REVERSAL_PATTERNS,
    detect_all_patterns,
)
from backend.v9.systems.woodies.schemas import WoodiesBar


@dataclass
class A3Output:
    """A3 stage output."""
    pattern_matched: str  # pattern ID or "NONE"
    pattern_category: str  # "TREND_CONFIRMING" | "NEW_TREND" | "NONE"
    pattern_direction: str  # "LONG" | "SHORT" | "NONE"


class A3PatternDetection:
    """Stage A3 — Pattern Detection.

    Scans all 9 patterns via pattern_engine.detect_all_patterns():
      Trend-Confirming (require BLUE/RED): ZLR, TT, TLB, GB100
      New-Trend (require color transition): VEGAS, GHOST, FAMIR, HTLB, HFE

    Returns first detected pattern (highest priority by engine order).
    Terminal states: WAIT (no pattern matched)
    """

    def evaluate(
        self,
        bars: Optional[List[WoodiesBar]] = None,
        color: Optional[str] = None,
        context: Optional[Dict] = None,
        # Legacy params kept for backward compat with scaffold tests
        cci_14_history: Optional[List[float]] = None,
        cci_zero_line_distance: float = 0.0,
        cci_extremes: Optional[Dict] = None,
        cci_trend_lines: Optional[Dict] = None,
        ema_13_34_89_state: Optional[Dict] = None,
    ) -> A3Output:
        """Evaluate pattern detection per Decision Tree V1 § A3.

        Uses pattern_engine.detect_all_patterns() on WoodiesBar history.
        Filters by color compatibility:
          TREND_CONFIRMING requires BLUE or RED
          NEW_TREND patterns allowed in any color state
        """
        if not bars or len(bars) < 3:
            return A3Output(
                pattern_matched="NONE",
                pattern_category="NONE",
                pattern_direction="NONE",
            )

        results = detect_all_patterns(bars, context)

        if not results:
            return A3Output(
                pattern_matched="NONE",
                pattern_category="NONE",
                pattern_direction="NONE",
            )

        # Filter by color compatibility if color is provided
        for result in results:
            pid = result.pattern_id
            is_continuation = pid in CONTINUATION_PATTERNS
            is_reversal = pid in REVERSAL_PATTERNS

            # Trend-confirming patterns require established color (BLUE/RED)
            if is_continuation and color not in ("BLUE", "RED", None):
                continue

            category = "TREND_CONFIRMING" if is_continuation else "NEW_TREND"
            direction = result.direction if result.direction != "NEUTRAL" else "NONE"

            return A3Output(
                pattern_matched=pid,
                pattern_category=category,
                pattern_direction=direction,
            )

        return A3Output(
            pattern_matched="NONE",
            pattern_category="NONE",
            pattern_direction="NONE",
        )
