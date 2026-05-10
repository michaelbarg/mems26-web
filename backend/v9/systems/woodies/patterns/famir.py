"""FAMIR (Failure At MIR / +/-200) — Reversal pattern.

CCI approaches ±200 but fails to reach or exceed it, then reverses.
Signals exhaustion of the trend.
"""

from typing import Optional
from backend.v9.systems.woodies.schemas import PatternSignal

THRESHOLD = 200
NEAR_THRESHOLD = 170  # "approaching" the ±200 level


def detect_famir(cci_history: list, bar_index: int, ts: float,
                 **kwargs) -> Optional[PatternSignal]:
    n = len(cci_history)
    if n < 5:
        return None

    current = cci_history[-1]
    prev = cci_history[-2]

    # Check recent history for approach to +200
    recent = cci_history[-5:]
    max_recent = max(recent)
    min_recent = min(recent)

    # FAMIR SHORT: CCI approached +200 but failed, now dropping
    if max_recent >= NEAR_THRESHOLD and max_recent < THRESHOLD + 10:
        if current < prev and current < max_recent - 20:
            return PatternSignal(
                pattern="FAMIR", group="REVERSAL", direction="SHORT",
                confidence=min(0.8, 0.5 + (THRESHOLD - max_recent) / 100),
                cci_at_signal=current, bar_index=bar_index, ts=ts,
                details={"peak_cci": round(max_recent, 2),
                         "distance_from_200": round(THRESHOLD - max_recent, 2)},
            )

    # FAMIR LONG: CCI approached -200 but failed, now rising
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
