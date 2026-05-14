"""Per-zone playbook — preferred patterns + quality modifiers per killzone.

Constitution V3 Part 1 Layer 2 Killzone (S6).
Each zone has different volatility characteristics → different pattern
types perform better. This module provides read-only zone context
for firing systems to adjust signal evaluation.

NOT a composite scorer (CORR-23). Returns zone preferences that
firing systems can use as ONE input to their per-system internal sizing.
"""

from typing import Dict, List, Optional


# Per-zone configuration per V3 + compliance manifest
_ZONE_PLAYBOOK: Dict[str, Dict] = {
    "ASIA": {
        "preferred_patterns": ["REACTIVE"],
        "avoid_patterns": ["INITIATIVE", "BREAKOUT"],
        "quality_modifier": -0.15,  # lower quality zone for MES
        "volatility": "LOW",
        "sizing_cap": "HALF",  # max 2 contracts
        "notes": "Low volume session; reactive setups only, avoid breakouts",
        "reasoning_notes": "ASIA: low vol, reactive only, half size cap",
    },
    "LONDON": {
        "preferred_patterns": ["REACTIVE", "INITIATIVE"],
        "avoid_patterns": [],
        "quality_modifier": 0.0,  # neutral
        "volatility": "MEDIUM",
        "sizing_cap": "FULL",
        "notes": "Mixed; London open can drive MES via ES correlation",
        "reasoning_notes": "LONDON: mixed session, no restrictions",
    },
    "NY_PREMARKET": {
        "preferred_patterns": ["REACTIVE"],
        "avoid_patterns": ["INITIATIVE"],
        "quality_modifier": -0.05,
        "volatility": "MEDIUM",
        "sizing_cap": "FULL",
        "notes": "Pre-RTH; reactive only until 9:30 ET open",
        "reasoning_notes": "NY_PREMARKET: pre-RTH, reactive preferred",
    },
    "NY_OPEN": {
        "preferred_patterns": ["INITIATIVE", "BREAKOUT", "REACTIVE"],
        "avoid_patterns": [],
        "quality_modifier": 0.15,  # best quality zone
        "volatility": "HIGH",
        "sizing_cap": "FULL",
        "notes": "Prime session 9:30-11:30 ET; all patterns valid, initiative preferred",
        "reasoning_notes": "NY_OPEN: prime time, initiative + breakout preferred, quality boost",
    },
    "MIDDAY": {
        "preferred_patterns": ["REACTIVE"],
        "avoid_patterns": ["INITIATIVE", "BREAKOUT"],
        "quality_modifier": -0.20,  # worst quality zone
        "volatility": "LOW",
        "sizing_cap": "HALF",
        "notes": "Lunch hour; low vol, choppy, reactive only if at all",
        "reasoning_notes": "MIDDAY: low vol lunch, reactive only, half size, quality penalty",
    },
    "NY_PM": {
        "preferred_patterns": ["INITIATIVE", "REACTIVE"],
        "avoid_patterns": [],
        "quality_modifier": 0.10,  # good quality zone
        "volatility": "MEDIUM",
        "sizing_cap": "FULL",
        "notes": "PM session 13:30-16:00 ET; day extension trades, trail runners",
        "reasoning_notes": "NY_PM: good session, day extension + trail, quality boost",
    },
    "POST_MARKET": {
        "preferred_patterns": [],
        "avoid_patterns": ["INITIATIVE", "BREAKOUT", "REACTIVE"],
        "quality_modifier": -0.30,
        "volatility": "LOW",
        "sizing_cap": "MIN",
        "notes": "Post-market; generally avoid new entries",
        "reasoning_notes": "POST_MARKET: avoid new entries, close only",
    },
    "CLOSED": {
        "preferred_patterns": [],
        "avoid_patterns": ["INITIATIVE", "BREAKOUT", "REACTIVE"],
        "quality_modifier": -1.0,  # block
        "volatility": "NONE",
        "sizing_cap": "REJECT",
        "notes": "Market closed; no trading",
        "reasoning_notes": "CLOSED: market closed, reject all",
    },
    "WEEKEND": {
        "preferred_patterns": [],
        "avoid_patterns": ["INITIATIVE", "BREAKOUT", "REACTIVE"],
        "quality_modifier": -1.0,
        "volatility": "NONE",
        "sizing_cap": "REJECT",
        "notes": "Weekend; no trading",
        "reasoning_notes": "WEEKEND: market closed, reject all",
    },
}


def get_zone_preferences(zone_name: str) -> Optional[Dict]:
    """Return playbook preferences for a killzone.

    Args:
        zone_name: e.g. "NY_OPEN", "MIDDAY", "ASIA"

    Returns:
        Dict with preferred_patterns, avoid_patterns, quality_modifier,
        volatility, sizing_cap, notes, reasoning_notes.
        None for unknown zones (explicit, no fallback per §6.7).
    """
    return _ZONE_PLAYBOOK.get(zone_name)


def is_pattern_preferred(zone_name: str, pattern_type: str) -> bool:
    """Check if a pattern type is preferred in the current zone."""
    prefs = _ZONE_PLAYBOOK.get(zone_name)
    if prefs is None:
        return False
    return pattern_type.upper() in prefs["preferred_patterns"]


def is_pattern_avoided(zone_name: str, pattern_type: str) -> bool:
    """Check if a pattern type should be avoided in the current zone."""
    prefs = _ZONE_PLAYBOOK.get(zone_name)
    if prefs is None:
        return True  # unknown zone = avoid
    return pattern_type.upper() in prefs["avoid_patterns"]


def get_quality_modifier(zone_name: str) -> float:
    """Return quality modifier for zone (-1.0 to +0.15).

    Firing systems can add this to their per-system quality score.
    NOT a composite formula — just one input to per-system sizing.
    """
    prefs = _ZONE_PLAYBOOK.get(zone_name)
    if prefs is None:
        return -1.0  # unknown = block
    return prefs["quality_modifier"]
