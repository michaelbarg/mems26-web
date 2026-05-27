"""HFE (Hook From Extreme) -- NEW_TREND pattern #9.

CCI(14) reaches +/-200 within last 6-12 bars (EXTREME zone),
then hooks back toward zero line -- price reversal candidate.

Direction:
  HFE UP:   CCI hit -200 or below, now hooking UP toward zero
  HFE DOWN: CCI hit +200 or above, now hooking DOWN toward zero

Category: NEW_TREND (with VEGAS, GHOST, FAMIR, HTLB)
Spec: MEMS26 Woodies Decision Tree V1, pattern #9 (A3)

W-4: DLL-primary with AP5 enforcement. Python runs for audit only.
     Trade decision is ALWAYS from DLL path. Python result is NEVER
     returned as trade decision -- only used for divergence logging.
"""

import time
from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult
from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker
from backend.v9.systems.woodies.atr_stop import compute_stop, PatternGroup
from backend.v9.systems.woodies.hfe_divergence_logger import (
    HFEDivergence,
    HFEDivergenceLogger,
)

PATTERN_ID = "HFE"
GROUP = "REVERSAL"  # NEW_TREND per spec -> mapped to REVERSAL group
_PATTERN_GROUP = PatternGroup.REV
LOOKBACK = 12  # bars to search for extreme
EXTREME_THRESHOLD = 200  # CCI must reach +/-200
HOOK_THRESHOLD = 50  # CCI must hook back at least this far from extreme
TICK_SIZE = 0.25
STOP_TICKS = 8
TARGET1_TICKS = 12
TARGET2_TICKS = 24
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

# Module-level divergence logger (can be replaced for testing)
_divergence_logger = HFEDivergenceLogger()


def _python_fallback_compute(bars: List[WoodiesBar]) -> dict:
    """Run the Python HFE detection logic. Returns a dict with detection info.

    This NEVER produces a trade decision -- only audit data.
    Logic and constants are identical to the original Python fallback.
    """
    result = {
        "detected": False,
        "direction": "NONE",
        "bars_ago": 0,
        "confidence": 0.0,
        "details": {},
    }

    if len(bars) < 4:
        return result

    current = bars[-1]
    cci_now = current.cci_14
    cci_prev = bars[-2].cci_14
    search_window = bars[-min(LOOKBACK, len(bars)):]
    cci_history = [b.cci_14 for b in search_window]

    max_cci = max(cci_history)
    min_cci = min(cci_history)
    max_idx = cci_history.index(max_cci)
    min_idx = cci_history.index(min_cci)

    # HFE UP: hit -200 or below, now hooking up
    if min_cci <= -EXTREME_THRESHOLD:
        bars_since_extreme = len(cci_history) - 1 - min_idx
        if 2 <= bars_since_extreme <= LOOKBACK:
            hook_distance = cci_now - min_cci
            if hook_distance >= HOOK_THRESHOLD and cci_now > cci_prev:
                result["detected"] = True
                result["direction"] = "LONG"
                result["bars_ago"] = bars_since_extreme
                result["confidence"] = min(0.8, 0.5 + hook_distance / 400)
                result["details"] = {
                    "source": "Python_fallback",
                    "extreme_cci": round(min_cci, 2),
                    "hook_distance": round(hook_distance, 2),
                    "bars_since_extreme": bars_since_extreme,
                }
                return result

    # HFE DOWN: hit +200 or above, now hooking down
    if max_cci >= EXTREME_THRESHOLD:
        bars_since_extreme = len(cci_history) - 1 - max_idx
        if 2 <= bars_since_extreme <= LOOKBACK:
            hook_distance = max_cci - cci_now
            if hook_distance >= HOOK_THRESHOLD and cci_now < cci_prev:
                result["detected"] = True
                result["direction"] = "SHORT"
                result["bars_ago"] = bars_since_extreme
                result["confidence"] = min(0.8, 0.5 + hook_distance / 400)
                result["details"] = {
                    "source": "Python_fallback",
                    "extreme_cci": round(max_cci, 2),
                    "hook_distance": round(hook_distance, 2),
                    "bars_since_extreme": bars_since_extreme,
                }
                return result

    return result


