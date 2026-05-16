"""Quality Tier — consume S5 /tpo/current for location-based sizing.

Per Constitution V3 §Layer 2 Quality Tier:
  HIGH (3 contracts): price at POC/VAH/VAL (strong reference)
  MEDIUM (2 contracts): price within value area but not at key level
  LOW (0 contracts = skip): price outside value area, no reference

Location source: S5 TPO endpoint /api/v9/tpo/current.
"""
from __future__ import annotations

from typing import Literal, Optional, Tuple

import requests


TPO_ENDPOINT = "http://localhost:8000/api/v9/tpo/current"
PROXIMITY_PT = 2.0  # within 2 points of key level = "at" level


def get_quality_tier(
    price: float,
    *,
    tpo_data: Optional[dict] = None,
) -> Tuple[Literal['HIGH', 'MEDIUM', 'LOW'], int]:
    """Determine quality tier based on price location vs TPO levels.

    Returns (tier, sizing_contracts).
    """
    if tpo_data is None:
        tpo_data = _fetch_tpo()
    if tpo_data is None:
        return ('MEDIUM', 2)  # fallback when TPO unavailable

    poc = tpo_data.get("poc") or tpo_data.get("poc_tpo")
    vah = tpo_data.get("vah")
    val = tpo_data.get("val")

    if poc is None or vah is None or val is None:
        return ('MEDIUM', 2)

    # HIGH: price at POC, VAH, or VAL (within PROXIMITY_PT)
    key_levels = [poc, vah, val]
    for level in key_levels:
        if level is not None and abs(price - level) <= PROXIMITY_PT:
            return ('HIGH', 3)

    # MEDIUM: price within value area (between VAL and VAH)
    if val <= price <= vah:
        return ('MEDIUM', 2)

    # LOW: price outside value area
    return ('LOW', 0)


def _fetch_tpo() -> Optional[dict]:
    """Fetch TPO state from S5 endpoint."""
    try:
        r = requests.get(TPO_ENDPOINT, timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None
