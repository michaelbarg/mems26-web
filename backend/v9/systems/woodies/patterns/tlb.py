"""TLB (Trend Line Break) -- Continuation pattern.

CCI breaks through a trendline drawn along recent CCI swing points.
Detection: linear regression on CCI over lookback window; break when
current CCI deviates significantly from projected trendline.

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (A2).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal
from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker
from backend.v9.systems.woodies.atr_stop import compute_stop, PatternGroup

LOOKBACK = 10
PATTERN_ID = "TLB"
GROUP = "CONTINUATION"
_PATTERN_GROUP = PatternGroup.CONT_TIGHT
TICK_SIZE = 0.25
STOP_TICKS = 10
TARGET1_TICKS = 15
TARGET2_TICKS = 30
_T1_TICKS = 4


def _compute_atr14_ticks(bars: List[WoodiesBar], tick_size: float = TICK_SIZE) -> float:
    """Compute ATR-14 from bars in ticks."""
    if len(bars) < 14:
        return 0.0
    trs = []
    for i, bar in enumerate(bars):
        if i == 0:
            trs.append(bar.high - bar.low)
        else:
            prev_c = bars[i - 1].close
            tr = max(bar.high - bar.low, abs(bar.high - prev_c), abs(bar.low - prev_c))
            trs.append(tr)
    atr = sum(trs[:14]) / 14
    for tr in trs[14:]:
        atr = ((atr * 13) + tr) / 14
    return atr / tick_size


def _compute_r_t1(entry_price: float, stop_price: float, direction: str,
                  tick_size: float = TICK_SIZE, t1_ticks: int = _T1_TICKS) -> Optional[float]:
    """Compute R_t1. Always positive."""
    risk = abs(entry_price - stop_price)
    if risk < 1e-9:
        return None
    return (t1_ticks * tick_size) / risk


def _linreg_slope(values: List[float]) -> tuple:
    """Linear regression slope and intercept over values."""
    n = len(values)
    sum_x = sum_y = sum_xy = sum_x2 = 0.0
    for i in range(n):
        sum_x += i
        sum_y += values[i]
        sum_xy += i * values[i]
        sum_x2 += i * i
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 0.001:
        return 0.0, 0.0
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect TLB pattern from WoodiesBar list."""
    n = len(bars)
    if n < LOOKBACK:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    # ── AP8: universal CCI flat check ──
    ap8 = AntiPatternChecker.check_ap8_cci_flat(bars)
    if ap8.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap8.reason})

    window = [b.cci_14 for b in bars[-LOOKBACK:]]
    current = window[-1]
    prev = window[-2]
    bar = bars[-1]

    slope, intercept = _linreg_slope(window)
    predicted = intercept + slope * (LOOKBACK - 1)

    # TLB UP: downward trendline broken upward
    if slope < -2 and current > predicted + 10 and current > prev:
        entry = bar.close
        atr_ticks = _compute_atr14_ticks(bars)
        if atr_ticks > 0:
            stop_result = compute_stop(
                direction="LONG", entry_bar=bar, swing_anchor=None,
                pattern_group=_PATTERN_GROUP, atr_14=atr_ticks, tick_size=TICK_SIZE,
            )
            stop = stop_result.stop_price
            stop_layer = stop_result.layer_applied
        else:
            stop = entry - STOP_TICKS * TICK_SIZE
            stop_layer = "primary"
        r_t1 = _compute_r_t1(entry, stop, "LONG")
        conf = min(0.85, 0.4 + abs(current - predicted) / 200)
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            direction="LONG",
            confidence=conf,
            raw_confidence=conf,
            r_t1=r_t1,
            entry_price=entry,
            stop=stop,
            targets=[
                entry + TARGET1_TICKS * TICK_SIZE,
                entry + TARGET2_TICKS * TICK_SIZE,
            ],
            group=GROUP,
            cci_at_signal=current,
            bar_index=n - 1,
            ts=bar.ts,
            details={"slope": round(slope, 2), "break_amount": round(current - predicted, 2),
                     "stop_layer_applied": stop_layer},
        )

    # TLB DOWN: upward trendline broken downward
    if slope > 2 and current < predicted - 10 and current < prev:
        entry = bar.close
        atr_ticks = _compute_atr14_ticks(bars)
        if atr_ticks > 0:
            stop_result = compute_stop(
                direction="SHORT", entry_bar=bar, swing_anchor=None,
                pattern_group=_PATTERN_GROUP, atr_14=atr_ticks, tick_size=TICK_SIZE,
            )
            stop = stop_result.stop_price
            stop_layer = stop_result.layer_applied
        else:
            stop = entry + STOP_TICKS * TICK_SIZE
            stop_layer = "primary"
        r_t1 = _compute_r_t1(entry, stop, "SHORT")
        conf = min(0.85, 0.4 + abs(current - predicted) / 200)
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            direction="SHORT",
            confidence=conf,
            raw_confidence=conf,
            r_t1=r_t1,
            entry_price=entry,
            stop=stop,
            targets=[
                entry - TARGET1_TICKS * TICK_SIZE,
                entry - TARGET2_TICKS * TICK_SIZE,
            ],
            group=GROUP,
            cci_at_signal=current,
            bar_index=n - 1,
            ts=bar.ts,
            details={"slope": round(slope, 2), "break_amount": round(current - predicted, 2),
                     "stop_layer_applied": stop_layer},
        )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_tlb(cci_history: list, bar_index: int, ts: float,
               **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    n = len(cci_history)
    if n < LOOKBACK:
        return None

    window = cci_history[-LOOKBACK:]
    current = window[-1]
    prev = window[-2]

    slope, intercept = _linreg_slope(window)
    predicted = intercept + slope * (LOOKBACK - 1)

    if slope < -2 and current > predicted + 10 and current > prev:
        return PatternSignal(
            pattern="TLB", group="CONTINUATION", direction="LONG",
            confidence=min(0.85, 0.4 + abs(current - predicted) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"slope": round(slope, 2), "break_amount": round(current - predicted, 2)},
        )

    if slope > 2 and current < predicted - 10 and current < prev:
        return PatternSignal(
            pattern="TLB", group="CONTINUATION", direction="SHORT",
            confidence=min(0.85, 0.4 + abs(current - predicted) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"slope": round(slope, 2), "break_amount": round(current - predicted, 2)},
        )

    return None
