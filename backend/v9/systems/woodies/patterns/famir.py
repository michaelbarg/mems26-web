"""FAMIR (Failed Attempt at Major Intermediate Resistance) -- Reversal pattern.

CCI approaches +/-200 but fails to reach or exceed it, then reverses.
Signals exhaustion of the trend at the major resistance/support level.

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (B3).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal

THRESHOLD = 200
NEAR_THRESHOLD = 170  # "approaching" the +/-200 level
PATTERN_ID = "FAMIR"
GROUP = "REVERSAL"
TICK_SIZE = 0.25
STOP_TICKS = 10
TARGET1_TICKS = 14
TARGET2_TICKS = 28


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect FAMIR pattern from WoodiesBar list."""
    if len(bars) < 5:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    bar = bars[-1]
    current = bar.cci_14
    prev = bars[-2].cci_14
    recent = [b.cci_14 for b in bars[-5:]]
    max_recent = max(recent)
    min_recent = min(recent)

    # FAMIR SHORT: CCI approached +200 but failed, now dropping
    if max_recent >= NEAR_THRESHOLD and max_recent < THRESHOLD + 10:
        if current < prev and current < max_recent - 20:
            entry = bar.close
            stop = entry + STOP_TICKS * TICK_SIZE
            return PatternResult(
                detected=True,
                pattern_id=PATTERN_ID,
                direction="SHORT",
                confidence=min(0.8, 0.5 + (THRESHOLD - max_recent) / 100),
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
                details={"peak_cci": round(max_recent, 2),
                         "distance_from_200": round(THRESHOLD - max_recent, 2)},
            )

    # FAMIR LONG: CCI approached -200 but failed, now rising
    if min_recent <= -NEAR_THRESHOLD and min_recent > -(THRESHOLD + 10):
        if current > prev and current > min_recent + 20:
            entry = bar.close
            stop = entry - STOP_TICKS * TICK_SIZE
            return PatternResult(
                detected=True,
                pattern_id=PATTERN_ID,
                direction="LONG",
                confidence=min(0.8, 0.5 + (THRESHOLD - abs(min_recent)) / 100),
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
                details={"trough_cci": round(min_recent, 2),
                         "distance_from_n200": round(THRESHOLD - abs(min_recent), 2)},
            )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_famir(cci_history: list, bar_index: int, ts: float,
                 **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    n = len(cci_history)
    if n < 5:
        return None

    current = cci_history[-1]
    prev = cci_history[-2]
    recent = cci_history[-5:]
    max_recent = max(recent)
    min_recent = min(recent)

    if max_recent >= NEAR_THRESHOLD and max_recent < THRESHOLD + 10:
        if current < prev and current < max_recent - 20:
            return PatternSignal(
                pattern="FAMIR", group="REVERSAL", direction="SHORT",
                confidence=min(0.8, 0.5 + (THRESHOLD - max_recent) / 100),
                cci_at_signal=current, bar_index=bar_index, ts=ts,
                details={"peak_cci": round(max_recent, 2),
                         "distance_from_200": round(THRESHOLD - max_recent, 2)},
            )

    if min_recent <= -NEAR_THRESHOLD and min_recent > -(THRESHOLD + 10):
        if current > prev and current > min_recent + 20:
            return PatternSignal(
                pattern="FAMIR", group="REVERSAL", direction="LONG",
                confidence=min(0.8, 0.5 + (THRESHOLD - abs(min_recent)) / 100),
                cci_at_signal=current, bar_index=bar_index, ts=ts,
                details={"trough_cci": round(min_recent, 2),
                         "distance_from_n200": round(THRESHOLD - abs(min_recent), 2)},
            )

    return None
