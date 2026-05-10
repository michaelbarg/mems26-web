"""HTLB (Horizontal Trend Line Break) — Reversal pattern.

CCI breaks through a horizontal support/resistance level formed by
multiple touches at approximately the same CCI value.
"""

from typing import Optional, List
from backend.v9.systems.woodies.schemas import PatternSignal

LOOKBACK = 15
TOUCH_TOLERANCE = 15  # CCI points
MIN_TOUCHES = 2


def _find_horizontal_level(values: List[float], kind: str = "resistance") -> Optional[float]:
    """Find a horizontal level with multiple touches."""
    if len(values) < 5:
        return None

    # Find local extremes
    extremes = []
    for i in range(1, len(values) - 1):
        if kind == "resistance":
            if values[i] >= values[i - 1] and values[i] >= values[i + 1]:
                extremes.append(values[i])
        else:
            if values[i] <= values[i - 1] and values[i] <= values[i + 1]:
                extremes.append(values[i])

    if len(extremes) < MIN_TOUCHES:
        return None

    # Check if recent extremes cluster around a level
    for level in extremes[-3:]:
        touches = sum(1 for e in extremes if abs(e - level) <= TOUCH_TOLERANCE)
        if touches >= MIN_TOUCHES:
            return level

    return None


def detect_htlb(cci_history: list, bar_index: int, ts: float,
                **kwargs) -> Optional[PatternSignal]:
    n = len(cci_history)
    if n < LOOKBACK:
        return None

    window = cci_history[-LOOKBACK:]
    current = window[-1]
    prev = window[-2]

    # HTLB UP: break above resistance
    resistance = _find_horizontal_level(window[:-1], "resistance")
    if resistance is not None and prev <= resistance and current > resistance + 5:
        return PatternSignal(
            pattern="HTLB", group="REVERSAL", direction="LONG",
            confidence=0.65,
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"level": round(resistance, 2),
                     "break_amount": round(current - resistance, 2)},
        )

    # HTLB DOWN: break below support
    support = _find_horizontal_level(window[:-1], "support")
    if support is not None and prev >= support and current < support - 5:
        return PatternSignal(
            pattern="HTLB", group="REVERSAL", direction="SHORT",
            confidence=0.65,
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"level": round(support, 2),
                     "break_amount": round(current - support, 2)},
        )

    return None
