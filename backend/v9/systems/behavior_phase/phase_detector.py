"""Behavior Phase Detector — Layer 2 Observing (advisory, NOT firing).

Classifies market behavior phase from recent bar structure:
  DEVELOPMENT: range-building, low directional commitment
  MATURE:      trend established, extensions from IB
  REVERSAL:    exhaustion signals, failed extensions
  TRANSITION:  phase boundary, mixed signals

Triggered every 5-min bar close. Firing systems read as advisory context.
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BehaviorPhase(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    MATURE = "MATURE"
    REVERSAL = "REVERSAL"
    TRANSITION = "TRANSITION"


@dataclass
class PhaseResult:
    phase: BehaviorPhase
    confidence: float  # 0.0-1.0
    reasoning_notes: str
    indicators: Dict


def detect_phase(
    bars: List[Dict],
    ib_high: Optional[float] = None,
    ib_low: Optional[float] = None,
    poc: Optional[float] = None,
) -> PhaseResult:
    """Detect current behavior phase from recent 5-min bars + TPO context.

    Args:
        bars: last 20+ bars (oldest first), each with o/h/l/c/v keys
        ib_high: IB high from TPO (optional)
        ib_low: IB low from TPO (optional)
        poc: current POC (optional)

    Returns:
        PhaseResult with phase classification + confidence + reasoning
    """
    if not bars or len(bars) < 5:
        return PhaseResult(
            phase=BehaviorPhase.DEVELOPMENT,
            confidence=0.0,
            reasoning_notes="Insufficient bars for phase detection",
            indicators={},
        )

    # Compute indicators from bar structure
    recent = bars[-10:] if len(bars) >= 10 else bars
    highs = [b.get("h", b.get("high", 0)) for b in recent]
    lows = [b.get("l", b.get("low", 0)) for b in recent]
    closes = [b.get("c", b.get("close", 0)) for b in recent]
    volumes = [b.get("v", b.get("volume", 0)) for b in recent]

    # Range expansion rate: are highs getting higher / lows getting lower?
    range_expanding = highs[-1] > max(highs[:-1]) or lows[-1] < min(lows[:-1]) if len(highs) > 1 else False

    # Directional bias: close position in range
    range_size = max(highs) - min(lows) if highs and lows else 1
    close_position = (closes[-1] - min(lows)) / max(range_size, 0.01) if closes else 0.5

    # Volume trend: increasing or decreasing
    vol_first_half = sum(volumes[:len(volumes)//2]) if volumes else 1
    vol_second_half = sum(volumes[len(volumes)//2:]) if volumes else 1
    vol_increasing = vol_second_half > vol_first_half * 1.1

    # IB extension check
    ib_extended_up = highs[-1] > ib_high if ib_high and highs else False
    ib_extended_down = lows[-1] < ib_low if ib_low and lows else False
    ib_both_sides = ib_extended_up and ib_extended_down

    # POC proximity: is price near POC (consolidation)?
    poc_near = abs(closes[-1] - poc) < range_size * 0.15 if poc and closes and range_size > 0 else False

    # Higher highs / higher lows count (trend strength)
    hh_count = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
    hl_count = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i-1])
    ll_count = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])

    indicators = {
        "range_expanding": range_expanding,
        "close_position": round(close_position, 3),
        "vol_increasing": vol_increasing,
        "ib_extended_up": ib_extended_up,
        "ib_extended_down": ib_extended_down,
        "ib_both_sides": ib_both_sides,
        "poc_near": poc_near,
        "hh_count": hh_count,
        "hl_count": hl_count,
        "ll_count": ll_count,
    }

    # Classification logic (order matters: check exhaustion before trend)
    if range_expanding and not vol_increasing:
        phase = BehaviorPhase.REVERSAL
        conf = 0.5
        reason = f"Exhaustion possible: range expanding but volume declining"
    elif ib_both_sides and not vol_increasing and poc_near:
        phase = BehaviorPhase.TRANSITION
        conf = 0.6
        reason = f"Both IB sides breached, volume declining, price near POC → transition"
    elif (hh_count >= 3 and hl_count >= 3) or (ll_count >= 3 and hh_count <= 1):
        if vol_increasing and range_expanding:
            phase = BehaviorPhase.MATURE
            conf = 0.8
            reason = f"Trend mature: {hh_count}HH+{hl_count}HL, volume rising, range expanding"
        elif vol_increasing:
            phase = BehaviorPhase.MATURE
            conf = 0.6
            reason = f"Trend developing: {hh_count}HH+{hl_count}HL, volume rising"
        else:
            phase = BehaviorPhase.DEVELOPMENT
            conf = 0.5
            reason = f"Trend structure but no volume confirmation"
    elif not range_expanding and poc_near and not vol_increasing:
        phase = BehaviorPhase.DEVELOPMENT
        conf = 0.7
        reason = f"Range building: no expansion, near POC, volume flat"
    else:
        phase = BehaviorPhase.DEVELOPMENT
        conf = 0.4
        reason = f"Default: mixed signals (pos={close_position:.2f}, hh={hh_count}, vol_up={vol_increasing})"

    logger.debug("[BehaviorPhase] %s (%.0f%%) — %s", phase.value, conf * 100, reason)

    return PhaseResult(
        phase=phase,
        confidence=conf,
        reasoning_notes=reason,
        indicators=indicators,
    )
