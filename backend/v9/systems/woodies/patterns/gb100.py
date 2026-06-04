"""GB100 (Ghost Bar 100) -- Continuation pattern.

CCI-14 bar touches +/-100 line and reverses back into the trend direction.
Specifically: CCI crosses the +100 or -100 level with momentum, confirming
trend continuation. Must already be in a trend (BLUE/RED).

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (A4).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal
from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker
from backend.v9.systems.woodies.atr_stop import compute_stop, PatternGroup

PATTERN_ID = "GB100"
GROUP = "CONTINUATION"
_PATTERN_GROUP = PatternGroup.CONT_MED
TICK_SIZE = 0.25
from ._pattern_ticks import get_ticks as _get_ticks
_ticks = _get_ticks("GB100")
STOP_TICKS = _ticks["stop_ticks"]       # fallback: 8
TARGET1_TICKS = _ticks["t1_ticks"]      # fallback: 12
TARGET2_TICKS = _ticks["t2_ticks"]      # fallback: 24
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


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect GB100 pattern from WoodiesBar list."""
    if len(bars) < 3:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    # ── AP8: universal CCI flat check ──
    ap8 = AntiPatternChecker.check_ap8_cci_flat(bars)
    if ap8.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap8.reason})

    # ── AP2: GB100 in YELLOW trend ──
    ap2 = AntiPatternChecker.check_ap2_gb100_yellow(bars)
    if ap2.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap2.reason})

    # ── AP6: GB100 pullback depth (count recent bars on opposite side of ZL) ──
    _trend = bars[-1].trend_state
    _opposite_count = 0
    for _b in reversed(bars[:-1]):
        if _trend == "BLUE" and _b.cci_14 < 0:
            _opposite_count += 1
        elif _trend == "RED" and _b.cci_14 > 0:
            _opposite_count += 1
        else:
            break
    ap6 = AntiPatternChecker.check_ap6_gb100_pullback_depth(bars, _opposite_count)
    if ap6.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap6.reason})

    bar = bars[-1]
    current = bar.cci_14
    prev = bars[-2].cci_14
    prev2 = bars[-3].cci_14
    trend = bar.trend_state

    # GB100 LONG: CCI crosses above +100 in a BLUE trend
    if trend == "BLUE" and current > 100 and prev <= 100 and prev2 < 100:
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
        conf = min(0.85, 0.5 + (current - 100) / 200)
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
            bar_index=len(bars) - 1,
            ts=bar.ts,
            details={"cross_level": 100, "momentum": round(current - prev, 2),
                     "stop_layer_applied": stop_layer},
        )

    # GB100 SHORT: CCI crosses below -100 in a RED trend
    if trend == "RED" and current < -100 and prev >= -100 and prev2 > -100:
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
        conf = min(0.85, 0.5 + (abs(current) - 100) / 200)
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
            bar_index=len(bars) - 1,
            ts=bar.ts,
            details={"cross_level": -100, "momentum": round(current - prev, 2),
                     "stop_layer_applied": stop_layer},
        )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_gb100(cci_history: list, bar_index: int, ts: float,
                 trend_state: str = "GRAY", **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    n = len(cci_history)
    if n < 3:
        return None

    current = cci_history[-1]
    prev = cci_history[-2]
    prev2 = cci_history[-3]

    if trend_state == "BLUE" and current > 100 and prev <= 100 and prev2 < 100:
        return PatternSignal(
            pattern="GB100", group="CONTINUATION", direction="LONG",
            confidence=min(0.85, 0.5 + (current - 100) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"cross_level": 100, "momentum": round(current - prev, 2)},
        )

    if trend_state == "RED" and current < -100 and prev >= -100 and prev2 > -100:
        return PatternSignal(
            pattern="GB100", group="CONTINUATION", direction="SHORT",
            confidence=min(0.85, 0.5 + (abs(current) - 100) / 200),
            cci_at_signal=current, bar_index=bar_index, ts=ts,
            details={"cross_level": -100, "momentum": round(current - prev, 2)},
        )

    return None
