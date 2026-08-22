"""S2 Auth Table V1 · pattern x day_type x tier -> contracts lookup.

Pure const dict + lookup function. No state, no I/O. Read by quality_tier.py V2.

Authority: docs/spec_authority/S2_AUTH_TABLE_V1.md (LOCKED 2026-05-25 12:22).
Source: D-095 path A · 10 PatternName x 7 DayType x 3 quality tiers = 70 cells.

Pkg 8 · Quality V2 · Phase A mechanical · DEMO+ parametric calibration.
"""
from __future__ import annotations

import logging
from typing import Dict, Literal, Tuple, get_args

from backend.v9.systems.five_min.output_schema import PatternName

logger = logging.getLogger(__name__)

QualityVerdict = Literal['FULL', 'REDUCED', 'SKIP']
QualityTier = Literal['HIGH', 'MEDIUM', 'LOW']

DAY_TYPES: Tuple[str, ...] = (
    "Trend_Normal", "Trend_DD", "Neutral_Extreme", "Variation",
    "Neutral_Center", "Normal", "Nontrend",
)

DAY_TYPE_ALIAS: Dict[str, str] = {
    "TN": "Trend_Normal", "TDD": "Trend_DD", "NeuE": "Neutral_Extreme",
    "NV": "Variation", "NeuC": "Neutral_Center", "Norm": "Normal", "NT": "Nontrend",
}

