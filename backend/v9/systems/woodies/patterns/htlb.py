"""HTLB (Hook Turn at Line Break) -- Reversal pattern.

CCI hooks at a trendline break point. Specifically, CCI breaks through
a horizontal support/resistance level formed by multiple touches at
the same CCI value (within tolerance).

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (B4).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal

LOOKBACK = 15
TOUCH_TOLERANCE = 15  # CCI points
MIN_TOUCHES = 2
PATTERN_ID = "HTLB"
GROUP = "REVERSAL"
TICK_SIZE = 0.25
STOP_TICKS = 10
TARGET1_TICKS = 14
TARGET2_TICKS = 28


def _find_horizontal_level(values: List[float], kind: str = "resistance") -> Optional[float]:
    """Find a horizontal level with multiple touches."""
    if len(values) < 5:
        return None

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

    for level in extremes[-3:]:
        touches = sum(1 for e in extremes if abs(e - level) <= TOUCH_TOLERANCE)
        if touches >= MIN_TOUCHES:
            return level

    return None


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect HTLB pattern from WoodiesBar list."""
    if len(bars) < LOOKBACK:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    window = [b.cci_14 for b in bars[-LOOKBACK:]]
    bar = bars[-1]
    current = window[-1]
    prev = window[-2]

    # HTLB UP: break above resistance
    resistance = _find_horizontal_level(window[:-1], "resistance")
    if resistance is not None and prev <= resistance and current > resistance + 5:
        entry = bar.close
        stop = entry - STOP_TICKS * TICK_SIZE
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            direction="LONG",
            confidence=0.65,
            entry_price=entry,
            stop=stop,
            targets=[
                entry + TARGET1_TICKS * TICK_SIZE,
                entry + TARGET2_TICKS * TICK_SIZE,
            ],
            group=GROUP,
            cci_at_signal=current,
            bar_index=len(bars) - 1,
            ts=bar.ts,
            details={"level": round(resistance, 2),
                     "break_amount": round(current - resistance, 2)},
        )

    # HTLB DOWN: break below support
    support = _find_horizontal_level(window[:-1], "support")
    if support is not None and prev >= support and current < support - 5:
        entry = bar.close
        stop = entry + STOP_TICKS * TICK_SIZE
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            direction="SHORT",
            confidence=0.65,
            entry_price=entry,
            stop=stop,
            targets=[
                entry - TARGET1_TICKS * TICK_SIZE,
                entry - TARGET2_TICKS * TICK_SIZE,
            ],
            group=GROUP,
            cci_at_signal=current,
            bar_index=len(bars) - 1,
            ts=bar.ts,
            details={"level": round(support, 2),
                     "break_amount": round(current - support, 2)},
        )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_htlb(cci_history: list, bar_index: int, ts: float,
                **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    n = len(cci_history)
    if n < LOOKBACK:
        return None

    window = cci_history[-LOOKBACK:]
    current = window[-1]
    prev = window[-2]

    resistance = _find_horizontal_level(window[:-1], "resistance")
    if resistance is not None and prev <= resistance and current > resistance + 5:
        return PatternSignal(
            pattern="HTLB", group="REVERSAL", direction="LONG",
            confidence=0.65,
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"level": round(resistance, 2),
                     "break_amount": round(current - resistance, 2)},
        )

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