def _log_divergence_if_needed(
    bar_ts: float,
    dll_detected: bool,
    dll_direction: str,
    dll_bars_ago: int,
    dll_confidence: float,
    py: dict,
) -> None:
    """Compare DLL vs Python results and log any divergence."""
    py_detected = py["detected"]
    py_direction = py["direction"]
    py_bars_ago = py["bars_ago"]
    py_confidence = py["confidence"]

    divergences = []

    # State mismatch
    if dll_detected != py_detected:
        divergences.append("state_mismatch")

    # Direction mismatch (only meaningful if both detected)
    if dll_detected and py_detected and dll_direction != py_direction:
        divergences.append("direction_mismatch")

    # Bars ago mismatch (only meaningful if both detected)
    if dll_detected and py_detected and dll_bars_ago != py_bars_ago:
        divergences.append("bars_ago_mismatch")

    # Confidence drift > 0.1 (only meaningful if both detected)
    if dll_detected and py_detected and abs(dll_confidence - py_confidence) > 0.1:
        divergences.append("confidence_drift")

    now = time.time()
    for div_type in divergences:
        event = HFEDivergence(
            timestamp=now,
            bar_ts=bar_ts,
            divergence_type=div_type,
            dll_detected=dll_detected,
            dll_direction=dll_direction,
            dll_bars_ago=dll_bars_ago,
            dll_confidence=dll_confidence,
            python_detected=py_detected,
            python_direction=py_direction,
            python_bars_ago=py_bars_ago,
            python_confidence=py_confidence,
            notes=f"W-4 audit divergence: {div_type}",
        )
        _divergence_logger.log_divergence(event)


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> Optional[PatternResult]:
    """Detect HFE pattern from WoodiesBar list.

    W-4 flow (P-W2 LOCK B):
    1. Python fallback runs ALWAYS (for audit)
    2. Compare DLL vs Python -> log divergence if different
    3. AP5 enforced on DLL path: bars_ago must be in [2, 12]
    4. Trade decision uses DLL ONLY -- Python NEVER returned as trade
    5. Confidence formulas UNCHANGED (DLL=0.7, Python=dynamic)
    """
    if len(bars) < 4:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    # ── AP8: universal CCI flat check (W-7) ──
    ap8 = AntiPatternChecker.check_ap8_cci_flat(bars)
    if ap8.blocked:
        return PatternResult(detected=False, pattern_id=PATTERN_ID,
                             details={"reject_reason": ap8.reason})

    current = bars[-1]
    cci_now = current.cci_14

    # ── ALWAYS: run Python fallback for audit ──
    py_result = _python_fallback_compute(bars)

    # ── PRIMARY: DLL JSON detection ──
    dll_detected = (
        getattr(current, 'hfe_detected', False)
        and getattr(current, 'hfe_direction', 'NONE') != 'NONE'
    )
    dll_direction_raw = getattr(current, 'hfe_direction', 'NONE')
    dll_bars_ago = getattr(current, 'hfe_extreme_bars_ago', 0)
    dll_confidence = 0.7  # fixed per spec

    # Map DLL direction to trade direction
    if dll_detected:
        direction = "LONG" if dll_direction_raw == "UP" else "SHORT"
    else:
        direction = "NONE"

    # ── Log divergence between DLL and Python ──
    _log_divergence_if_needed(
        bar_ts=current.ts,
        dll_detected=dll_detected,
        dll_direction=direction,
        dll_bars_ago=dll_bars_ago,
        dll_confidence=dll_confidence,
        py=py_result,
    )

    # ── AP5 enforcement on DLL path ──
    ap5_blocked = False
    if dll_detected and not (2 <= dll_bars_ago <= 12):
        ap5_blocked = True
        dll_detected = False

    # ── Trade decision: DLL ONLY ──
    if not dll_detected:
        return PatternResult(
            detected=False,
            pattern_id=PATTERN_ID,
            details={
                "source": "DLL",
                "ap5_blocked": ap5_blocked,
                "dll_raw_detected": current.hfe_detected,
                "python_audit": {
                    "detected": py_result["detected"],
                    "direction": py_result["direction"],
                },
            },
        )

    entry_price = current.close
    # ATR-based stop (W-6)
    if direction == "LONG":
        swing_anchor = min(b.low for b in bars[-min(LOOKBACK, len(bars)):])
    else:
        swing_anchor = max(b.high for b in bars[-min(LOOKBACK, len(bars)):])
    atr_ticks = _compute_atr14_ticks(bars)
    if atr_ticks > 0:
        stop_result = compute_stop(
            direction=direction, entry_bar=current, swing_anchor=swing_anchor,
            pattern_group=_PATTERN_GROUP, atr_14=atr_ticks, tick_size=TICK_SIZE,
        )
        stop_price = stop_result.stop_price
        stop_layer = stop_result.layer_applied
    else:
        if direction == "LONG":
            stop_price = current.low - STOP_TICKS * TICK_SIZE
        else:
            stop_price = current.high + STOP_TICKS * TICK_SIZE
        stop_layer = "primary"

    if direction == "LONG":
        targets = [entry_price + TARGET1_TICKS * TICK_SIZE, entry_price + TARGET2_TICKS * TICK_SIZE]
    else:
        targets = [entry_price - TARGET1_TICKS * TICK_SIZE, entry_price - TARGET2_TICKS * TICK_SIZE]

    r_t1 = _compute_r_t1(entry_price, stop_price)

    return PatternResult(
        detected=True,
        pattern_id=PATTERN_ID,
        group=GROUP,
        direction=direction,
        confidence=dll_confidence,
        raw_confidence=dll_confidence,
        r_t1=r_t1,
        entry_price=entry_price,
        stop=stop_price,
        targets=targets,
        cci_at_signal=cci_now,
        bar_index=len(bars) - 1,
        ts=0,
        details={
            "source": "DLL",
            "hfe_extreme_bars_ago": dll_bars_ago,
            "ap5_blocked": False,
            "stop_layer_applied": stop_layer,
            "python_audit": {
                "detected": py_result["detected"],
                "direction": py_result["direction"],
                "confidence": py_result["confidence"],
            },
            "reasoning_notes": (
                f"HFE {dll_direction_raw}: DLL detected, extreme {dll_bars_ago} bars ago, "
                f"CCI={cci_now:.0f}"
            ),
        },
    )