# Format: (pattern_name, day_type): (verdict, HIGH, MEDIUM, LOW)
_AUTH_TABLE_V1: Dict[Tuple[str, str], Tuple[QualityVerdict, int, int, int]] = {
    ("REACTIVE_LONG",        "Trend_Normal"):    ("REDUCED", 2, 1, 0),
    ("REACTIVE_LONG",        "Trend_DD"):        ("REDUCED", 2, 1, 0),
    ("REACTIVE_LONG",        "Neutral_Extreme"): ("FULL",    3, 2, 2),
    ("REACTIVE_LONG",        "Variation"):       ("FULL",    3, 2, 2),
    ("REACTIVE_LONG",        "Neutral_Center"):  ("FULL",    3, 2, 2),
    ("REACTIVE_LONG",        "Normal"):          ("FULL",    3, 2, 2),
    ("REACTIVE_LONG",        "Nontrend"):        ("SKIP",    0, 0, 0),
    ("REACTIVE_SHORT",       "Trend_Normal"):    ("REDUCED", 2, 2, 0),
    ("REACTIVE_SHORT",       "Trend_DD"):        ("REDUCED", 2, 2, 0),
    ("REACTIVE_SHORT",       "Neutral_Extreme"): ("FULL",    3, 2, 2),
    ("REACTIVE_SHORT",       "Variation"):       ("FULL",    3, 2, 2),
    ("REACTIVE_SHORT",       "Neutral_Center"):  ("FULL",    3, 2, 2),
    ("REACTIVE_SHORT",       "Normal"):          ("FULL",    3, 2, 2),
    ("REACTIVE_SHORT",       "Nontrend"):        ("SKIP",    0, 0, 0),
    ("INITIATIVE_LONG",      "Trend_Normal"):    ("FULL",    3, 2, 1),
    ("INITIATIVE_LONG",      "Trend_DD"):        ("FULL",    3, 2, 1),
    ("INITIATIVE_LONG",      "Neutral_Extreme"): ("SKIP",    0, 0, 0),
    ("INITIATIVE_LONG",      "Variation"):       ("FULL",    3, 2, 1),
    ("INITIATIVE_LONG",      "Neutral_Center"):  ("SKIP",    0, 0, 0),
    ("INITIATIVE_LONG",      "Normal"):          ("SKIP",    0, 0, 0),
    ("INITIATIVE_LONG",      "Nontrend"):        ("SKIP",    0, 0, 0),
    ("INITIATIVE_SHORT",     "Trend_Normal"):    ("FULL",    3, 2, 1),
    ("INITIATIVE_SHORT",     "Trend_DD"):        ("FULL",    3, 2, 1),
    ("INITIATIVE_SHORT",     "Neutral_Extreme"): ("SKIP",    0, 0, 0),
    ("INITIATIVE_SHORT",     "Variation"):       ("FULL",    3, 2, 1),
    ("INITIATIVE_SHORT",     "Neutral_Center"):  ("SKIP",    0, 0, 0),
    ("INITIATIVE_SHORT",     "Normal"):          ("SKIP",    0, 0, 0),
    ("INITIATIVE_SHORT",     "Nontrend"):        ("SKIP",    0, 0, 0),
    ("INVERSE_HNS_LONG",     "Trend_Normal"):    ("SKIP",    0, 0, 0),
    ("INVERSE_HNS_LONG",     "Trend_DD"):        ("SKIP",    0, 0, 0),
    ("INVERSE_HNS_LONG",     "Neutral_Extreme"): ("FULL",    3, 2, 1),
    ("INVERSE_HNS_LONG",     "Variation"):       ("REDUCED", 2, 1, 0),
    ("INVERSE_HNS_LONG",     "Neutral_Center"):  ("FULL",    3, 2, 1),
    ("INVERSE_HNS_LONG",     "Normal"):          ("FULL",    3, 2, 1),
    ("INVERSE_HNS_LONG",     "Nontrend"):        ("SKIP",    0, 0, 0),
    ("HNS_TOP_SHORT",        "Trend_Normal"):    ("SKIP",    0, 0, 0),
    ("HNS_TOP_SHORT",        "Trend_DD"):        ("SKIP",    0, 0, 0),
    ("HNS_TOP_SHORT",        "Neutral_Extreme"): ("FULL",    3, 2, 1),
    ("HNS_TOP_SHORT",        "Variation"):       ("REDUCED", 2, 1, 0),
    ("HNS_TOP_SHORT",        "Neutral_Center"):  ("FULL",    3, 2, 1),
    ("HNS_TOP_SHORT",        "Normal"):          ("FULL",    3, 2, 1),
    ("HNS_TOP_SHORT",        "Nontrend"):        ("SKIP",    0, 0, 0),
    ("DOUBLE_BOTTOM_EE_LONG","Trend_Normal"):    ("SKIP",    0, 0, 0),
    ("DOUBLE_BOTTOM_EE_LONG","Trend_DD"):        ("SKIP",    0, 0, 0),
    ("DOUBLE_BOTTOM_EE_LONG","Neutral_Extreme"): ("FULL",    3, 2, 2),
    ("DOUBLE_BOTTOM_EE_LONG","Variation"):       ("FULL",    3, 2, 2),
    ("DOUBLE_BOTTOM_EE_LONG","Neutral_Center"):  ("FULL",    3, 2, 2),
    ("DOUBLE_BOTTOM_EE_LONG","Normal"):          ("FULL",    3, 2, 2),
    ("DOUBLE_BOTTOM_EE_LONG","Nontrend"):        ("SKIP",    0, 0, 0),
    ("DOUBLE_TOP_AA_SHORT",  "Trend_Normal"):    ("SKIP",    0, 0, 0),
    ("DOUBLE_TOP_AA_SHORT",  "Trend_DD"):        ("SKIP",    0, 0, 0),
    ("DOUBLE_TOP_AA_SHORT",  "Neutral_Extreme"): ("FULL",    3, 2, 2),
    ("DOUBLE_TOP_AA_SHORT",  "Variation"):       ("FULL",    3, 2, 2),
    ("DOUBLE_TOP_AA_SHORT",  "Neutral_Center"):  ("FULL",    3, 2, 2),
    ("DOUBLE_TOP_AA_SHORT",  "Normal"):          ("FULL",    3, 2, 2),
    ("DOUBLE_TOP_AA_SHORT",  "Nontrend"):        ("SKIP",    0, 0, 0),
    ("BULL_FLAG_LONG",       "Trend_Normal"):    ("FULL",    3, 2, 2),
    ("BULL_FLAG_LONG",       "Trend_DD"):        ("FULL",    3, 2, 2),
    ("BULL_FLAG_LONG",       "Neutral_Extreme"): ("REDUCED", 2, 2, 0),
    ("BULL_FLAG_LONG",       "Variation"):       ("FULL",    3, 2, 2),
    ("BULL_FLAG_LONG",       "Neutral_Center"):  ("SKIP",    0, 0, 0),
    ("BULL_FLAG_LONG",       "Normal"):          ("REDUCED", 2, 2, 0),
    ("BULL_FLAG_LONG",       "Nontrend"):        ("SKIP",    0, 0, 0),
    ("BEAR_FLAG_SHORT",      "Trend_Normal"):    ("FULL",    3, 2, 2),
    ("BEAR_FLAG_SHORT",      "Trend_DD"):        ("FULL",    3, 2, 2),
    ("BEAR_FLAG_SHORT",      "Neutral_Extreme"): ("REDUCED", 2, 2, 0),
    ("BEAR_FLAG_SHORT",      "Variation"):       ("FULL",    3, 2, 1),
    ("BEAR_FLAG_SHORT",      "Neutral_Center"):  ("SKIP",    0, 0, 0),
    ("BEAR_FLAG_SHORT",      "Normal"):          ("REDUCED", 2, 1, 0),
    ("BEAR_FLAG_SHORT",      "Nontrend"):        ("SKIP",    0, 0, 0),
    # C2: RE_PULLBACK — pullback to broken IB edge (CONT-family)
    ("RE_PULLBACK_LONG",     "Trend_Normal"):    ("FULL",    3, 2, 2),
    ("RE_PULLBACK_LONG",     "Trend_DD"):        ("FULL",    3, 2, 2),
    ("RE_PULLBACK_LONG",     "Neutral_Extreme"): ("REDUCED", 2, 2, 0),
    ("RE_PULLBACK_LONG",     "Variation"):       ("FULL",    3, 2, 2),
    ("RE_PULLBACK_LONG",     "Neutral_Center"):  ("SKIP",    0, 0, 0),
    ("RE_PULLBACK_LONG",     "Normal"):          ("REDUCED", 2, 1, 0),
    ("RE_PULLBACK_LONG",     "Nontrend"):        ("SKIP",    0, 0, 0),
    ("RE_PULLBACK_SHORT",    "Trend_Normal"):    ("FULL",    3, 2, 2),
    ("RE_PULLBACK_SHORT",    "Trend_DD"):        ("FULL",    3, 2, 2),
    ("RE_PULLBACK_SHORT",    "Neutral_Extreme"): ("REDUCED", 2, 2, 0),
    ("RE_PULLBACK_SHORT",    "Variation"):       ("FULL",    3, 2, 2),
    ("RE_PULLBACK_SHORT",    "Neutral_Center"):  ("SKIP",    0, 0, 0),
    ("RE_PULLBACK_SHORT",    "Normal"):          ("REDUCED", 2, 1, 0),
    ("RE_PULLBACK_SHORT",    "Nontrend"):        ("SKIP",    0, 0, 0),
}

