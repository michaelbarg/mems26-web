"""Day Type x Pattern Trade Management Matrix (V3.0 spec Section 3).

Lookup: (day_type, pattern_id, direction) -> TradeManagement config.
Also handles First Hour Matrix (V3.3) when is_first_hour=True.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class TradeManagement:
    """Output of matrix lookup."""
    t1_reason: str
    t1_contracts: int = 1
    t1_price: Optional[float] = None
    t1_level: Optional[str] = None
    t2_reason: Optional[str] = None
    t2_contracts: int = 0
    t3_reason: Optional[str] = None
    t3_contracts: int = 0
    time_stop_min: Optional[int] = None
    sizing: str = "HALF"         # MIN, HALF, FULL
    blocked: bool = False
    block_reason: str = ""


# ─── Day Type Matrix (V3.0 Section 3) ───────────────────────

_TREND_NORMAL = {
    # Initiative continuation — full targets, Vegas trail
    ("initiative_buyer", "LONG"): TradeManagement(
        t1_reason="momentum_push", t1_contracts=1,
        t2_reason="previous_high_pdh", t2_contracts=1,
        t3_reason="trail_vegas_ema", t3_contracts=1,
        sizing="FULL",
    ),
    ("initiative_seller", "SHORT"): TradeManagement(
        t1_reason="momentum_push", t1_contracts=1,
        t2_reason="previous_low_pdl", t2_contracts=1,
        t3_reason="trail_vegas_ema", t3_contracts=1,
        sizing="FULL",
    ),
    # Reactive AGAINST trend = Suffering Side
    ("reactive_buyer", "LONG"): TradeManagement(
        t1_reason="", blocked=True, block_reason="Suffering Side — reactive against trend",
    ),
    ("reactive_seller", "SHORT"): TradeManagement(
        t1_reason="", blocked=True, block_reason="Suffering Side — reactive against trend",
    ),
    # Flags/Pennants continuation
    ("bull_flag", "LONG"): TradeManagement(
        t1_reason="pole_projection", t1_contracts=1,
        t2_reason="previous_high", t2_contracts=1,
        t3_reason="trail_vegas", t3_contracts=1,
        sizing="FULL",
    ),
    ("bear_flag", "SHORT"): TradeManagement(
        t1_reason="pole_projection", t1_contracts=1,
        t2_reason="previous_low", t2_contracts=1,
        t3_reason="trail_vegas", t3_contracts=1,
        sizing="FULL",
    ),
    ("bull_pennant", "LONG"): TradeManagement(
        t1_reason="pole_projection", t1_contracts=1,
        t2_reason="previous_high", t2_contracts=1,
        t3_reason="trail_vegas", t3_contracts=1,
        sizing="FULL",
    ),
    ("bear_pennant", "SHORT"): TradeManagement(
        t1_reason="pole_projection", t1_contracts=1,
        t2_reason="previous_low", t2_contracts=1,
        t3_reason="trail_vegas", t3_contracts=1,
        sizing="FULL",
    ),
}

_VARIATION = {
    ("reactive_buyer", "LONG"): TradeManagement(
        t1_reason="poc_tpo_vwap", t1_contracts=1,
        t2_reason="opposite_extreme_ib", t2_contracts=2,
        time_stop_min=60, sizing="FULL",
    ),
    ("reactive_seller", "SHORT"): TradeManagement(
        t1_reason="poc_tpo_vwap", t1_contracts=1,
        t2_reason="opposite_extreme_ib", t2_contracts=2,
        time_stop_min=60, sizing="FULL",
    ),
    ("double_bottom", "LONG"): TradeManagement(
        t1_reason="neckline", t1_contracts=1,
        t2_reason="pattern_projection", t2_contracts=2,
        sizing="FULL",
    ),
    ("double_top", "SHORT"): TradeManagement(
        t1_reason="neckline", t1_contracts=1,
        t2_reason="pattern_projection", t2_contracts=2,
        sizing="FULL",
    ),
    # Initiative on Variation = CAUTION
    ("initiative_buyer", "LONG"): TradeManagement(
        t1_reason="momentum_push", t1_contracts=1,
        sizing="HALF",
    ),
    ("initiative_seller", "SHORT"): TradeManagement(
        t1_reason="momentum_push", t1_contracts=1,
        sizing="HALF",
    ),
}

_NORMAL = {
    ("reactive_buyer", "LONG"): TradeManagement(
        t1_reason="poc", t1_contracts=1,
        t2_reason="opposite_side_vah", t2_contracts=2,
        time_stop_min=30, sizing="HALF",
    ),
    ("reactive_seller", "SHORT"): TradeManagement(
        t1_reason="poc", t1_contracts=1,
        t2_reason="opposite_side_val", t2_contracts=2,
        time_stop_min=30, sizing="HALF",
    ),
}

_TREND_DD = {
    ("initiative_buyer", "LONG"): TradeManagement(
        t1_reason="first_dist_edge", t1_contracts=1,
        t2_reason="second_dist_center", t2_contracts=1,
        t3_reason="second_dist_edge", t3_contracts=1,
        sizing="FULL",
    ),
    ("initiative_seller", "SHORT"): TradeManagement(
        t1_reason="first_dist_edge", t1_contracts=1,
        t2_reason="second_dist_center", t2_contracts=1,
        t3_reason="second_dist_edge", t3_contracts=1,
        sizing="FULL",
    ),
    ("reactive_buyer", "LONG"): TradeManagement(
        t1_reason="first_dist_center", t1_contracts=1,
        t2_reason="first_dist_edge", t2_contracts=1,
        sizing="FULL",
    ),
    ("reactive_seller", "SHORT"): TradeManagement(
        t1_reason="first_dist_center", t1_contracts=1,
        t2_reason="first_dist_edge", t2_contracts=1,
        sizing="FULL",
    ),
}

_NEUTRAL = {
    ("reactive_buyer", "LONG"): TradeManagement(
        t1_reason="poc_return", t1_contracts=1,
        time_stop_min=30, sizing="HALF",
    ),
    ("reactive_seller", "SHORT"): TradeManagement(
        t1_reason="poc_return", t1_contracts=1,
        time_stop_min=30, sizing="HALF",
    ),
}

_NONTREND = {
    # Tiny scalps only — strategic trades blocked
    ("reactive_buyer", "LONG"): TradeManagement(
        t1_reason="3_5_ticks", t1_contracts=1,
        time_stop_min=20, sizing="MIN",
    ),
    ("reactive_seller", "SHORT"): TradeManagement(
        t1_reason="3_5_ticks", t1_contracts=1,
        time_stop_min=20, sizing="MIN",
    ),
}

_DAY_TYPE_MATRIX = {
    "TREND_NORMAL": _TREND_NORMAL,
    "TREND_DD": _TREND_DD,
    "VARIATION": _VARIATION,
    "NORMAL": _NORMAL,
    "NEUTRAL": _NEUTRAL,
    "NONTREND": _NONTREND,
}


# ─── First Hour Matrix (V3.3) ───────────────────────────────

_FIRST_HOUR = {
    ("OPEN_DRIVE", "initiative_buyer", "LONG"): TradeManagement(
        t1_reason="momentum_push", t1_contracts=1,
        t2_reason="range_projection", t2_contracts=1,
        time_stop_min=30, sizing="HALF",
    ),
    ("OPEN_DRIVE", "initiative_seller", "SHORT"): TradeManagement(
        t1_reason="momentum_push", t1_contracts=1,
        t2_reason="range_projection", t2_contracts=1,
        time_stop_min=30, sizing="HALF",
    ),
    ("OPEN_DRIVE", "bull_flag", "LONG"): TradeManagement(
        t1_reason="pole_projection", t1_contracts=1,
        t2_reason="range_projection", t2_contracts=1,
        sizing="HALF",
    ),
    ("OPEN_DRIVE", "bear_flag", "SHORT"): TradeManagement(
        t1_reason="pole_projection", t1_contracts=1,
        t2_reason="range_projection", t2_contracts=1,
        sizing="HALF",
    ),
    ("OPEN_TEST_DRIVE", "reactive_buyer", "LONG"): TradeManagement(
        t1_reason="poc_vwap", t1_contracts=1,
        t2_reason="opposite_extreme", t2_contracts=1,
        time_stop_min=30, sizing="HALF",
    ),
    ("OPEN_TEST_DRIVE", "reactive_seller", "SHORT"): TradeManagement(
        t1_reason="poc_vwap", t1_contracts=1,
        t2_reason="opposite_extreme", t2_contracts=1,
        time_stop_min=30, sizing="HALF",
    ),
    ("OPEN_REJECTION_REVERSE", "reactive_buyer", "LONG"): TradeManagement(
        t1_reason="poc", t1_contracts=1,
        time_stop_min=20, sizing="MIN",
    ),
    ("OPEN_REJECTION_REVERSE", "reactive_seller", "SHORT"): TradeManagement(
        t1_reason="poc", t1_contracts=1,
        time_stop_min=20, sizing="MIN",
    ),
    ("OPEN_AUCTION_IN_RANGE", "reactive_buyer", "LONG"): TradeManagement(
        t1_reason="3_5_ticks", t1_contracts=1,
        time_stop_min=15, sizing="MIN",
    ),
    ("OPEN_AUCTION_IN_RANGE", "reactive_seller", "SHORT"): TradeManagement(
        t1_reason="3_5_ticks", t1_contracts=1,
        time_stop_min=15, sizing="MIN",
    ),
    ("OPEN_AUCTION_OUT_OF_RANGE", "initiative_buyer", "LONG"): TradeManagement(
        t1_reason="initial_dist_edge", t1_contracts=1,
        time_stop_min=30, sizing="HALF",
    ),
    ("OPEN_AUCTION_OUT_OF_RANGE", "initiative_seller", "SHORT"): TradeManagement(
        t1_reason="initial_dist_edge", t1_contracts=1,
        time_stop_min=30, sizing="HALF",
    ),
}


# ─── Public API ──────────────────────────────────────────────

def lookup_matrix(
    day_type: str,
    pattern_id: str,
    direction: str,
    is_first_hour: bool = False,
    opening_type: Optional[str] = None,
) -> TradeManagement:
    """Look up trade management rules from the matrix.

    Returns TradeManagement with blocked=True if the combination
    is not allowed (e.g. reactive against trend, strategic in first hour).
    """
    # First hour uses its own matrix
    if is_first_hour and opening_type:
        key = (opening_type, pattern_id, direction)
        result = _FIRST_HOUR.get(key)
        if result:
            # First hour: NO T3, NO STRATEGIC
            return TradeManagement(
                t1_reason=result.t1_reason,
                t1_contracts=result.t1_contracts,
                t2_reason=result.t2_reason,
                t2_contracts=result.t2_contracts,
                t3_reason=None,  # always off in first hour
                t3_contracts=0,
                time_stop_min=result.time_stop_min,
                sizing=result.sizing,
            )
        # Pattern/opening combo not in first hour matrix
        return TradeManagement(
            t1_reason="", blocked=True,
            block_reason=f"No first-hour entry for {opening_type} x {pattern_id}",
        )

    # Post-lock: Day Type matrix
    dt_matrix = _DAY_TYPE_MATRIX.get(day_type, {})

    # Try exact match
    result = dt_matrix.get((pattern_id, direction))
    if result:
        return result

    # For patterns not explicitly in the matrix, provide defaults based on group
    # Group A patterns map to their reactive/initiative counterparts
    # Group B/C geometric patterns get moderate defaults
    if day_type == "NONTREND":
        return TradeManagement(
            t1_reason="", t1_contracts=0,
            time_stop_min=20, sizing="MIN",
            blocked=True,
            block_reason="NONTREND blocks strategic pattern",
        )

    return TradeManagement(
        t1_reason="pattern_target", t1_contracts=1,
        t2_reason="pattern_projection", t2_contracts=1,
        sizing="HALF",
    )


def classify_opportunity(confluence_score: int, is_first_hour: bool = False) -> str:
    """Classify setup per V3.1 spec.

    First hour: never STRATEGIC (V3.3).
    """
    if is_first_hour:
        if confluence_score >= 4:
            return "TACTICAL_PLUS"  # best you can get in first hour
        elif confluence_score >= 2:
            return "TACTICAL_PLUS"
        return "TACTICAL"

    if confluence_score >= 4:
        return "STRATEGIC"
    elif confluence_score >= 2:
        return "TACTICAL_PLUS"
    return "TACTICAL"


def sizing_for_classification(classification: str) -> str:
    """Map classification to sizing rule."""
    return {
        "TACTICAL": "MIN",
        "TACTICAL_PLUS": "HALF",
        "STRATEGIC": "FULL",
    }.get(classification, "MIN")
