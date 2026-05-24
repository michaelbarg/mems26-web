"""Targets per Day Type — Constitution V3 Part 1 Layer 4 + EXIT_V6 + D-091.Q1.

Exports get_targets(day_type) for L4 BarLevelDetector and TradingGateway
to compute T1/T2/T3 price levels and time stops.

Each target is expressed in R-multiples (risk units) relative to stop distance.
Time stops are in minutes from entry.

| Day Type        | T1   | T2        | T3        | Time Stop |
|-----------------|------|-----------|-----------|-----------|
| Trend Normal    | 1R   | 2R+TPO    | 4R+trail  | none      |
| Trend DD        | 1R   | open      | 4R cap    | 90min     |
| Variation       | 1R   | 2.5R      | trail     | 60min     |
| Normal          | 1R   | POC       | NO T3     | 30min     |
| Neutral Extreme | 1R   | extreme   | NO T3     | 45min     |
| Neutral Center  | 1R   | extreme   | NO T3     | 30min     |
| Nontrend        | n/a  | n/a       | n/a       | NO TRADE  |
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DAY_TYPES = {
    "Trend_Normal", "Trend_DD", "Variation", "Normal",
    "Neutral_Extreme", "Neutral_Center",
    "Nontrend",
}

# Canonical target definitions per V3 Layer 4 + EXIT_V6
_TARGETS: Dict[str, Dict] = {
    "Trend_Normal": {
        "t1": "1R",
        "t1_r": 1.0,
        "t2": "2R+TPO",
        "t2_r": 2.0,
        "t3": "4R+trail",
        "t3_r": 4.0,
        "time_stop_minutes": None,
        "trail_after_t2": True,
        "sizing": "AGGRESSIVE",
        "contracts": 3,
        "no_trade": False,
        "reasoning_notes": "Trend Normal: full 3-contract bracket, no time stop, trail after T2",
    },
    "Trend_DD": {
        "t1": "1R",
        "t1_r": 1.0,
        "t2": "open",
        "t2_r": None,  # open-ended, capped at 4R
        "t3": "4R cap",
        "t3_r": 4.0,
        "time_stop_minutes": 90,
        "trail_after_t2": False,
        "sizing": "AGGRESSIVE",
        "contracts": 3,
        "no_trade": False,
        "reasoning_notes": "Trend DD: T2 open-ended, T3 capped 4R, 90min time stop",
    },
    "Variation": {
        "t1": "1R",
        "t1_r": 1.0,
        "t2": "2.5R",
        "t2_r": 2.5,
        "t3": "trail",
        "t3_r": None,  # trail only
        "time_stop_minutes": 60,
        "trail_after_t2": True,
        "sizing": "FULL",
        "contracts": 2,
        "no_trade": False,
        "reasoning_notes": "Variation: 2 contracts, T3 trail only, 60min time stop",
    },
    "Normal": {
        "t1": "1R",
        "t1_r": 1.0,
        "t2": "POC",
        "t2_r": None,  # POC-based, not R-based
        "t3": None,
        "t3_r": None,
        "time_stop_minutes": 30,
        "trail_after_t2": False,
        "sizing": "HALF",
        "contracts": 1,
        "no_trade": False,
        "reasoning_notes": "Normal: T2 at POC, no T3, 30min time stop",
    },
    "Neutral_Extreme": {
        "t1": "1R",
        "t1_r": 1.0,
        "t2": "extreme",
        "t2_r": None,
        "t3": None,
        "t3_r": None,
        "time_stop_minutes": 45,
        "trail_after_t2": False,
        "sizing": "HALF",
        "contracts": 1,
        "no_trade": False,
        "reasoning_notes": "NeuE (D-091.Q1): T2 at opposite extreme · 45min window · open at VA edge",
    },
    "Neutral_Center": {
        "t1": "1R",
        "t1_r": 1.0,
        "t2": "extreme",
        "t2_r": None,
        "t3": None,
        "t3_r": None,
        "time_stop_minutes": 30,
        "trail_after_t2": False,
        "sizing": "HALF",
        "contracts": 1,
        "no_trade": False,
        "reasoning_notes": "NeuC (D-091.Q1): T2 at opposite extreme · 30min window · open inside VA",
    },
    "Nontrend": {
        "t1": None,
        "t1_r": None,
        "t2": None,
        "t2_r": None,
        "t3": None,
        "t3_r": None,
        "time_stop_minutes": None,
        "trail_after_t2": False,
        "sizing": None,
        "contracts": 0,
        "no_trade": True,
        "reasoning_notes": "NT: NO TRADE per EXIT_V6 + D-091 Coverage Matrix",
    },
}

# Aliases for enum-style keys (Trend_Normal vs TREND_NORMAL)
_ALIASES = {
    "TREND_NORMAL": "Trend_Normal",
    "TREND_DD": "Trend_DD",
    "VARIATION": "Variation",
    "NORMAL": "Normal",
    "NORMAL_DAY": "Normal",
    "NEUTRAL": "Neutral_Center",
    "NEUTRAL_CENTER": "Neutral_Center",
    "NEUTRAL_EXTREME": "Neutral_Extreme",
    "NEUE": "Neutral_Extreme",
    "NEUC": "Neutral_Center",
    "NONTREND": "Nontrend",
}

_neutral_deprecation_logged = False


def _log_deprecated_neutral_once() -> None:
    global _neutral_deprecation_logged
    if not _neutral_deprecation_logged:
        logger.warning(
            "[targets_table] DEPRECATED day_type='Neutral' · mapped to Neutral_Center · "
            "update caller per D-091.Q1"
        )
        _neutral_deprecation_logged = True


def get_targets(day_type: str) -> Optional[Dict]:
    """Return target configuration for a given day type.

    Accepts both enum-style (Trend_Normal) and uppercase (TREND_NORMAL) keys.
    Legacy 'Neutral' maps to Neutral_Center with deprecation warning.
    Returns None for unknown day types (explicit, no fallback per §6.7).
    """
    upper = day_type.upper().replace(" ", "_")
    canonical = _ALIASES.get(upper, day_type)

    # Legacy Neutral → NeuC with deprecation log
    if day_type == "Neutral" or upper == "NEUTRAL":
        _log_deprecated_neutral_once()
        canonical = "Neutral_Center"

    return _TARGETS.get(canonical)


def resolve_trail_config(day_type: str, pattern_name: Optional[str]) -> dict:
    """Resolve trail config with pattern override (D-094 §3.A hybrid).

    If (day_type, pattern_family) has an override, merge it on top of the
    base targets_table config. Otherwise return base config unchanged.
    """
    from backend.v9.systems.five_min.atr_caps import (
        TRAIL_OVERRIDE_BY_PATTERN,
        _pattern_to_family,
    )
    base = _TARGETS.get(day_type, {}).copy()
    if pattern_name is None:
        return base
    family = _pattern_to_family(pattern_name)
    if family is None:
        return base
    override = TRAIL_OVERRIDE_BY_PATTERN.get((day_type, family))
    if override is None:
        return base
    base.update(override)
    return base
