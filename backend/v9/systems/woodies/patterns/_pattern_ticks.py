"""Centralized S4 pattern tick loader — reads from config/stop_params.yaml.

Single source for STOP_TICKS, TARGET1_TICKS, TARGET2_TICKS per pattern.
Falls back to hardcoded defaults if YAML is missing/invalid (Rule 1).

Usage in each detector:
    from ._pattern_ticks import get_ticks
    _ticks = get_ticks("ZLR")
    STOP_TICKS = _ticks["stop_ticks"]
    TARGET1_TICKS = _ticks["t1_ticks"]
    TARGET2_TICKS = _ticks["t2_ticks"]

NOTE: _T1_TICKS (=4, used for R_t1 computation) is NOT loaded here —
it is intentionally separate from TARGET1_TICKS (the actual target).
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Hardcoded defaults — the authoritative fallback if YAML is unavailable.
# These MUST match the original module-level constants in each detector.
_DEFAULTS: Dict[str, Dict[str, int]] = {
    "ZLR":   {"stop_ticks": 8,  "t1_ticks": 12, "t2_ticks": 24},
    "TLB":   {"stop_ticks": 10, "t1_ticks": 15, "t2_ticks": 30},
    "TT":    {"stop_ticks": 8,  "t1_ticks": 12, "t2_ticks": 20},
    "GB100": {"stop_ticks": 8,  "t1_ticks": 12, "t2_ticks": 24},
    "VEGAS": {"stop_ticks": 12, "t1_ticks": 16, "t2_ticks": 32},
    "GHOST": {"stop_ticks": 12, "t1_ticks": 16, "t2_ticks": 32},
    "FAMIR": {"stop_ticks": 10, "t1_ticks": 14, "t2_ticks": 28},
    "HTLB":  {"stop_ticks": 10, "t1_ticks": 14, "t2_ticks": 28},
    "HFE":   {"stop_ticks": 8,  "t1_ticks": 12, "t2_ticks": 24},
}

# Module-level cache: loaded once, reused.
_loaded: Dict[str, Dict[str, int]] = {}
_loaded_flag = False


def _ensure_loaded() -> None:
    """Load from YAML once. On failure, _loaded stays empty → fallback per PID."""
    global _loaded, _loaded_flag
    if _loaded_flag:
        return
    _loaded_flag = True
    try:
        from backend.v9.config_loader import load_stop_params
        data = load_stop_params()
        if data is not None:
            s4 = data.get("s4_patterns", {})
            if isinstance(s4, dict) and s4:
                _loaded = {k.upper(): v for k, v in s4.items()}
                logger.info("[S4_ticks] loaded %d patterns from stop_params.yaml", len(_loaded))
                return
        logger.warning("[S4_ticks] YAML load returned None — using hardcoded defaults")
    except Exception as e:
        logger.warning("[S4_ticks] YAML load failed (%s) — using hardcoded defaults", e)


def get_ticks(pattern_id: str) -> Dict[str, int]:
    """Return {stop_ticks, t1_ticks, t2_ticks} for a pattern.

    Reads from YAML (cached); falls back to hardcoded default for the pattern.
    """
    _ensure_loaded()
    pid = pattern_id.upper()

    # Try YAML-loaded value
    if pid in _loaded:
        return dict(_loaded[pid])

    # Fallback to hardcoded
    if pid in _DEFAULTS:
        return dict(_DEFAULTS[pid])

    logger.warning("[S4_ticks] unknown pattern_id=%s — returning ZLR defaults", pid)
    return dict(_DEFAULTS["ZLR"])


def reset_cache() -> None:
    """Reset the cache — for testing only."""
    global _loaded, _loaded_flag
    _loaded = {}
    _loaded_flag = False
