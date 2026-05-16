"""HFE (Hook From Extreme) -- NEW_TREND pattern #9.

CCI(14) reaches ±200 within last 6-12 bars (EXTREME zone),
then hooks back toward zero line — price reversal candidate.

Direction:
  HFE UP:   CCI hit -200 or below, now hooking UP toward zero
  HFE DOWN: CCI hit +200 or above, now hooking DOWN toward zero

Category: NEW_TREND (with VEGAS, GHOST, FAMIR, HTLB)
Spec: MEMS26 Woodies Decision Tree V1, pattern #9 (A3)
"""

from typing import List, Optional
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult

PATTERN_ID = "HFE"
GROUP = "REVERSAL"  # NEW_TREND per spec → mapped to REVERSAL group
LOOKBACK = 12  # bars to search for extreme
EXTREME_THRESHOLD = 200  # CCI must reach ±200
HOOK_THRESHOLD = 50  # CCI must hook back at least this far from extreme
TICK_SIZE = 0.25
STOP_TICKS = 8
TARGET1_TICKS = 12
TARGET2_TICKS = 24


def detect(bars: List[WoodiesBar], context: Optional[dict] = None) -> Optional[PatternResult]:
    """Detect HFE pattern from WoodiesBar list.

    Per Decision Tree V1:
    - CCI(14) reaches ±200 within last 6-12 bars
    - Then hooks back toward zero line
    - Current CCI moving in hook direction (confirmation)

    Primary: reads hfe_detected/hfe_direction from DLL JSON (via WoodiesBar fields).
    Fallback: Python compute if DLL fields not populated.
    """
    if len(bars) < 4:
        return PatternResult(detected=False, pattern_id=PATTERN_ID)

    current = bars[-1]
    cci_now = current.cci_14

    # ── PRIMARY: DLL JSON detection (consistent with ZLR pattern) ──
    if getattr(current, 'hfe_detected', False) and getattr(current, 'hfe_direction', 'NONE') != 'NONE':
        direction = "LONG" if current.hfe_direction == "UP" else "SHORT"
        bars_ago = getattr(current, 'hfe_extreme_bars_ago', 0)
        entry_price = current.close
        if direction == "LONG":
            stop_price = current.low - STOP_TICKS * TICK_SIZE
            targets = [entry_price + TARGET1_TICKS * TICK_SIZE, entry_price + TARGET2_TICKS * TICK_SIZE]
        else:
            stop_price = current.high + STOP_TICKS * TICK_SIZE
            targets = [entry_price - TARGET1_TICKS * TICK_SIZE, entry_price - TARGET2_TICKS * TICK_SIZE]
        return PatternResult(
            detected=True,
            pattern_id=PATTERN_ID,
            group=GROUP,
            direction=direction,
            confidence=0.7,
            entry_price=entry_price,
            stop=stop_price,
            targets=targets,
            cci_at_signal=cci_now,
            bar_index=len(bars) - 1,
            ts=0,
            details={
                "source": "DLL",
                "hfe_extreme_bars_ago": bars_ago,
                "reasoning_notes": f"HFE {current.hfe_direction}: DLL detected, extreme {bars_ago} bars ago, CCI={cci_now:.0f}",
            },
        )

    # ── FALLBACK: Python compute (if DLL fields not populated) ──
    cci_prev = bars[-2].cci_14
    search_window = bars[-min(LOOKBACK, len(bars)):]
    cci_history = [b.cci_14 for b in search_window]

    max_cci = max(cci_history)
    min_cci = min(cci_history)

    # Find which bar had the extreme
    max_idx = cci_history.index(max_cci)
    min_idx = cci_history.index(min_cci)

    # HFE UP: hit -200 or below, now hooking up
    if min_cci <= -EXTREME_THRESHOLD:
        bars_since_extreme = len(cci_history) - 1 - min_idx
        if 2 <= bars_since_extreme <= LOOKBACK:
            hook_distance = cci_now - min_cci
            if hook_distance >= HOOK_THRESHOLD and cci_now > cci_prev:
                entry_price = current.close
                stop_price = current.low - STOP_TICKS * TICK_SIZE
                return PatternResult(
                    detected=True,
                    pattern_id=PATTERN_ID,
                    group=GROUP,
                    direction="LONG",
                    confidence=min(0.8, 0.5 + hook_distance / 400),
                    entry_price=entry_price,
                    stop=stop_price,
                    targets=[entry_price + TARGET1_TICKS * TICK_SIZE, entry_price + TARGET2_TICKS * TICK_SIZE],
                    cci_at_signal=cci_now,
                    bar_index=len(bars) - 1,
                    ts=0,
                    details={
                        "source": "Python_fallback", "extreme_cci": round(min_cci, 2),
                        "hook_distance": round(hook_distance, 2),
                        "bars_since_extreme": bars_since_extreme,
                        "reasoning_notes": (
                            f"HFE UP: CCI hit {min_cci:.0f} ({bars_since_extreme} bars ago), "
                            f"hooked back to {cci_now:.0f} (distance {hook_distance:.0f})"
                        ),
                    },
                )

    # HFE DOWN: hit +200 or above, now hooking down
    if max_cci >= EXTREME_THRESHOLD:
        bars_since_extreme = len(cci_history) - 1 - max_idx
        if 2 <= bars_since_extreme <= LOOKBACK:
            hook_distance = max_cci - cci_now
            if hook_distance >= HOOK_THRESHOLD and cci_now < cci_prev:
                entry_price = current.close
                stop_price = current.high + STOP_TICKS * TICK_SIZE
                return PatternResult(
                    detected=True,
                    pattern_id=PATTERN_ID,
                    group=GROUP,
                    direction="SHORT",
                    confidence=min(0.8, 0.5 + hook_distance / 400),
                    entry_price=entry_price,
                    stop=stop_price,
                    targets=[entry_price - TARGET1_TICKS * TICK_SIZE, entry_price - TARGET2_TICKS * TICK_SIZE],
                    cci_at_signal=cci_now,
                    bar_index=len(bars) - 1,
                    ts=0,
                    details={
                        "source": "Python_fallback", "extreme_cci": round(max_cci, 2),
                        "hook_distance": round(hook_distance, 2),
                        "bars_since_extreme": bars_since_extreme,
                        "reasoning_notes": (
                            f"HFE DOWN: CCI hit {max_cci:.0f} ({bars_since_extreme} bars ago), "
                            f"hooked back to {cci_now:.0f} (distance {hook_distance:.0f})"
                        ),
                    },
                )

    return PatternResult(detected=False, pattern_id=PATTERN_ID)
