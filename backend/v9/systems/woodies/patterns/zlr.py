"""ZLR (Zero Line Reject) -- Continuation pattern.

ZLR UP:  CCI was above +100 -> pulls back toward zero (stays > -100) -> bounces up.
ZLR DOWN: CCI was below -100 -> pulls back toward zero (stays < +100) -> drops.
Lookback: 12 bars (matching DLL).

Spec reference: MEMS26_WOODIES_SPEC_V1_DERIVED Section 5 (A1).
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult, PatternSignal
from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker
from backend.v9.systems.woodies.atr_stop import compute_stop, compute_stop_v2, PatternGroup
from backend.v9.shared.atr import flag as _flag

LOOKBACK = 12
PATTERN_ID = "ZLR"
GROUP = "CONTINUATION"
_PATTERN_GROUP = PatternGroup.CONT_TIGHT
# MES tick size for stop/target computation
TICK_SIZE = 0.25
from ._pattern_ticks import get_ticks as _get_ticks
_ticks = _get_ticks("ZLR")
STOP_TICKS = _ticks["stop_ticks"]       # fallback: 8
TARGET1_TICKS = _ticks["t1_ticks"]      # fallback: 12
TARGET2_TICKS = _ticks["t2_ticks"]      # fallback: 24
_T1_TICKS = 4  # T1 for R_t1 computation — intentionally NOT from YAML


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
    # Wilder's smoothing
    atr = sum(trs[:14]) / 14
    for tr in trs[14:]:
        atr = ((atr * 13) + tr) / 14
    return atr / tick_size


def _compute_r_t1(entry_price: float, stop_price: float, direction: str,
                  tick_size: float = TICK_SIZE, t1_ticks: int = _T1_TICKS) -> Optional[float]:
    """Compute R_t1 = (t1_price - entry_price) / (entry_price - stop_price). Always positive."""
    risk = abs(entry_price - stop_price)
    if risk < 1e-9:
        return None
    t1_distance = t1_ticks * tick_size
    return t1_distance / risk


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> PatternResult:
    """Detect ZLR pattern from WoodiesBar list.

    Returns PatternResult with detected=True if a ZLR is found.
    """
    n = len(bars)
    if n < LOOKBACK + 1:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    # ── AP8: universal CCI flat check ──
    ap8 = AntiPatternChecker.check_ap8_cci_flat(bars)
    if ap8.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap8.reason})

    # ── AP1: ZLR pullback too long ──
    ap1 = AntiPatternChecker.check_ap1_zlr_pullback(bars)
    if ap1.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap1.reason})

    cci_history = [b.cci_14 for b in bars]
    current = cci_history[-1]
    prev = cci_history[-2]
    bar = bars[-1]

    # ZLR UP Stage 1: find bar where CCI >= 100 (trend-side extreme per DTV1 § A3)
    for i in range(n - 2, max(n - LOOKBACK - 2, -1), -1):
        if cci_history[i] >= 100:
            # Stage 2: pullback below 100, NOT below -100
            pulled = any(
                -100 < cci_history[j] <= 100
                for j in range(i + 1, n - 1)
            )
            # Stage 3: sharp reversal up, CCI bouncing back
            if pulled and current > prev and 0 < current < 200:
                bars_since = n - 1 - i
                entry = bar.close
                # ATR-based stop (W-6)
                atr_ticks = _compute_atr14_ticks(bars)
                if _flag("STOP_ANCHORS_V2") and atr_ticks > 0:
                    from backend.v9.config_loader import load_stop_anchors
                    from backend.v9.systems.stop_anchors import resolver as SA
                    cfg = load_stop_anchors()
                    if cfg:
                        a = cfg["anchors"]["ZLR"]
                        window_bars = bars[-a["window"]:]  # cluster_low: last N bars
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
                        pattern_group=_PATTERN_GROUP, atr_14=atr_ticks,
                        tick_size=TICK_SIZE,
                    )
                    stop = stop_result.stop_price
                    stop_layer = stop_result.layer_applied
                else:
                    stop = entry - STOP_TICKS * TICK_SIZE
                    stop_layer = "primary"
                r_t1 = _compute_r_t1(entry, stop, "LONG")
                conf = min(0.9, 0.5 + current / 400)
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
                    details={"bars_since_extreme": bars_since, "stop_layer_applied": stop_layer},
                )
            break

    # ZLR DOWN Stage 1: find bar where CCI <= -100 (trend-side extreme per DTV1 § A3)
    for i in range(n - 2, max(n - LOOKBACK - 2, -1), -1):
        if cci_history[i] <= -100:
            # Stage 2: pullback above -100, NOT above +100
            pulled = any(
                -100 <= cci_history[j] < 100
                for j in range(i + 1, n - 1)
            )
            if pulled and current < prev and -200 < current < 0:
                bars_since = n - 1 - i
                entry = bar.close
                # ATR-based stop (W-6)
                atr_ticks = _compute_atr14_ticks(bars)
                if _flag("STOP_ANCHORS_V2") and atr_ticks > 0:
                    from backend.v9.config_loader import load_stop_anchors
                    from backend.v9.systems.stop_anchors import resolver as SA
                    cfg = load_stop_anchors()
                    if cfg:
                        a = cfg["anchors"]["ZLR"]
                        window_bars = bars[-a["window"]:]
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
                        pattern_group=_PATTERN_GROUP, atr_14=atr_ticks,
                        tick_size=TICK_SIZE,
                    )
                    stop = stop_result.stop_price
                    stop_layer = stop_result.layer_applied
                else:
                    stop = entry + STOP_TICKS * TICK_SIZE
                    stop_layer = "primary"
                r_t1 = _compute_r_t1(entry, stop, "SHORT")
                conf = min(0.9, 0.5 + abs(current) / 400)
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
                    details={"bars_since_extreme": bars_since, "stop_layer_applied": stop_layer},
                )
            break

    return PatternResult(detected=False, pattern_id=PATTERN_ID)


def detect_zlr(cci_history: list, bar_index: int, ts: float,
               **kwargs) -> Optional[PatternSignal]:
    """Legacy interface for backward compatibility with detector.py."""
    n = len(cci_history)
    if n < LOOKBACK + 1:
        return None

    current = cci_history[-1]
    prev = cci_history[-2]

    # ZLR UP Stage 1: CCI >= 100 (DTV1 § A3)
    for i in range(n - 2, max(n - LOOKBACK - 1, -1), -1):
        if cci_history[i] >= 100:
            bars_since = n - 1 - i
            pulled = any(
                -100 < cci_history[j] <= 100
                for j in range(i + 1, n - 1)
            )
            if pulled and current > prev and 0 < current < 200:
                return PatternSignal(
                    pattern="ZLR", group="CONTINUATION", direction="LONG",
                    confidence=min(0.9, 0.5 + current / 400),
                    cci_at_signal=current, bar_index=bar_index, ts=ts,
                    details={"bars_since_extreme": bars_since},
                )
            break

    # ZLR DOWN Stage 1: CCI <= -100 (DTV1 § A3)
    for i in range(n - 2, max(n - LOOKBACK - 1, -1), -1):
        if cci_history[i] <= -100:
            bars_since = n - 1 - i
            pulled = any(
                -100 <= cci_history[j] < 100
                for j in range(i + 1, n - 1)
            )
            if pulled and current < prev and -200 < current < 0:
                return PatternSignal(
                    pattern="ZLR", group="CONTINUATION", direction="SHORT",
                    confidence=min(0.9, 0.5 + abs(current) / 400),
                    cci_at_signal=current, bar_index=bar_index, ts=ts,
                    details={"bars_since_extreme": bars_since},
                )
            break

    return None
