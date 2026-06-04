"""GHOST -- Reversal pattern (CCI divergence).

CCI forms a head-and-shoulders pattern (three pushes, middle highest/lowest).
Bearish GHOST: CCI makes three peaks, middle highest (head-and-shoulders).
Bullish GHOST: CCI makes three troughs, middle lowest (inverse H&S).

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (B2).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal
from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker
from backend.v9.systems.woodies.atr_stop import compute_stop, PatternGroup

LOOKBACK = 20
PATTERN_ID = "GHOST"
GROUP = "REVERSAL"
_PATTERN_GROUP = PatternGroup.REV
TICK_SIZE = 0.25
from ._pattern_ticks import get_ticks as _get_ticks
_ticks = _get_ticks("GHOST")
STOP_TICKS = _ticks["stop_ticks"]       # fallback: 12
TARGET1_TICKS = _ticks["t1_ticks"]      # fallback: 16
TARGET2_TICKS = _ticks["t2_ticks"]      # fallback: 32
_T1_TICKS = 4  # NOT from YAML


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


def _find_extremes(values: List[float], kind: str = "high") -> list:
    """Find local extremes. kind='high' or 'low'."""
    extremes = []
    for i in range(2, len(values) - 1):
        if kind == "high":
            if values[i] > values[i - 1] and values[i] > values[i - 2] and values[i] > values[i + 1]:
                extremes.append((i, values[i]))
        else:
            if values[i] < values[i - 1] and values[i] < values[i - 2] and values[i] < values[i + 1]:
                extremes.append((i, values[i]))
    return extremes


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect GHOST pattern from WoodiesBar list."""
    if len(bars) < LOOKBACK:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    # ── AP8: universal CCI flat check ──
    ap8 = AntiPatternChecker.check_ap8_cci_flat(bars)
    if ap8.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap8.reason})

    window = [b.cci_14 for b in bars[-LOOKBACK:]]
    bar = bars[-1]

    # Bearish GHOST: three CCI peaks, middle is highest
    peaks = _find_extremes(window, "high")
    if len(peaks) >= 3:
        p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
        if p2[1] > p1[1] and p2[1] > p3[1] and p3[1] < p1[1]:
            current = window[-1]
            if current < p3[1]:
                entry = bar.close
                swing_anchor = max(b.high for b in bars[-LOOKBACK:])
                atr_ticks = _compute_atr14_ticks(bars)
                if atr_ticks > 0:
                    stop_result = compute_stop(
                        direction="SHORT", entry_bar=bar, swing_anchor=swing_anchor,
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
                    confidence=0.7,
                    raw_confidence=0.7,
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
                    details={"left": round(p1[1], 2), "head": round(p2[1], 2),
                             "right": round(p3[1], 2), "stop_layer_applied": stop_layer},
                )

    # Bullish GHOST: three CCI troughs, middle is lowest
    troughs = _find_extremes(window, "low")
    if len(troughs) >= 3:
        t1, t2, t3 = troughs[-3], troughs[-2], troughs[-1]
        if t2[1] < t1[1] and t2[1] < t3[1] and t3[1] > t1[1]:
            current = window[-1]
            if current > t3[1]:
                entry = bar.close
                swing_anchor = min(b.low for b in bars[-LOOKBACK:])
                atr_ticks = _compute_atr14_ticks(bars)
                if atr_ticks > 0:
                    stop_result = compute_stop(
                        direction="LONG", entry_bar=bar, swing_anchor=swing_anchor,
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
                    confidence=0.7,
                    raw_confidence=0.7,
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
                    details={"left": round(t1[1], 2), "head": round(t2[1], 2),
                             "right": round(t3[1], 2), "stop_layer_applied": stop_layer},
                )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_ghost(cci_history: list, bar_index: int, ts: float,
                 **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    n = len(cci_history)
    if n < LOOKBACK:
        return None

    window = cci_history[-LOOKBACK:]

    peaks = _find_extremes(window, "high")
    if len(peaks) >= 3:
        p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
        if p2[1] > p1[1] and p2[1] > p3[1] and p3[1] < p1[1]:
            current = window[-1]
            if current < p3[1]:
                return PatternSignal(
                    pattern="GHOST", group="REVERSAL", direction="SHORT",
                    confidence=0.7,
                    cci_at_signal=current, bar_index=bar_index, ts=ts,
                    details={"left": round(p1[1], 2), "head": round(p2[1], 2),
                             "right": round(p3[1], 2)},
                )

    troughs = _find_extremes(window, "low")
    if len(troughs) >= 3:
        t1, t2, t3 = troughs[-3], troughs[-2], troughs[-1]
        if t2[1] < t1[1] and t2[1] < t3[1] and t3[1] > t1[1]:
            current = window[-1]
            if current > t3[1]:
                return PatternSignal(
                    pattern="GHOST", group="REVERSAL", direction="LONG",
                    confidence=0.7,
                    cci_at_signal=current, bar_index=bar_index, ts=ts,
                    details={"left": round(t1[1], 2), "head": round(t2[1], 2),
                             "right": round(t3[1], 2)},
                )

    return None
