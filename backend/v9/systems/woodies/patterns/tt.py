"""TT (Turbo CCI Touch) — Continuation pattern.

TCCI (CCI-6) touches or crosses the CCI-14 line during a trend,
then bounces back in the trend direction. Confirms trend strength.
"""

from typing import Optional
from backend.v9.systems.woodies.schemas import PatternSignal


def detect_tt(cci_history: list, bar_index: int, ts: float,
              cci6_history: list = None, trend_state: str = "GRAY",
              **kwargs) -> Optional[PatternSignal]:
    if cci6_history is None or len(cci6_history) < 3 or len(cci_history) < 3:
        return None

    cci14 = cci_history[-1]
    cci14_prev = cci_history[-2]
    cci6 = cci6_history[-1]
    cci6_prev = cci6_history[-2]
    cci6_prev2 = cci6_history[-3]

    # TT LONG: trend BLUE, TCCI touched CCI-14 from above then bounced
    if trend_state == "BLUE" and cci14 > 0:
        touched = (cci6_prev <= cci14_prev + 5)  # TCCI got close to CCI-14
        bounced = (cci6 > cci14 + 5) and (cci6 > cci6_prev)
        was_above = (cci6_prev2 > cci14_prev + 10)
        if touched and bounced and was_above:
            return PatternSignal(
                pattern="TT", group="CONTINUATION", direction="LONG",
                confidence=0.7,
                cci_at_signal=cci14, bar_index=bar_index, ts=ts,
                details={"cci6": round(cci6, 2), "gap": round(cci6 - cci14, 2)},
            )

    # TT SHORT: trend RED, TCCI touched CCI-14 from below then dropped
    if trend_state == "RED" and cci14 < 0:
        touched = (cci6_prev >= cci14_prev - 5)
        bounced = (cci6 < cci14 - 5) and (cci6 < cci6_prev)
        was_below = (cci6_prev2 < cci14_prev - 10)
        if touched and bounced and was_below:
            return PatternSignal(
                pattern="TT", group="CONTINUATION", direction="SHORT",
                confidence=0.7,
                cci_at_signal=cci14, bar_index=bar_index, ts=ts,
                details={"cci6": round(cci6, 2), "gap": round(cci6 - cci14, 2)},
            )

    return None
