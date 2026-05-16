"""First Hour Buffer state machine — Tree V3.3 §Stage B.

Dynamic bar count 4-12:
  Bars 1-3: ACCUMULATING (no patterns eligible)
  Bars 4-6: REACTIVE eligible only
  Bars 7-9: REACTIVE + INITIATIVE eligible
  Bars 10-12: ALL patterns + full sizing
  Bar 13+: Buffer complete → Day Type Mode takes over at 10:30

Pattern eligibility by bar count enforces conservative early behavior.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Set


class BufferState(str, Enum):
    ACCUMULATING = "ACCUMULATING"   # bars 1-3, no patterns
    EARLY = "EARLY"                 # bars 4-6, reactive only
    DEVELOPING = "DEVELOPING"       # bars 7-9, reactive + initiative
    MATURE = "MATURE"               # bars 10-12, all patterns
    COMPLETE = "COMPLETE"           # bar 13+, buffer done


ELIGIBLE_PATTERNS: dict = {
    BufferState.ACCUMULATING: set(),
    BufferState.EARLY: {"REACTIVE_LONG", "REACTIVE_SHORT"},
    BufferState.DEVELOPING: {"REACTIVE_LONG", "REACTIVE_SHORT", "INITIATIVE_LONG", "INITIATIVE_SHORT"},
    BufferState.MATURE: {"REACTIVE_LONG", "REACTIVE_SHORT", "INITIATIVE_LONG", "INITIATIVE_SHORT"},
    BufferState.COMPLETE: {"REACTIVE_LONG", "REACTIVE_SHORT", "INITIATIVE_LONG", "INITIATIVE_SHORT"},
}


class FirstHourBuffer:
    """Tracks bar count in First Hour and determines pattern eligibility."""

    def __init__(self):
        self._bar_count: int = 0
        self._state: BufferState = BufferState.ACCUMULATING

    @property
    def bar_count(self) -> int:
        return self._bar_count

    @property
    def state(self) -> BufferState:
        return self._state

    @property
    def eligible_patterns(self) -> Set[str]:
        return ELIGIBLE_PATTERNS[self._state]

    def on_bar(self) -> BufferState:
        """Advance buffer by one bar. Returns new state."""
        self._bar_count += 1
        self._update_state()
        return self._state

    def is_pattern_eligible(self, pattern_name: str) -> bool:
        """Check if a pattern is eligible at current bar count."""
        return pattern_name in self.eligible_patterns

    def reset(self):
        """Reset for new session."""
        self._bar_count = 0
        self._state = BufferState.ACCUMULATING

    def _update_state(self):
        if self._bar_count <= 3:
            self._state = BufferState.ACCUMULATING
        elif self._bar_count <= 6:
            self._state = BufferState.EARLY
        elif self._bar_count <= 9:
            self._state = BufferState.DEVELOPING
        elif self._bar_count <= 12:
            self._state = BufferState.MATURE
        else:
            self._state = BufferState.COMPLETE
