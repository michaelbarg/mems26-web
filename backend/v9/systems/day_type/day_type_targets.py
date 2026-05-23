"""day_type_targets — resolve R-based targets to actual prices per day type.

Reads from targets_table.get_targets() · returns gateway-ready price scheme.
Per D-091.Q1 + EXIT_V6 (7 day types: TN/TDD/V/N/NeuE/NeuC/NT).
"""
from __future__ import annotations
import logging
from typing import Optional, Dict, Any, Literal
from backend.v9.systems.day_type.targets_table import get_targets

logger = logging.getLogger(__name__)


def compute_targets_for_day_type(
    *,
    day_type: Optional[str],
    entry_price: float,
    stop_price: float,
    direction: Literal["LONG", "SHORT"],
) -> Optional[Dict[str, Any]]:
    """Resolve targets for a day type to actual prices.

    Returns dict with t1/t2/t3 prices, time_stop, sizing, no_trade flag.
    Returns None if day_type unknown OR R<=0.
    """
    if day_type is None:
        return None

    targets = get_targets(day_type)
    if targets is None:
        logger.warning(
            "[day_type_targets] unknown day_type=%s · returning None",
            day_type,
        )
        return None

    R = abs(entry_price - stop_price)
    if R <= 0:
        logger.warning(
            "[day_type_targets] non-positive R · entry=%.2f stop=%.2f",
            entry_price,
            stop_price,
        )
        return None

    sign = 1.0 if direction == "LONG" else -1.0

    t1_r = targets.get("t1_r")
    t2_r = targets.get("t2_r")
    t3_r = targets.get("t3_r")

    t1_price = entry_price + sign * float(t1_r) * R if isinstance(t1_r, (int, float)) else None
    t2_price = entry_price + sign * float(t2_r) * R if isinstance(t2_r, (int, float)) else None
    t3_price = entry_price + sign * float(t3_r) * R if isinstance(t3_r, (int, float)) else None

    return {
        "t1_price": t1_price,
        "t2_price": t2_price,
        "t3_price": t3_price,
        "time_stop_minutes": targets.get("time_stop_minutes"),
        "trail_after_t2": targets.get("trail_after_t2", False),
        "sizing_contracts": targets.get("contracts", 0),
        "no_trade": targets.get("no_trade", False),
        "day_type_canonical": _resolve_canonical(day_type),
    }


def _resolve_canonical(day_type: str) -> str:
    """Map alias/legacy to canonical day type string."""
    upper = day_type.upper().replace(" ", "_")
    aliases = {
        "NEUTRAL": "Neutral_Center",
        "NEUTRAL_CENTER": "Neutral_Center",
        "NEUTRAL_EXTREME": "Neutral_Extreme",
        "NEUE": "Neutral_Extreme",
        "NEUC": "Neutral_Center",
    }
    return aliases.get(upper, day_type)
