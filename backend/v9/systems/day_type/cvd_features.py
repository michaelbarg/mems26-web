"""cvd_features.py — RELATIVE CVD signal for S1 day-type classification.

Per the spec (A3): absolute CVD thresholds do NOT transfer between days /
instruments. Use the NORMALIZED position of CVD within the session range, plus
whether a new CVD extreme is RECENT (momentum), not just present.

  cvd_pos = (cvd_now - cvd_session_min) / (cvd_session_max - cvd_session_min)  ∈ 0..1

  direction:
    support_long  = cvd_pos >= 0.75 AND a new session-HIGH was made in the last K bars
    support_short = cvd_pos <= 0.25 AND a new session-LOW  was made in the last K bars
    flat          = otherwise (mid-band, OR the extreme is old = a swing that returned)

This is why 2026-06-19 is FLAT (not trend) despite cvd_pos≈0.21: CVD swung from
+1658 to -564 — the session-low (-1170) is 15 bars old, so no RECENT new low.
Pure function; not wired live.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def compute_cvd_features(
    cum_series: List[float],
    *,
    k: int = 5,
    hi: float = 0.75,
    lo: float = 0.25,
) -> Dict[str, Any]:
    """cum_series: cumulative-delta values in session time order (e.g. points[].cum)."""
    n = len(cum_series)
    if n == 0:
        return {"cvd_pos": None, "direction": "flat",
                "recent_new_high": False, "recent_new_low": False, "n": 0}

    now = cum_series[-1]
    mx = max(cum_series)
    mn = min(cum_series)
    cvd_pos: Optional[float] = round((now - mn) / (mx - mn), 4) if mx > mn else 0.5

    idx_max = max(range(n), key=lambda i: cum_series[i])
    idx_min = min(range(n), key=lambda i: cum_series[i])
    recent_new_high = (n - 1 - idx_max) < k
    recent_new_low = (n - 1 - idx_min) < k

    if cvd_pos is not None and cvd_pos >= hi and recent_new_high:
        direction = "support_long"
    elif cvd_pos is not None and cvd_pos <= lo and recent_new_low:
        direction = "support_short"
    else:
        direction = "flat"

    return {"cvd_pos": cvd_pos, "direction": direction,
            "recent_new_high": recent_new_high, "recent_new_low": recent_new_low, "n": n}
