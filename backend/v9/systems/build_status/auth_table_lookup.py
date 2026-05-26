"""S2 Auth Table V1 — Python const dict lookup.

Source: docs/spec_authority/S2_AUTH_TABLE_V1.md §4 (🔒 LOCKED 2026-05-25 12:22)
Format: AUTH_TABLE[pattern_name][day_type] = (verdict, high, medium, low)
verdict ∈ {"FULL", "REDUCED", "SKIP"}
"""

from typing import Dict, Tuple, Literal

Verdict = Literal["FULL", "REDUCED", "SKIP"]
AuthCell = Tuple[Verdict, int, int, int]  # (verdict, HIGH, MEDIUM, LOW)

# Day type short keys → enum values mapping for lookup
DAY_TYPE_SHORT_TO_ENUM = {
    "TN": "Trend_Normal",
    "TDD": "Trend_DD",
    "NeuE": "Neutral_Extreme",
    "NV": "Variation",
    "NeuC": "Neutral_Center",
    "Norm": "Normal",
    "NT": "Nontrend",
}

DAY_TYPE_ENUM_TO_SHORT = {v: k for k, v in DAY_TYPE_SHORT_TO_ENUM.items()}

# Verbatim from S2_AUTH_TABLE_V1.md §4 (post-audit, post-transformation)
# Pattern order per §2: REACTIVE_LONG, REACTIVE_SHORT, INITIATIVE_LONG,
# INITIATIVE_SHORT, INVERSE_HNS_LONG, HNS_TOP_SHORT, DOUBLE_BOTTOM_EE_LONG,
# DOUBLE_TOP_AA_SHORT, BULL_FLAG_LONG, BEAR_FLAG_SHORT
AUTH_TABLE: Dict[str, Dict[str, AuthCell]] = {
    "REACTIVE_LONG": {
        "Trend_Normal": ("REDUCED", 2, 1, 0),
        "Trend_DD": ("REDUCED", 2, 1, 0),
        "Neutral_Extreme": ("FULL", 3, 2, 2),
        "Variation": ("FULL", 3, 2, 2),
        "Neutral_Center": ("FULL", 3, 2, 2),
        "Normal": ("FULL", 3, 2, 2),
        "Nontrend": ("SKIP", 0, 0, 0),
    },
    "REACTIVE_SHORT": {
        "Trend_Normal": ("REDUCED", 2, 2, 0),
        "Trend_DD": ("REDUCED", 2, 2, 0),
        "Neutral_Extreme": ("FULL", 3, 2, 2),
        "Variation": ("FULL", 3, 2, 2),
        "Neutral_Center": ("FULL", 3, 2, 2),
        "Normal": ("FULL", 3, 2, 2),
        "Nontrend": ("SKIP", 0, 0, 0),
    },
    "INITIATIVE_LONG": {
        "Trend_Normal": ("FULL", 3, 2, 1),
        "Trend_DD": ("FULL", 3, 2, 1),
        "Neutral_Extreme": ("SKIP", 0, 0, 0),
        "Variation": ("FULL", 3, 2, 1),
        "Neutral_Center": ("SKIP", 0, 0, 0),
        "Normal": ("SKIP", 0, 0, 0),
        "Nontrend": ("SKIP", 0, 0, 0),
    },
    "INITIATIVE_SHORT": {
        "Trend_Normal": ("FULL", 3, 2, 1),
        "Trend_DD": ("FULL", 3, 2, 1),
        "Neutral_Extreme": ("SKIP", 0, 0, 0),
        "Variation": ("FULL", 3, 2, 1),
        "Neutral_Center": ("SKIP", 0, 0, 0),
        "Normal": ("SKIP", 0, 0, 0),
        "Nontrend": ("SKIP", 0, 0, 0),
    },
    "INVERSE_HNS_LONG": {
        "Trend_Normal": ("SKIP", 0, 0, 0),
        "Trend_DD": ("SKIP", 0, 0, 0),
        "Neutral_Extreme": ("FULL", 3, 2, 1),
        "Variation": ("REDUCED", 2, 1, 0),
        "Neutral_Center": ("FULL", 3, 2, 1),
        "Normal": ("FULL", 3, 2, 1),
        "Nontrend": ("SKIP", 0, 0, 0),
    },
    "HNS_TOP_SHORT": {
        "Trend_Normal": ("SKIP", 0, 0, 0),
        "Trend_DD": ("SKIP", 0, 0, 0),
        "Neutral_Extreme": ("FULL", 3, 2, 1),
        "Variation": ("REDUCED", 2, 1, 0),
        "Neutral_Center": ("FULL", 3, 2, 1),
        "Normal": ("FULL", 3, 2, 1),
        "Nontrend": ("SKIP", 0, 0, 0),
    },
    "DOUBLE_BOTTOM_EE_LONG": {
        "Trend_Normal": ("SKIP", 0, 0, 0),
        "Trend_DD": ("SKIP", 0, 0, 0),
        "Neutral_Extreme": ("FULL", 3, 2, 2),
        "Variation": ("FULL", 3, 2, 2),
        "Neutral_Center": ("FULL", 3, 2, 2),
        "Normal": ("FULL", 3, 2, 2),
        "Nontrend": ("SKIP", 0, 0, 0),
    },
    "DOUBLE_TOP_AA_SHORT": {
        "Trend_Normal": ("SKIP", 0, 0, 0),
        "Trend_DD": ("SKIP", 0, 0, 0),
        "Neutral_Extreme": ("FULL", 3, 2, 2),
        "Variation": ("FULL", 3, 2, 2),
        "Neutral_Center": ("FULL", 3, 2, 2),
        "Normal": ("FULL", 3, 2, 2),
        "Nontrend": ("SKIP", 0, 0, 0),
    },
    "BULL_FLAG_LONG": {
        "Trend_Normal": ("FULL", 3, 2, 2),
        "Trend_DD": ("FULL", 3, 2, 2),
        "Neutral_Extreme": ("REDUCED", 2, 2, 0),
        "Variation": ("FULL", 3, 2, 2),
        "Neutral_Center": ("SKIP", 0, 0, 0),
        "Normal": ("REDUCED", 2, 2, 0),
        "Nontrend": ("SKIP", 0, 0, 0),
    },
    "BEAR_FLAG_SHORT": {
        "Trend_Normal": ("FULL", 3, 2, 2),
        "Trend_DD": ("FULL", 3, 2, 2),
        "Neutral_Extreme": ("REDUCED", 2, 2, 0),
        "Variation": ("FULL", 3, 2, 1),
        "Neutral_Center": ("SKIP", 0, 0, 0),
        "Normal": ("REDUCED", 2, 1, 0),
        "Nontrend": ("SKIP", 0, 0, 0),
    },
}

