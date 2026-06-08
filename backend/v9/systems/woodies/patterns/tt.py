"""TT (Turbo Trend) -- Continuation pattern.

TCCI (CCI-6) hooks in the trend direction while CCI-14 is trending.
Specifically: TCCI touches or crosses CCI-14 during a trend, then
bounces back in the trend direction. Confirms trend strength.

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (A3).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal
from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker
from backend.v9.systems.woodies.atr_stop import compute_stop, compute_stop_v2, PatternGroup
from backend.v9.shared.atr import flag as _flag

PATTERN_ID = "TT"
GROUP = "CONTINUATION"
_PATTERN_GROUP = PatternGroup.CONT_TIGHT
TICK_SIZE = 0.25
from ._pattern_ticks import get_ticks as _get_ticks
_ticks = _get_ticks("TT")
STOP_TICKS = _ticks["stop_ticks"]       # fallback: 8
TARGET1_TICKS = _ticks["t1_ticks"]      # fallback: 12
TARGET2_TICKS = _ticks["t2_ticks"]      # fallback: 20
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
    """Detect TT pattern from WoodiesBar list."""
    if len(bars) < 3:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    # ── AP8: universal CCI flat check ──
    ap8 = AntiPatternChecker.check_ap8_cci_flat(bars)
    if ap8.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap8.reason})

    # ── AP7: TT TCCI divergence gap ──
    ap7 = AntiPatternChecker.check_ap7_tt_divergence_gap(bars[-1])
    if ap7.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap7.reason})

    bar = bars[-1]
    bar_prev = bars[-2]
    bar_prev2 = bars[-3]

    cci14 = bar.cci_14
    cci14_prev = bar_prev.cci_14
    cci6 = bar.cci_6_tcci
    cci6_prev = bar_prev.cci_6_tcci
    cci6_prev2 = bar_prev2.cci_6_tcci
    trend = bar.trend_state

    # TT LONG: trend BLUE, TCCI touched CCI-14 from above then bounced
    if trend == "BLUE" and cci14 > 0:
        touched = (cci6_prev <= cci14_prev + 5)
        bounced = (cci6 > cci14 + 5) and (cci6 > cci6_prev)
        was_above = (cci6_prev2 > bar_prev2.cci_14 + 10)
        if touched and bounced and was_above:
            entry = bar.close
            atr_ticks = _compute_atr14_ticks(bars)
            if _flag("STOP_ANCHORS_V2") and atr_ticks > 0:
                from backend.v9.config_loader import load_stop_anchors
                from backend.v9.systems.stop_anchors import resolver as SA
                cfg = load_stop_anchors()
                if cfg:
                    a = cfg["anchors"]["TT"]
                    # zl_excursion: bars of the excursion (up to window)
                    window_bars = bars[-min(a["window"], len(bars)):]
                    struct = SA.resolve_anchor_from_window(
                        window_bars, "LONG", cfg["principles"]["anchor_offset_ticks"], TICK_SIZE)
                    v2 = compute_stop_v2("LONG", entry, struct, _PATTERN_GROUP, atr_ticks,
                                         tick_size=TICK_SIZE)
                    stop = v2.stop_price
                    stop_layer = "v2_structural"
                else:
                    stop_result = compute_stop(
                        direction="LONG", entry_bar=bar, swing_anchor=None,
                        pattern_group=_PATTERN_GROUP, atr_14=atr_ticks, tick_size=TICK_SIZE)
                    stop = stop_result.stop_price
                    stop_layer = stop_result.layer_applied
            elif atr_ticks > 0:
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
                cci_at_signal=cci14,
                bar_index=len(bars) - 1,
                ts=bar.ts,
                details={"cci6": round(cci6, 2), "gap": round(cci6 - cci14, 2),
                         "stop_layer_applied": stop_layer},
            )

    # TT SHORT: trend RED, TCCI touched CCI-14 from below then dropped
    if trend == "RED" and cci14 < 0:
        touched = (cci6_prev >= cci14_prev - 5)
        bounced = (cci6 < cci14 - 5) and (cci6 < cci6_prev)
        was_below = (cci6_prev2 < bar_prev2.cci_14 - 10)
        if touched and bounced and was_below:
            entry = bar.close
            atr_ticks = _compute_atr14_ticks(bars)
            if _flag("STOP_ANCHORS_V2") and atr_ticks > 0:
                from backend.v9.config_loader import load_stop_anchors
                from backend.v9.systems.stop_anchors import resolver as SA
                cfg = load_stop_anchors()
                if cfg:
                    a = cfg["anchors"]["TT"]
                    window_bars = bars[-min(a["window"], len(bars)):]
                    struct = SA.resolve_anchor_from_window(
                        window_bars, "SHORT", cfg["principles"]["anchor_offset_ticks"], TICK_SIZE)
                    v2 = compute_stop_v2("SHORT", entry, struct, _PATTERN_GROUP, atr_ticks,
                                         tick_size=TICK_SIZE)
                    stop = v2.stop_price
                    stop_layer = "v2_structural"
                else:
                    stop_result = compute_stop(
                        direction="SHORT", entry_bar=bar, swing_anchor=None,
                        pattern_group=_PATTERN_GROUP, atr_14=atr_ticks, tick_size=TICK_SIZE)
                    stop = stop_result.stop_price
                    stop_layer = stop_result.layer_applied
            elif atr_ticks > 0:
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
                cci_at_signal=cci14,
                bar_index=len(bars) - 1,
                ts=bar.ts,
                details={"cci6": round(cci6, 2), "gap": round(cci6 - cci14, 2),
                         "stop_layer_applied": stop_layer},
            )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_tt(cci_history: list, bar_index: int, ts: float,
              cci6_history: list = None, trend_state: str = "GRAY",
              **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    if cci6_history is None or len(cci6_history) < 3 or len(cci_history) < 3:
        return None

    cci14 = cci_history[-1]
    cci14_prev = cci_history[-2]
    cci6 = cci6_history[-1]
    cci6_prev = cci6_history[-2]
    cci6_prev2 = cci6_history[-3]

    if trend_state == "BLUE" and cci14 > 0:
        touched = (cci6_prev <= cci14_prev + 5)
        bounced = (cci6 > cci14 + 5) and (cci6 > cci6_prev)
        was_above = (cci6_prev2 > cci14_prev + 10)
        if touched and bounced and was_above:
            return PatternSignal(
                pattern="TT", group="CONTINUATION", direction="LONG",
                confidence=0.7,
                cci_at_signal=cci14, bar_index=bar_index, ts=ts,
                details={"cci6": round(cci6, 2), "gap": round(cci6 - cci14, 2)},
            )

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
