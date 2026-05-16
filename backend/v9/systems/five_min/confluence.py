"""Confluence count — Tree V3.3 §Q6 (max 4).

Scoring:
  +1 base (pattern detected)
  +1 Opening Type aligned with direction (First Hour Matrix)
  +1 Killzone HIGH edge_class (S6 prime zones)
  -1 Choppy opening (choppiness > 60)

Max = 4 (base + aligned + killzone + reference lines bonus).
Min = 0 (clamped).

Consumes:
  - S6 Killzone endpoint (/api/v9/killzone/current) READ-ONLY
  - S1 Open Type (via first_hour_matrix)
  - choppiness.py (local)
"""
from __future__ import annotations

from typing import Optional, List

import requests

from .choppiness import is_choppy
from .first_hour_matrix import lookup_matrix


KILLZONE_ENDPOINT = "http://localhost:8000/api/v9/killzone/current"
HIGH_EDGE_ZONES = {"NY_OPEN_VOLATILITY", "NY_PRIME", "PM_PRIME"}


def compute_confluence(
    direction: str,
    opening_bars: List[dict],
    *,
    opening_type: Optional[str] = None,
    killzone_data: Optional[dict] = None,
    near_reference_line: bool = False,
) -> int:
    """Compute confluence score (0-4).

    Args:
        direction: 'LONG' or 'SHORT'
        opening_bars: first 3-6 bars of session (for choppiness)
        opening_type: from S1 Open Type endpoint
        killzone_data: from S6 endpoint (or fetched if None)
        near_reference_line: True if price near PDH/PDL/VAH/VAL (from sr_proximity)
    """
    score = 1  # base: pattern detected

    # +1 Opening Type aligned
    if opening_type is not None:
        sizing_mod, _ = lookup_matrix(opening_type, direction)
        if sizing_mod >= 1.0:
            score += 1

    # +1 Killzone HIGH (prime trading zone)
    if killzone_data is None:
        killzone_data = _fetch_killzone()
    if killzone_data is not None:
        zone_name = (killzone_data.get("current_zone") or {}).get("name", "")
        if zone_name in HIGH_EDGE_ZONES:
            score += 1

    # +1 Near reference line (S/R proximity already computed)
    if near_reference_line:
        score += 1

    # -1 Choppy opening
    if is_choppy(opening_bars):
        score -= 1

    return max(0, min(4, score))


def _fetch_killzone() -> Optional[dict]:
    """Fetch killzone state from S6 endpoint."""
    try:
        r = requests.get(KILLZONE_ENDPOINT, timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None