# Ordered pattern list per S2_AUTH_TABLE_V1.md §2
S2_PATTERN_IDS = [
    "REACTIVE_LONG",
    "REACTIVE_SHORT",
    "INITIATIVE_LONG",
    "INITIATIVE_SHORT",
    "INVERSE_HNS_LONG",
    "HNS_TOP_SHORT",
    "DOUBLE_BOTTOM_EE_LONG",
    "DOUBLE_TOP_AA_SHORT",
    "BULL_FLAG_LONG",
    "BEAR_FLAG_SHORT",
]

# Ordered Woodies pattern list per D-092_S4_WOODIES_UPDATE.md §2
WOODIES_PATTERN_IDS = [
    "ZLR",
    "TLB",
    "TT",
    "GB100",
    "Vegas",
    "Ghost",
    "FaMir",
    "HTLB",
    "HFE",
]


def lookup_auth_cell(pattern_name: str, day_type: str) -> AuthCell:
    """Look up the (verdict, HIGH, MEDIUM, LOW) cell for a pattern × day_type.

    Args:
        pattern_name: One of S2_PATTERN_IDS
        day_type: DayType enum value (e.g. "Neutral_Center") or short key (e.g. "NeuC")

    Returns:
        (verdict, high_contracts, medium_contracts, low_contracts)

    Raises:
        ValueError: if pattern_name not in AUTH_TABLE
    """
    if pattern_name not in AUTH_TABLE:
        raise ValueError(f"Unknown pattern_name: {pattern_name!r}. Valid: {S2_PATTERN_IDS}")

    # Allow short-key lookup
    if day_type in DAY_TYPE_SHORT_TO_ENUM:
        day_type = DAY_TYPE_SHORT_TO_ENUM[day_type]

    # Fallback for unknown/legacy day types → Neutral_Center per §6.4
    if day_type not in AUTH_TABLE[pattern_name]:
        day_type = "Neutral_Center"

    return AUTH_TABLE[pattern_name][day_type]


def is_skip(pattern_name: str, day_type: str) -> bool:
    """Return True if the auth table cell is SKIP (pattern blocked for this day type)."""
    verdict, _, _, _ = lookup_auth_cell(pattern_name, day_type)
    return verdict == "SKIP"
