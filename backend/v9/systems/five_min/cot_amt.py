"""COT/AMT standalone · direct Sierra read · coexists with HTTP fallback.

Per Constitution V3 §Layer 1 §T1 (Zohar OFA).
- COT = cumulative buyer vol - seller vol (current session)
- AMT = 90-min rolling average baseline of COT
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import json


SIERRA_DATA_DIR = Path("/Users/michael/SierraChart_Data/v9_export")
CUM_DELTA_FILE = SIERRA_DATA_DIR / "cumulative_delta.json"
AMT_WINDOW_BARS = 18  # 90 min / 5 min


def read_cumulative_delta() -> Optional[dict]:
    """Read cumulative_delta.json from Sierra export."""
    if not CUM_DELTA_FILE.exists():
        return None
    try:
        with CUM_DELTA_FILE.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def compute_cot(points: list) -> float:
    """Compute COT from cumulative delta points.

    Each point has 'd' (delta per bar) and 'cum' (cumulative).
    COT = latest cumulative value.
    """
    if not points:
        return 0.0
    return points[-1].get("cum", 0.0)


def compute_amt(points: list, window: int = AMT_WINDOW_BARS) -> float:
    """Compute AMT (90-min rolling average of cumulative delta).

    AMT = mean of last `window` cumulative values.
    """
    if not points:
        return 0.0
    window_points = points[-window:]
    cum_values = [p.get("cum", 0.0) for p in window_points]
    return sum(cum_values) / len(cum_values) if cum_values else 0.0


def cot_vs_amt(points: list) -> Literal['ABOVE', 'BELOW', 'AT']:
    """Compare COT to AMT. Returns regime label."""
    cot = compute_cot(points)
    amt = compute_amt(points)
    if abs(cot - amt) < 1e-6:
        return 'AT'
    return 'ABOVE' if cot > amt else 'BELOW'
