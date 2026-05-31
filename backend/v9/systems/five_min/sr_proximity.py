"""sr_proximity — Reactive pattern S/R level proximity gate.

Per Constitution V3 §Layer 1 §T1: Reactive Bar -3 requires price
at/near support (LONG) or resistance (SHORT).

Levels consumed from S5 TPO endpoint when available · fallback to
direct Sierra volume_profile data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Literal, Tuple

import json


DEFAULT_PROXIMITY_TICKS = 5  # MES tick = 0.25 pt · 5 ticks = 1.25 pt
VP_FILE = Path("/Users/michael/SierraChart_Data/v9_export/volume_profile.json")

# S2 ATR-relative proximity (E2E 2/2 · shadow only)
from backend.v9.shared.atr import S2_ATR_RELATIVE  # noqa: E402
_SR_PROXIMITY_ATR_K = 1.25  # prior: 1.25×ATR5m


def get_proximity_ticks(atr_5m=None, tick_size: float = 0.25) -> int:
    """S/R proximity tolerance in ticks — ATR-relative when flag ON."""
    if S2_ATR_RELATIVE and atr_5m is not None:
        return max(1, round(_SR_PROXIMITY_ATR_K * atr_5m / tick_size))
    return DEFAULT_PROXIMITY_TICKS


def get_sr_levels() -> Optional[dict]:
    """Read S/R levels from Sierra volume_profile export.

    Returns {pdh, pdl, vah, val, ibh, ibl} or None if unavailable.
    """
    if not VP_FILE.exists():
        return None
    try:
        with VP_FILE.open() as f:
            data = json.load(f)
        profiles = data.get("profiles", [])
        if not profiles:
            return None
        # Use first profile for VAH/VAL (current session)
        first = profiles[0]
        return {
            'vah': first.get('vah'),
            'val': first.get('val'),
            'ibh': None,  # IB from TPO system, not in VP file
            'ibl': None,
            'pdh': None,  # Previous day from TPO system
            'pdl': None,
        }
    except (json.JSONDecodeError, OSError):
        return None


def check_proximity(
    price: float,
    direction: Literal['LONG', 'SHORT'],
    levels: Optional[dict] = None,
    tolerance_ticks: int = DEFAULT_PROXIMITY_TICKS,
    tick_size: float = 0.25,
) -> Tuple[bool, Optional[str]]:
    """Check if price is within tolerance of relevant S/R level.

    LONG -> near support (PDL/VAL/IBL).
    SHORT -> near resistance (PDH/VAH/IBH).

    Returns (is_near, level_name_if_near).
    """
    if levels is None:
        levels = get_sr_levels()
    if levels is None:
        return (False, None)

    tolerance = tolerance_ticks * tick_size
    if direction == 'LONG':
        relevant = {k: levels[k] for k in ('pdl', 'val', 'ibl') if levels.get(k) is not None}
    else:
        relevant = {k: levels[k] for k in ('pdh', 'vah', 'ibh') if levels.get(k) is not None}

    for name, level in relevant.items():
        if abs(price - level) <= tolerance:
            return (True, name.upper())
    return (False, None)
