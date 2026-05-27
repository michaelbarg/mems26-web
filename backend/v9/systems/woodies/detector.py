"""Woodies CCI pattern detector — runs all 8 legacy patterns against bar history.

DEPRECATED (W-6): Use pattern_engine.py / detect_all_patterns() for the canonical
9-pattern WoodiesBar interface. This module is retained for api.py backward
compatibility only. Migration to pattern_engine.py is planned for Phase B.
"""

from typing import List, Optional
from backend.v9.systems.woodies.cci_calc import (
    calc_cci_series, calc_ema_series, compute_all_studies,
)
from backend.v9.systems.woodies.schemas import PatternSignal, WoodiesState
from backend.v9.systems.woodies.patterns import ALL_DETECTORS


def detect_patterns(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    timestamps: List[float],
) -> List[PatternSignal]:
    """Run all 8 pattern detectors on the bar history.

    Returns list of detected patterns (may be empty).
    """
    n = len(closes)
    if n < 14:
        return []

    cci14_series = calc_cci_series(highs, lows, closes, 14)
    cci6_series = calc_cci_series(highs, lows, closes, 6)
    studies = compute_all_studies(highs, lows, closes)
    trend_state = studies["trend_state"]

    bar_index = n - 1
    ts = timestamps[-1] if timestamps else 0

    signals = []
    for detector in ALL_DETECTORS:
        result = detector(
            cci_history=cci14_series,
            bar_index=bar_index,
            ts=ts,
            cci6_history=cci6_series,
            trend_state=trend_state,
            price_closes=closes,
        )
        if result is not None:
            signals.append(result)

    return signals


def compute_state(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    timestamps: List[float],
) -> WoodiesState:
    """Compute current Woodies state including all studies and active patterns."""
    studies = compute_all_studies(highs, lows, closes)
    patterns = detect_patterns(highs, lows, closes, timestamps)

    # Classification logic
    classification = "NO_SETUP"
    direction = "NEUTRAL"

    if patterns:
        continuations = [p for p in patterns if p.group == "CONTINUATION"]
        reversals = [p for p in patterns if p.group == "REVERSAL"]

        if continuations and studies["trend_state"] in ("BLUE", "RED"):
            classification = "STRATEGIC"
            direction = continuations[0].direction
        elif continuations:
            classification = "TACTICAL"
            direction = continuations[0].direction
        elif reversals:
            classification = "TACTICAL"
            direction = reversals[0].direction

        # Boost to STRATEGIC if multiple patterns agree
        if len(patterns) >= 2:
            dirs = set(p.direction for p in patterns)
            if len(dirs) == 1:
                classification = "STRATEGIC"

    return WoodiesState(
        cci_14=studies["cci_14"],
        cci_6_tcci=studies["cci_6_tcci"],
        ema_34=studies["ema_34"],
        lsma_value=studies["lsma_value"],
        swi_value=studies["swi_value"],
        czi_value=studies["czi_value"],
        trend_state=studies["trend_state"],
        predictor_next_cci=studies["predictor_next_cci"],
        active_patterns=patterns,
        classification=classification,
        direction=direction,
    )
