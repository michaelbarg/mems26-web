"""Unified Balance↔Imbalance toggle (Dalton Step 3).

Combines three signals into a single market-regime assessment:
  1. Day type (from classifier): Trend/Variation = IMBALANCE, Balance/Neutral = BALANCE
  2. Leg state (from radar): active leg in one direction = IMBALANCE signal
  3. 7-day VA overlap (from multiday composite): high overlap = BALANCE, low = IMBALANCE

Output: a single BALANCE / IMBALANCE / TRANSITIONAL verdict with confidence,
consumable by S2 and S4 fire paths. Pure detection — flag-gated for fire
influence (BALANCE_IMBALANCE_TOGGLE_V1, default OFF).

When BALANCE:  mean-reversion setups favored (S4 patterns, tighter stops)
When IMBALANCE: trend-following favored (S2 drives, wider stops, floor applies)
When TRANSITIONAL: both sides open, standard behavior
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToggleState:
    """Market regime assessment."""
    regime: str           # BALANCE / IMBALANCE / TRANSITIONAL
    confidence: float     # 0.0–1.0
    day_type_signal: str  # what the day type says
    leg_signal: str       # what the leg says
    overlap_signal: str   # what the 7-day overlap says
    detail: str


# Day types that signal imbalance
_IMBALANCE_TYPES = {"Trend_Normal", "Trend_DD", "Variation"}
_BALANCE_TYPES = {"Balance", "Neutral_Center", "Neutral_Extreme", "Normal_Variation"}


def assess_regime(
    *,
    day_type: Optional[str] = None,
    leg: Optional[str] = None,      # "UP" / "DOWN" / None
    va_overlap_pct: Optional[float] = None,  # 0-100% overlap of today's VA with 7-day VA
    opening_type: Optional[str] = None,
) -> ToggleState:
    """Assess the current market regime from available signals.

    Pure function. Missing inputs → TRANSITIONAL (Rule-1).
    """
    signals = []
    imbalance_votes = 0
    balance_votes = 0

    # 1. Day type signal
    dt = (day_type or "").strip()
    dt_family = dt.split("_")[0] if "_" in dt else dt
    if dt in _IMBALANCE_TYPES or dt_family in ("Trend", "Variation"):
        dt_signal = "IMBALANCE"
        imbalance_votes += 1
    elif dt in _BALANCE_TYPES or dt_family in ("Balance", "Neutral", "Normal"):
        dt_signal = "BALANCE"
        balance_votes += 1
    else:
        dt_signal = "UNKNOWN"
    signals.append(f"day_type={dt}→{dt_signal}")

    # 2. Leg signal
    if leg in ("UP", "DOWN"):
        leg_signal = "IMBALANCE"
        imbalance_votes += 1
    elif leg is None:
        leg_signal = "UNKNOWN"
    else:
        leg_signal = "BALANCE"
        balance_votes += 1
    signals.append(f"leg={leg}→{leg_signal}")

    # 3. VA overlap signal
    # High overlap (>60%) = value area stable → BALANCE
    # Low overlap (<30%) = value area shifting → IMBALANCE
    if va_overlap_pct is not None:
        if va_overlap_pct > 60:
            overlap_signal = "BALANCE"
            balance_votes += 1
        elif va_overlap_pct < 30:
            overlap_signal = "IMBALANCE"
            imbalance_votes += 1
        else:
            overlap_signal = "TRANSITIONAL"
    else:
        overlap_signal = "UNKNOWN"
    signals.append(f"overlap={va_overlap_pct}→{overlap_signal}")

    # 4. Opening type boost
    if opening_type and "DRIVE" in (opening_type or ""):
        imbalance_votes += 1
        signals.append(f"opening={opening_type}→IMBALANCE")

    # Verdict
    total_votes = imbalance_votes + balance_votes
    if total_votes == 0:
        regime = "TRANSITIONAL"
        confidence = 0.3
    elif imbalance_votes >= 2 and imbalance_votes > balance_votes:
        regime = "IMBALANCE"
        confidence = 0.5 + 0.15 * (imbalance_votes - balance_votes)
    elif balance_votes >= 2 and balance_votes > imbalance_votes:
        regime = "BALANCE"
        confidence = 0.5 + 0.15 * (balance_votes - imbalance_votes)
    else:
        regime = "TRANSITIONAL"
        confidence = 0.4

    confidence = min(confidence, 1.0)

    return ToggleState(
        regime=regime,
        confidence=round(confidence, 3),
        day_type_signal=dt_signal,
        leg_signal=leg_signal,
        overlap_signal=overlap_signal,
        detail="; ".join(signals),
    )


def assess_regime_live() -> Dict[str, Any]:
    """Live assessment from current system state. For radar/API.

    Reads day_type, leg, and VA overlap from the running system.
    Returns dict for JSON consumption. Never raises.
    """
    try:
        from backend.v9.db.read import read_one

        # Day type
        dt_row = read_one(
            "SELECT day_type, direction FROM v9_day_type_state "
            "ORDER BY ts DESC LIMIT 1", {},
        )
        day_type = dt_row.get("day_type") if dt_row else None
        direction = dt_row.get("direction", "") if dt_row else ""

        # Leg from direction
        leg = None
        if direction:
            import re
            m = re.search(r"\((UP|DOWN)\)", str(direction))
            if m:
                leg = m.group(1)

        # Opening type
        opening_type = None
        dt_row2 = read_one(
            "SELECT opening_type FROM v9_day_type_state "
            "ORDER BY ts DESC LIMIT 1", {},
        )
        if dt_row2:
            opening_type = dt_row2.get("opening_type")

        # VA overlap (from multiday if available)
        va_overlap = None
        try:
            from backend.v9.api.v9.context_multiday import multiday
            md = multiday()
            comp = md.get("composite", {})
            va_overlap = comp.get("va_overlap_pct")
        except Exception:
            pass

        state = assess_regime(
            day_type=day_type,
            leg=leg,
            va_overlap_pct=va_overlap,
            opening_type=opening_type,
        )

        return {
            "regime": state.regime,
            "confidence": state.confidence,
            "day_type_signal": state.day_type_signal,
            "leg_signal": state.leg_signal,
            "overlap_signal": state.overlap_signal,
            "detail": state.detail,
        }
    except Exception:
        return {"regime": "TRANSITIONAL", "confidence": 0.0, "detail": "error"}
