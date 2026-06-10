"""VEGAS (Virtual Extended Geometric Algo Scan) -- Reversal pattern.

Multiple indicators align for strong trend entry via divergence detection.
Price makes HH but CCI makes LH (bearish divergence), or
price makes LL but CCI makes HL (bullish divergence).

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (B1).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal
from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker
from backend.v9.systems.woodies.atr_stop import compute_stop, compute_stop_v2, PatternGroup
from backend.v9.shared.atr import flag as _flag

LOOKBACK = 20
PATTERN_ID = "VEGAS"
GROUP = "REVERSAL"
_PATTERN_GROUP = PatternGroup.REV
TICK_SIZE = 0.25
from ._pattern_ticks import get_ticks as _get_ticks
_ticks = _get_ticks("VEGAS")
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


def _find_swings(values: List[float], min_swing: int = 3) -> list:
    """Find swing highs and lows as (index, value, type='H'|'L')."""
    swings = []
    for i in range(min_swing, len(values) - 1):
        is_high = all(values[i] >= values[i - j] for j in range(1, min_swing + 1))
        if i + 1 < len(values):
            is_high = is_high and values[i] > values[i + 1]
        if is_high:
            swings.append((i, values[i], "H"))

        is_low = all(values[i] <= values[i - j] for j in range(1, min_swing + 1))
        if i + 1 < len(values):
            is_low = is_low and values[i] < values[i + 1]
        if is_low:
            swings.append((i, values[i], "L"))
    return swings


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect VEGAS pattern from WoodiesBar list."""
    if len(bars) < LOOKBACK:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    # ── AP8: universal CCI flat check ──
    ap8 = AntiPatternChecker.check_ap8_cci_flat(bars)
    if ap8.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap8.reason})

    window_bars = bars[-LOOKBACK:]
    window_cci = [b.cci_14 for b in window_bars]
    window_price = [b.close for b in window_bars]
    bar = bars[-1]

    price_swings = _find_swings(window_price, 2)
    cci_swings = _find_swings(window_cci, 2)

    price_highs = [(i, v) for i, v, t in price_swings if t == "H"]
    cci_highs = [(i, v) for i, v, t in cci_swings if t == "H"]
    price_lows = [(i, v) for i, v, t in price_swings if t == "L"]
    cci_lows = [(i, v) for i, v, t in cci_swings if t == "L"]

    # Bearish VEGAS: price HH, CCI LH. This uses the second most recent swing
    # and the most recent swing to require a double divergence structure rather
    # than a single-bar mismatch.
    if len(price_highs) >= 2 and len(cci_highs) >= 2:
        p1, p2 = price_highs[-2], price_highs[-1]
        c1, c2 = cci_highs[-2], cci_highs[-1]
        if p2[1] > p1[1] and c2[1] < c1[1]:
            # ── AP3: VEGAS swings too close ──
            _swing_lo = min(p1[0], p2[0])
            _swing_hi = max(p1[0], p2[0])
            ap3 = AntiPatternChecker.check_ap3_vegas_swings(bars, _swing_lo, _swing_hi)
            if ap3.blocked:
                return PatternResult(detected=False, pattern_id=PATTERN_ID,
                                     details={"reject_reason": ap3.reason})
            entry = bar.close
            # swing_anchor = most recent price swing high for REV stop
            swing_anchor = max(b.high for b in bars[-LOOKBACK:])
            atr_ticks = _compute_atr14_ticks(bars)
            if _flag("STOP_ANCHORS_V2") and atr_ticks > 0:
                from backend.v9.systems.stop_anchors import resolver as SA
                from backend.v9.config_loader import load_stop_anchors
                cfg = load_stop_anchors()
                if cfg:
                    # swing_extreme: use the known structural price + 3T offset
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
            return PatternResult(
                detected=True,
                pattern_id=PATTERN_ID,
                direction="SHORT",
                confidence=0.75,
                raw_confidence=0.75,
                r_t1=r_t1,
                entry_price=entry,
                stop=stop,
                targets=[
                    entry - TARGET1_TICKS * TICK_SIZE,
                    entry - TARGET2_TICKS * TICK_SIZE,
                ],
                group=GROUP,
                cci_at_signal=bar.cci_14,
                bar_index=len(bars) - 1,
                ts=bar.ts,
                details={"price_hh": True, "cci_lh": True, "swing_anchor": swing_anchor,
                         "measure_pts": round(abs(c1[1] - c2[1]) / 25.0, 2),
                         "stop_layer_applied": stop_layer},
            )

    # Bullish VEGAS: price LL, CCI HL. This uses the second most recent swing
    # and the most recent swing to require a double divergence structure rather
    # than a single-bar mismatch.
    if len(price_lows) >= 2 and len(cci_lows) >= 2:
        p1, p2 = price_lows[-2], price_lows[-1]
        c1, c2 = cci_lows[-2], cci_lows[-1]
        if p2[1] < p1[1] and c2[1] > c1[1]:
            # ── AP3: VEGAS swings too close ──
            _swing_lo = min(p1[0], p2[0])
            _swing_hi = max(p1[0], p2[0])
            ap3 = AntiPatternChecker.check_ap3_vegas_swings(bars, _swing_lo, _swing_hi)
            if ap3.blocked:
                return PatternResult(detected=False, pattern_id=PATTERN_ID,
                                     details={"reject_reason": ap3.reason})
            entry = bar.close
            swing_anchor = min(b.low for b in bars[-LOOKBACK:])
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
            return PatternResult(
                detected=True,
                pattern_id=PATTERN_ID,
                direction="LONG",
                confidence=0.75,
                raw_confidence=0.75,
                r_t1=r_t1,
                entry_price=entry,
                stop=stop,
                targets=[
                    entry + TARGET1_TICKS * TICK_SIZE,
                    entry + TARGET2_TICKS * TICK_SIZE,
                ],
                group=GROUP,
                cci_at_signal=bar.cci_14,
                bar_index=len(bars) - 1,
                ts=bar.ts,
                details={"price_ll": True, "cci_hl": True, "swing_anchor": swing_anchor,
                         "stop_layer_applied": stop_layer,
                         "measure_pts": round(abs(c2[1] - c1[1]) / 25.0, 2)},
            )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_vegas(cci_history: list, bar_index: int, ts: float,
                 price_closes: list = None, **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py.

    Uses the second most recent swing and most recent swing, which is the
    double divergence structure required by the VEGAS spec.
    """
    if price_closes is None or len(price_closes) < LOOKBACK or len(cci_history) < LOOKBACK:
        return None

    window_cci = cci_history[-LOOKBACK:]
    window_price = price_closes[-LOOKBACK:]

    price_swings = _find_swings(window_price, 2)
    cci_swings = _find_swings(window_cci, 2)

    price_highs = [(i, v) for i, v, t in price_swings if t == "H"]
    cci_highs = [(i, v) for i, v, t in cci_swings if t == "H"]
    price_lows = [(i, v) for i, v, t in price_swings if t == "L"]
    cci_lows = [(i, v) for i, v, t in cci_swings if t == "L"]

    if len(price_highs) >= 2 and len(cci_highs) >= 2:
        p1, p2 = price_highs[-2], price_highs[-1]
        c1, c2 = cci_highs[-2], cci_highs[-1]
        if p2[1] > p1[1] and c2[1] < c1[1]:
            return PatternSignal(
                pattern="VEGAS", group="REVERSAL", direction="SHORT",
                confidence=0.75,
                cci_at_signal=cci_history[-1], bar_index=bar_index, ts=ts,
                details={"price_hh": True, "cci_lh": True},
            )

    if len(price_lows) >= 2 and len(cci_lows) >= 2:
        p1, p2 = price_lows[-2], price_lows[-1]
        c1, c2 = cci_lows[-2], cci_lows[-1]
        if p2[1] < p1[1] and c2[1] > c1[1]:
            return PatternSignal(
                pattern="VEGAS", group="REVERSAL", direction="LONG",
                confidence=0.75,
                cci_at_signal=cci_history[-1], bar_index=bar_index, ts=ts,
                details={"price_ll": True, "cci_hl": True},
            )

    return None
