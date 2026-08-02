"""S6 MAE Scratch — adverse-excursion-based early exit (DEV_PLAN 02.08 §P3.1).

Sweeney (1996): the winning trades move favorably quickly; the losers dwell
deep in red. Our data (112 trades): winners median MAE 3.2pt, losers 11.2pt.
When a trade hits the per-pattern MAE threshold before T1, scratch it (FLATTEN).
After T1 → BE already protects; this only fires pre-T1.

Flag: S6_MAE_SCRATCH_V1 (default OFF). When OFF, should_scratch() returns
(False, "") and zero behavior changes. When ON, the bar_level_detector calls
it each bar on open demo/live trades and issues FLATTEN on True.

The thresholds come from config/mae_scratch.yaml (calibrated from actual trades).
Responsive patterns get threshold × 1.5 per Kaminski&Lo (early exit hurts
mean-reversion).

NEVER calls op=EXIT (forbidden). Uses FLATTEN only (the allowed mechanism).
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

from backend.v9.config_loader import _load_yaml

logger = logging.getLogger(__name__)

_cache = None
_loaded = False


def _flag_on() -> bool:
    return os.getenv("S6_MAE_SCRATCH_V1", "0").lower() in ("1", "true", "yes")


def _cfg():
    global _cache, _loaded
    if not _loaded:
        _loaded = True
        _cache = _load_yaml("mae_scratch.yaml")
    return _cache or {}


def reset_cache():
    global _cache, _loaded
    _cache = None
    _loaded = False


def _normalize_pattern(pattern_name: str) -> str:
    """Normalize pattern name for lookup (strip _LONG/_SHORT suffix)."""
    p = (pattern_name or "").upper().strip()
    for suf in ("_LONG", "_SHORT"):
        if p.endswith(suf):
            p = p[:-len(suf)]
    return p


def get_threshold(pattern_name: str) -> float:
    """Get the MAE scratch threshold for a pattern.

    Uses per-pattern override from config if available, else default.
    Responsive patterns get threshold × multiplier.
    """
    cfg = _cfg()
    default = float(cfg.get("default_threshold_pts", 8.0))
    multiplier = float(cfg.get("responsive_multiplier", 1.5))
    responsive = set(cfg.get("responsive_patterns", []))
    overrides = cfg.get("pattern_thresholds", {})

    norm = _normalize_pattern(pattern_name)

    # Check per-pattern override first
    threshold = overrides.get(norm) or overrides.get(pattern_name)
    if threshold is not None:
        return float(threshold)

    # Check if responsive → apply multiplier
    if norm in responsive or pattern_name in responsive:
        return default * multiplier

    return default


def compute_mae(
    entry_price: float,
    direction: str,
    bar_low: float,
    bar_high: float,
) -> float:
    """Compute the Maximum Adverse Excursion from a single bar's extremes.

    MAE = how far price went AGAINST the trade on this bar.
    LONG: MAE = entry - bar_low (positive when price dipped below entry)
    SHORT: MAE = bar_high - entry (positive when price spiked above entry)
    """
    d = direction.upper()
    if d == "LONG":
        return max(0.0, entry_price - bar_low)
    elif d == "SHORT":
        return max(0.0, bar_high - entry_price)
    return 0.0


def should_scratch(
    *,
    pattern_name: str,
    entry_price: float,
    direction: str,
    bar_low: float,
    bar_high: float,
    t1_hit: bool = False,
) -> Tuple[bool, str]:
    """Determine if a trade should be scratched based on MAE.

    Returns (True, reason) if MAE >= threshold and pre-T1.
    Returns (False, "") otherwise or when flag is OFF.

    NEVER returns True after T1 (BE already covers post-T1).
    """
    if not _flag_on():
        return (False, "")

    if t1_hit:
        return (False, "")  # post-T1 → BE handles it

    mae = compute_mae(entry_price, direction, bar_low, bar_high)
    threshold = get_threshold(pattern_name)

    if mae >= threshold:
        reason = (f"MAE scratch: {mae:.1f}pt >= {threshold:.1f}pt threshold "
                  f"for {pattern_name} (pre-T1)")
        return (True, reason)

    return (False, "")
