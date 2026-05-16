"""Stage B8 — Counter-Pattern Detection (PROMPT 3 · 3.5).

Purpose: Detect counter-patterns that warn of reversal (tighten, not exit).
Reference: Decision Tree V1 § Section 5 · B8
Type: Woodies Core
Priority Class: TIGHTEN
"""

from dataclasses import dataclass
from typing import List, Optional

from backend.v9.systems.woodies.pattern_engine import detect_all_patterns, REVERSAL_PATTERNS
from backend.v9.systems.woodies.schemas import WoodiesBar


@dataclass
class B8Output:
    """B8 stage output."""
    counter_detected: bool
    action: str  # "TIGHTEN_STOP" | "HOLD"
    tighten_destination: Optional[str]  # target level description


# Counter-patterns: reversal patterns in opposite direction
COUNTER_PATTERN_IDS = {"HFE", "TT", "FAMIR"}


class B8CounterPattern:
    """Stage B8 — Counter-Pattern Detection.

    Scans for HFE_against, TT_against, FAMIR_against.
    If detected → TIGHTEN_STOP with destination:
      pre-T1: stop → 50% of T1 distance
      post-T1: stop → entry
      post-T2: stop → T1 level
    Action: TIGHTEN STOP (no close)
    """

    priority_class = "TIGHTEN"

    def evaluate(
        self,
        bars: Optional[List[WoodiesBar]] = None,
        direction: Optional[str] = None,
        t1_hit: bool = False,
        t2_hit: bool = False,
        # Legacy params for scaffold compat
        cci_14_history: Optional[List[float]] = None,
        current_color: Optional[str] = None,
    ) -> B8Output:
        """Evaluate counter-pattern per Decision Tree V1 § B8."""
        if not bars or not direction:
            return B8Output(counter_detected=False, action="HOLD", tighten_destination=None)

        results = detect_all_patterns(bars)
        for result in results:
            if result.pattern_id in COUNTER_PATTERN_IDS:
                # Check if pattern direction is AGAINST our position
                if direction == "LONG" and result.direction == "SHORT":
                    return self._tighten(t1_hit, t2_hit)
                if direction == "SHORT" and result.direction == "LONG":
                    return self._tighten(t1_hit, t2_hit)

        return B8Output(counter_detected=False, action="HOLD", tighten_destination=None)

    def _tighten(self, t1_hit: bool, t2_hit: bool) -> B8Output:
        """Determine tighten destination based on milestone state."""
        if t2_hit:
            dest = "T1_LEVEL"
        elif t1_hit:
            dest = "ENTRY"
        else:
            dest = "50PCT_T1_DISTANCE"

        return B8Output(counter_detected=True, action="TIGHTEN_STOP", tighten_destination=dest)
