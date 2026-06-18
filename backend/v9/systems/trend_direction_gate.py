"""Trend Direction Gate — blocks counter-trend fires for targeted patterns.

Fail-open, env-gated (TREND_DIRECTION_GATE=1), config-tunable.
Independent of day_type classification — uses live trend_state only.

Counter-trend: LONG∧RED or SHORT∧BLUE.
GRAY/YELLOW/None → fail-open (allow).
"""

import logging
import os
from typing import Tuple

import yaml

logger = logging.getLogger(__name__)

# Resolve config path from project root (same pattern as config_loader.py)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
_CFG_PATH = os.path.join(_PROJECT_ROOT, "config", "trend_direction_gate.yaml")
_cfg_cache = None


def _load_cfg() -> dict:
    global _cfg_cache
    if _cfg_cache is not None:
        return _cfg_cache
    try:
        with open(_CFG_PATH) as f:
            _cfg_cache = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("[TrendGate] config load failed (fail-open): %s", e)
        _cfg_cache = {}
    return _cfg_cache


def _enabled() -> bool:
    return os.environ.get("TREND_DIRECTION_GATE", "0").lower() in ("1", "true", "yes")


def decide(pattern, direction, trend_state) -> Tuple[bool, str]:
    """Decide whether to allow or block a fire based on trend direction.

    Returns (allow: bool, reason: str).
    """
    if not _enabled():
        return (True, "gate OFF")
    if not pattern or not direction:
        return (True, "missing pattern/direction")
    if trend_state not in ("BLUE", "RED"):
        return (True, f"trend_state={trend_state} (fail-open)")

    cfg = _load_cfg()
    patterns = cfg.get("patterns", {})

    # Match: try full pattern_id first (e.g. "REACTIVE_LONG"), then base (e.g. "HFE")
    targeted_sides = None
    if pattern in patterns:
        targeted_sides = patterns[pattern]
    else:
        # Strip _LONG/_SHORT suffix for base match
        base = pattern.rsplit("_", 1)[0] if "_" in pattern else pattern
        if base in patterns:
            targeted_sides = patterns[base]

    if not targeted_sides:
        return (True, f"{pattern} not targeted")

    dir_upper = direction.upper()
    if dir_upper not in targeted_sides:
        return (True, f"{pattern} {dir_upper} not in targeted sides {targeted_sides}")

    # Check counter-trend
    is_counter = (dir_upper == "LONG" and trend_state == "RED") or \
                 (dir_upper == "SHORT" and trend_state == "BLUE")

    if is_counter:
        return (False, f"{pattern} counter-trend ({dir_upper} vs trend={trend_state})")

    return (True, f"{pattern} {dir_upper} with-trend ({trend_state})")
