"""FAMIR (Failed Attempt at Major Intermediate Resistance) -- Reversal pattern.

CCI approaches +/-200 but fails to reach or exceed it, then reverses.
Signals exhaustion of the trend at the major resistance/support level.

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (B3).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal
from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker
from backend.v9.systems.woodies.atr_stop import compute_stop, compute_stop_v2, PatternGroup
from backend.v9.shared.atr import flag as _flag

THRESHOLD = 200
NEAR_THRESHOLD = 170  # "approaching" the +/-200 level
PATTERN_ID = "FAMIR"
GROUP = "REVERSAL"
_PATTERN_GROUP = PatternGroup.REV
TICK_SIZE = 0.25
from ._pattern_ticks import get_ticks as _get_ticks
_ticks = _get_ticks("FAMIR")
STOP_TICKS = _ticks["stop_ticks"]       # fallback: 10
TARGET1_TICKS = _ticks["t1_ticks"]      # fallback: 14
TARGET2_TICKS = _ticks["t2_ticks"]      # fallback: 28
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
    """Detect FAMIR pattern from WoodiesBar list."""
    if len(bars) < 5:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    # ── AP8: universal CCI flat check ──
    ap8 = AntiPatternChecker.check_ap8_cci_flat(bars)
    if ap8.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap8.reason})

    bar = bars[-1]
    current = bar.cci_14
    prev = bars[-2].cci_14
    recent = [b.cci_14 for b in bars[-5:]]
    max_recent = max(recent)
    min_recent = min(recent)

    # FAMIR SHORT: CCI approached +200 but failed, now dropping
    if max_recent >= NEAR_THRESHOLD and max_recent < THRESHOLD + 10:
        if current < prev and current < max_recent - 20:
            # ── AP9: FAMIR LSMA mismatch ──
            ap9 = AntiPatternChecker.check_ap9_famir_lsma(bars, direction="SHORT")
            if ap9.blocked:
                return PatternResult(detected=False, pattern_id=PATTERN_ID,
                                     details={"reject_reason": ap9.reason})
            entry = bar.close
            swing_anchor = max(b.high for b in bars[-5:])
            atr_ticks = _compute_atr14_ticks(bars)
            if _flag("STOP_ANCHORS_V2") and atr_ticks > 0:
                from backend.v9.systems.stop_anchors import resolver as SA
                from backend.v9.config_loader import load_stop_anchors
                cfg = load_stop_anchors()
                if cfg:
                    # failed_bar: structural = the failed bar's high + 3T offset
                    struct = SA.apply_offset(swing_anchor, "SHORT",
                                             cfg["principles"]["anchor_offset_ticks"], TICK_SIZE)
                    v2 = compute_stop_v2("SHORT", entry, struct, _PATTERN_GROUP, atr_ticks,
                                         tick_size=TICK_SIZE)
                    stop = v2.stop_price
                    stop_layer = "v2_structural"
                else:
                    stop_result = compute_stop(
                        direction="SHORT", entry_bar=bar, swing_anchor=swing_anchor,
                        pattern_group=_PATTERN_GROUP, atr_14=atr_ticks, tick_size=TICK_SIZE)
                    stop = stop_result.stop_price
                    stop_layer = stop_result.layer_applied
            elif atr_ticks > 0:
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
            conf = min(0.8, 0.5 + (THRESHOLD - max_recent) / 100)
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
                details={"peak_cci": round(max_recent, 2),
                         "distance_from_200": round(THRESHOLD - max_recent, 2),
                         "stop_layer_applied": stop_layer},
            )

    # FAMIR LONG: CCI approached -200 but failed, now rising
    if min_recent <= -NEAR_THRESHOLD and min_recent > -(THRESHOLD + 10):
        if current > prev and current > min_recent + 20:
            # ── AP9: FAMIR LSMA mismatch ──
            ap9 = AntiPatternChecker.check_ap9_famir_lsma(bars, direction="LONG")
            if ap9.blocked:
                return PatternResult(detected=False, pattern_id=PATTERN_ID,
                                     details={"reject_reason": ap9.reason})
            entry = bar.close
            swing_anchor = min(b.low for b in bars[-5:])
            atr_ticks = _compute_atr14_ticks(bars)
            if _flag("STOP_ANCHORS_V2") and atr_ticks > 0:
                from backend.v9.systems.stop_anchors import resolver as SA
                from backend.v9.config_loader import load_stop_anchors
                cfg = load_stop_anchors()
                if cfg:
                    struct = SA.apply_offset(swing_anchor, "LONG",
                                             cfg["principles"]["anchor_offset_ticks"], TICK_SIZE)
                    v2 = compute_stop_v2("LONG", entry, struct, _PATTERN_GROUP, atr_ticks,
                                         tick_size=TICK_SIZE)
                    stop = v2.stop_price
                    stop_layer = "v2_structural"
                else:
                    stop_result = compute_stop(
                        direction="LONG", entry_bar=bar, swing_anchor=swing_anchor,
                        pattern_group=_PATTERN_GROUP, atr_14=atr_ticks, tick_size=TICK_SIZE)
                    stop = stop_result.stop_price
                    stop_layer = stop_result.layer_applied
            elif atr_ticks > 0:
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
            conf = min(0.8, 0.5 + (THRESHOLD - abs(min_recent)) / 100)
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
                details={"trough_cci": round(min_recent, 2),
                         "distance_from_n200": round(THRESHOLD - abs(min_recent), 2),
                         "stop_layer_applied": stop_layer},
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
