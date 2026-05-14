"""Targets per Day Type — Constitution V3 Part 1 Layer 4.

Exports get_targets(day_type) for L4 BarLevelDetector and TradingGateway
to compute T1/T2/T3 price levels and time stops.

Each target is expressed in R-multiples (risk units) relative to stop distance.
Time stops are in minutes from entry.

| Day Type      | T1   | T2        | T3        | Time Stop |
|---------------|------|-----------|-----------|-----------|
| Trend Normal  | 1R   | 2R+TPO    | 4R+trail  | none      |
| Trend DD      | 1R   | open      | 4R cap    | 90min     |
| Variation     | 1R   | 2.5R      | trail     | 60min     |
| Normal        | 1R   | POC       | NO T3     | 30min     |
| Neutral       | 1R   | extreme   | NO T3     | 45min     |
| Nontrend      | 1R   | NO T2     | NO T3     | 20min     |
"""

from typing import Dict, Optional


DAY_TYPES = {
    "Trend_Normal", "Trend_DD", "Variation",
    "Normal", "Neutral", "Nontrend",
}

# Canonical target definitions per V3 Layer 4
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
        "reasoning_notes": "Normal: T2 at POC, no T3, 30min time stop",
    },
    "Neutral": {
        "t1": "1R",
        "t1_r": 1.0,
        "t2": "extreme",
        "t2_r": None,  # extreme-based
        "t3": None,
        "t3_r": None,
        "time_stop_minutes": 45,
        "trail_after_t2": False,
        "sizing": "HALF",
        "contracts": 1,
        "reasoning_notes": "Neutral: T2 at extreme, no T3, 45min time stop",
    },
    "Nontrend": {
        "t1": "1R",
        "t1_r": 1.0,
        "t2": None,
        "t2_r": None,
        "t3": None,
        "t3_r": None,
        "time_stop_minutes": 20,
        "trail_after_t2": False,
        "sizing": "MIN",
        "contracts": 1,
        "reasoning_notes": "Nontrend: T1 only, no T2/T3, 20min time stop",
    },
}

# Aliases for enum-style keys (Trend_Normal vs TREND_NORMAL)
_ALIASES = {
    "TREND_NORMAL": "Trend_Normal",
    "TREND_DD": "Trend_DD",
    "VARIATION": "Variation",
    "NORMAL": "Normal",
    "NORMAL_DAY": "Normal",
    "NEUTRAL": "Neutral",
    "NONTREND": "Nontrend",
}


def get_targets(day_type: str) -> Optional[Dict]:
    """Return target configuration for a given day type.

    Accepts both enum-style (Trend_Normal) and uppercase (TREND_NORMAL) keys.
    Returns None for unknown day types (explicit, no fallback per §6.7).
    """
    canonical = _ALIASES.get(day_type.upper().replace(" ", "_"), day_type)
    return _TARGETS.get(canonical)
