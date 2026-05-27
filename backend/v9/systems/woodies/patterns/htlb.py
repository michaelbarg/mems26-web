"""HTLB (Hook Turn at Line Break) -- Reversal pattern.

CCI hooks at a trendline break point. Specifically, CCI breaks through
a horizontal support/resistance level formed by multiple touches at
the same CCI value (within tolerance).

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (B4).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal
from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker
from backend.v9.systems.woodies.atr_stop import compute_stop, PatternGroup

LOOKBACK = 15
TOUCH_TOLERANCE = 15  # CCI points
MIN_TOUCHES = 2
PATTERN_ID = "HTLB"
GROUP = "REVERSAL"
_PATTERN_GROUP = PatternGroup.CONT_MED
TICK_SIZE = 0.25
STOP_TICKS = 10
TARGET1_TICKS = 14
TARGET2_TICKS = 28
_T1_TICKS = 4


def _compute_atr14_ticks(bars: List[WoodiesBar], tick_size: float = TICK_SIZE) -> float:
    if len(bars) < 14:
        return 0.0
    trs = []
    for i, bar in enumerate(bars):
        if i == 0:
            trs.append(bar.high - bar.low)
        else:
            prev_c = bars[i - 1].close
            trs.append(max(bar.high - bar.low, abs(bar.high - prev_c), abs(bar.low - prev_c)))
    atr = sum(trs[:14]) / 14
    for tr in trs[14:]:
        atr = ((atr * 13) + tr) / 14
    return atr / tick_size


def _compute_r_t1(entry_price: float, stop_price: float,
                  tick_size: float = TICK_SIZE, t1_ticks: int = _T1_TICKS) -> Optional[float]:
    risk = abs(entry_price - stop_price)
    if risk < 1e-9:
        return None
    return (t1_ticks * tick_size) / risk


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

    # ── AP8: universal CCI flat check ──
    ap8 = AntiPatternChecker.check_ap8_cci_flat(bars)
    if ap8.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap8.reason})

    window = [b.cci_14 for b in bars[-LOOKBACK:]]
    bar = bars[-1]
    current = window[-1]
    prev = window[-2]

    # HTLB UP: break above resistance
    resistance = _find_horizontal_level(window[:-1], "resistance")
    if resistance is not None and prev <= resistance and current > resistance + 5:
        # ── AP4: formalize MIN_TOUCHES check ──
        _extremes_r = [v for i in range(1, len(window) - 2)
                       if (v := window[i]) >= window[i - 1] and v >= window[i + 1]]
        _touches_r = sum(1 for e in _extremes_r if abs(e - resistance) <= TOUCH_TOLERANCE)
        ap4 = AntiPatternChecker.check_ap4_htlb_touches(bars, _touches_r)
        if ap4.blocked:
            return PatternResult(detected=False, pattern_id=PATTERN_ID,
                                 details={"reject_reason": ap4.reason})
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
        r_t1 = _compute_r_t1(entry, stop)
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            direction="LONG",
            confidence=0.65,
            raw_confidence=0.65,
            r_t1=r_t1,
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
                     "break_amount": round(current - resistance, 2),
                     "stop_layer_applied": stop_layer},
        )

    # HTLB DOWN: break below support
    support = _find_horizontal_level(window[:-1], "support")
    if support is not None and prev >= support and current < support - 5:
        # ── AP4: formalize MIN_TOUCHES check ──
        _extremes_s = [v for i in range(1, len(window) - 2)
                       if (v := window[i]) <= window[i - 1] and v <= window[i + 1]]
        _touches_s = sum(1 for e in _extremes_s if abs(e - support) <= TOUCH_TOLERANCE)
        ap4 = AntiPatternChecker.check_ap4_htlb_touches(bars, _touches_s)
        if ap4.blocked:
            return PatternResult(detected=False, pattern_id=PATTERN_ID,
                                 details={"reject_reason": ap4.reason})
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
        r_t1 = _compute_r_t1(entry, stop)
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            direction="SHORT",
            confidence=0.65,
            raw_confidence=0.65,
            r_t1=r_t1,
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
                     "break_amount": round(current - support, 2),
                     "stop_layer_applied": stop_layer},
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
