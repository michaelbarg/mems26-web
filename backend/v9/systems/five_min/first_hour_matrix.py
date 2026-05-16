"""First Hour Matrix — Tree V3.3 §Stage C.

5 Opening Types × Pattern lookup.
Consumed from S1 Open Type endpoint (/api/v9/open_type/current).

Matrix maps (Opening Type, Pattern) → sizing modifier + time_stop override.
"""
from __future__ import annotations

from typing import Optional, Tuple

import requests


OPEN_TYPE_ENDPOINT = "http://localhost:8000/api/v9/open_type/current"

# Matrix: (opening_type, pattern_direction) → (sizing_modifier, time_stop_override)
# sizing_modifier: 1.0 = full, 0.5 = half, 0.0 = skip
# time_stop_override: None = use Day Type default
FIRST_HOUR_MATRIX: dict = {
    # Open Drive: strong directional → favor same-direction patterns
    ("OPEN_DRIVE", "LONG"): (1.0, None),        # full size, drive direction
    ("OPEN_DRIVE", "SHORT"): (0.0, None),       # skip counter-drive
    # Open Test Drive: reversal likely → favor counter-patterns
    ("OPEN_TEST_DRIVE", "LONG"): (0.5, 45),     # half size, cautious
    ("OPEN_TEST_DRIVE", "SHORT"): (1.0, None),  # full, aligned with reversal
    # Open Rejection Reverse: strong reversal → favor reversal direction
    ("OPEN_REJECTION_REVERSE", "LONG"): (0.5, 30),
    ("OPEN_REJECTION_REVERSE", "SHORT"): (1.0, None),
    # Open Auction In: rotational → conservative
    ("OPEN_AUCTION_IN", "LONG"): (0.5, 30),
    ("OPEN_AUCTION_IN", "SHORT"): (0.5, 30),
    # Open Auction Out: gap day → favor gap direction
    ("OPEN_AUCTION_OUT", "LONG"): (1.0, None),
    ("OPEN_AUCTION_OUT", "SHORT"): (0.5, 45),
}


def get_current_open_type() -> Optional[str]:
    """Fetch current opening type from S1 endpoint."""
    try:
        r = requests.get(OPEN_TYPE_ENDPOINT, timeout=2)
        if r.status_code == 200:
            data = r.json()
            return data.get("type") or data.get("opening_type")
    except Exception:
        pass
    return None


def lookup_matrix(
    opening_type: Optional[str],
    direction: str,
) -> Tuple[float, Optional[int]]:
    """Look up First Hour Matrix for sizing modifier + time_stop override.

    Returns (sizing_modifier, time_stop_override).
    If opening_type unknown → (0.5, 45) conservative default.
    """
    if opening_type is None:
        return (0.5, 45)  # conservative when unknown

    key = (opening_type.upper(), direction.upper())
    return FIRST_HOUR_MATRIX.get(key, (0.5, 45))
