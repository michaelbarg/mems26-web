"""System 3: Tick Reversal + Footprint Observer.

STANDALONE — monitors, marks, logs. NEVER fires trades.
Color: #d2a8ff (purple).

5 patterns: Accumulation+Breakout, V-Shape, Failed Test, Stair-step, Compression+Pop
10 signals: 5 Zohar + 5 Industry
3 classifications: NO_SETUP, TACTICAL, STRATEGIC
"""

from .detector import TickReversalDetector
from .schemas import (
    TickReversalConfig, BarInput, BarAnalysis,
    MicroPatternResult, SignalResult,
)
from .signal_engine import detect_all_signals
from .micro_patterns import detect_all_micro_patterns

__all__ = [
    "TickReversalDetector",
    "TickReversalConfig",
    "BarInput",
    "BarAnalysis",
    "MicroPatternResult",
    "SignalResult",
    "detect_all_signals",
    "detect_all_micro_patterns",
]
