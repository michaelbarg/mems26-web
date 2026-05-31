"""R:R score computation for D-094 fire selection.

Pure function — no state, no I/O. Computes the weighted R:R ratio
for a setup dict using contract_split percentages.

Formula (D-094 LOCKED):
    R:R = Σ_i ( |target_i − entry| × split_pct_i ) / |entry − stop|

Contracts cancel out — R:R is price-distance only.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def compute_rr_score(setup: dict) -> Optional[float]:
    """Compute R:R score for a setup dict.

    Args:
        setup: dict with keys entry_price, stop, t1, t2, t3, classification

    Returns:
        R:R as float, or None if inputs are invalid (entry==stop, missing prices).
    """
    entry = setup.get("entry_price") or 0.0
    stop = setup.get("stop") or 0.0
    t1 = setup.get("t1") or 0.0
    t2 = setup.get("t2") or 0.0
    t3 = setup.get("t3") or 0.0

    risk = abs(entry - stop)
    if risk == 0:
        return None  # division by zero guard

    # Get contract split from pattern classification
    classification = setup.get("classification") or ""
    try:
        from backend.v9.systems.five_min.contract_split import get_contract_split
        t1_pct, t2_pct, t3_pct = get_contract_split(classification)
    except (ValueError, ImportError):
        # Unknown pattern — default equal split across non-zero targets
        targets_present = sum(1 for t in (t1, t2, t3) if t != 0)
        if targets_present == 0:
            return None
        equal_pct = 1.0 / targets_present
        t1_pct = equal_pct if t1 != 0 else 0.0
        t2_pct = equal_pct if t2 != 0 else 0.0
        t3_pct = equal_pct if t3 != 0 else 0.0

    # Weighted reward
    reward = (
        abs(t1 - entry) * t1_pct +
        abs(t2 - entry) * t2_pct +
        abs(t3 - entry) * t3_pct
    )

    if reward <= 0:
        return None

    return round(reward / risk, 4)
