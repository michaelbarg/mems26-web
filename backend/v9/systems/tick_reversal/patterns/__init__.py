"""5 micro-patterns for tick reversal observer (spec Section 6, Step 5)."""

from .accumulation_breakout import detect_accumulation_breakout
from .v_shape_reversal import detect_v_shape_reversal
from .failed_test import detect_failed_test
from .stair_step import detect_stair_step
from .compression_pop import detect_compression_pop

ALL_PATTERNS = [
    ("Accumulation + Breakout", detect_accumulation_breakout),
    ("V-Shape Reversal", detect_v_shape_reversal),
    ("Failed Test", detect_failed_test),
    ("Stair-step", detect_stair_step),
    ("Compression + Pop", detect_compression_pop),
]

__all__ = ["ALL_PATTERNS"]