# ── YAML override with fallback ──────────────────────────────────────
def _try_load_yaml_auth() -> Dict[Tuple[str, str], Tuple[QualityVerdict, int, int, int]]:
    """Attempt to load auth matrix from YAML; return hardcoded fallback on failure."""
    try:
        from backend.v9.config_loader import load_auth_matrix
        loaded = load_auth_matrix()
        if loaded is not None and len(loaded) >= 84:
            logger.info("[Pkg8/auth_table_v1] loaded %d cells from auth_matrix.yaml", len(loaded))
            return loaded
    except Exception as e:
        logger.warning("[Pkg8/auth_table_v1] YAML load failed (%s) — using hardcoded fallback", e)
    return _AUTH_TABLE_V1

AUTH_TABLE: Dict[Tuple[str, str], Tuple[QualityVerdict, int, int, int]] = _try_load_yaml_auth()

assert len(AUTH_TABLE) >= 84  # 12 patterns × 7 day_types (YAML + hardcoded both have RE_PULLBACK)
assert len(_AUTH_TABLE_V1) == 84
_pattern_names = set(get_args(PatternName))
assert {k[0] for k in _AUTH_TABLE_V1} == _pattern_names
assert {k[1] for k in _AUTH_TABLE_V1} == set(DAY_TYPES)
# A4: assert the LOADED table (YAML or fallback) covers ALL PatternNames
assert {k[0] for k in AUTH_TABLE} >= _pattern_names, (
    f"AUTH_TABLE missing patterns: {_pattern_names - {k[0] for k in AUTH_TABLE}}"
)
assert max(max(v[1], v[2], v[3]) for v in _AUTH_TABLE_V1.values()) == 3
for (p, d), (verdict, h, m, l) in _AUTH_TABLE_V1.items():
    if verdict == 'SKIP':
        assert h == 0 and m == 0 and l == 0
for p in _pattern_names:
    assert _AUTH_TABLE_V1[(p, "Nontrend")] == ("SKIP", 0, 0, 0)


def get_auth_cell(
    pattern_name: str, day_type: str,
) -> Tuple[QualityVerdict, int, int, int]:
    """Return (verdict, HIGH, MEDIUM, LOW) for (pattern x day_type) cell."""
    if pattern_name not in get_args(PatternName):
        raise ValueError(
            f"auth_table_v1: pattern_name={pattern_name!r} not in PatternName. "
            f"Known: {sorted(get_args(PatternName))}"
        )
    if day_type not in DAY_TYPES:
        logger.warning(
            "[Pkg8/auth_table_v1] unknown day_type=%r · falling back to Neutral_Center", day_type,
        )
        day_type = "Neutral_Center"
    return AUTH_TABLE[(pattern_name, day_type)]
