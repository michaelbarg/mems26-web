"""YAML config loader with fallback — auth_matrix, targets, stop_params.

Loads from config/*.yaml. If file missing/invalid → falls back to the
hardcoded const-dict already in the code + logger.warning (never silent).

Schema validation enforces structure, types, completeness, and guardrails
(max contracts, R-multiple bounds, tick bounds). Invalid config → rejected
entirely, fallback used.

Round-trip equality: load_from_yaml() must return values identical to the
hardcoded constants. Tests verify this.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(os.getenv(
    "MEMS26_CONFIG_DIR",
    str(Path(__file__).resolve().parent.parent.parent / "config"),
))

# Valid verdicts and day types for schema validation
_VALID_VERDICTS = {"FULL", "REDUCED", "SKIP"}
_VALID_DAY_TYPES = {
    "Trend_Normal", "Trend_DD", "Neutral_Extreme", "Variation",
    "Neutral_Center", "Normal", "Nontrend",
}


def _load_yaml(filename: str) -> Optional[dict]:
    """Load a YAML file from config dir. Returns None on any failure."""
    filepath = _CONFIG_DIR / filename
    try:
        import yaml
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            logger.warning("[ConfigLoader] %s: root is not a dict", filepath)
            return None
        return data
    except FileNotFoundError:
        logger.warning("[ConfigLoader] %s not found — using fallback", filepath)
        return None
    except ImportError:
        logger.warning("[ConfigLoader] PyYAML not installed — using fallback")
        return None
    except Exception as e:
        logger.warning("[ConfigLoader] %s load error: %s — using fallback", filepath, e)
        return None


# ── Auth Matrix ──────────────────────────────────────────────────────

def load_auth_matrix() -> Optional[Dict[Tuple[str, str], Tuple[str, int, int, int]]]:
    """Load auth_matrix.yaml → dict matching _AUTH_TABLE_V1 shape.

    Returns None if file missing/invalid (caller uses hardcoded fallback).
    """
    data = _load_yaml("auth_matrix.yaml")
    if data is None:
        return None

    max_contracts = data.get("max_contracts", 3)
    cells = data.get("cells")
    if not isinstance(cells, dict):
        logger.warning("[ConfigLoader] auth_matrix: missing 'cells' key")
        return None

    result: Dict[Tuple[str, str], Tuple[str, int, int, int]] = {}
    errors = []

    for pattern, day_types_dict in cells.items():
        if not isinstance(day_types_dict, dict):
            errors.append(f"{pattern}: not a dict")
            continue
        for dt, cell in day_types_dict.items():
            if dt not in _VALID_DAY_TYPES:
                errors.append(f"{pattern}.{dt}: invalid day_type")
                continue
            if not isinstance(cell, dict):
                errors.append(f"{pattern}.{dt}: cell not a dict")
                continue
            verdict = cell.get("verdict")
            if verdict not in _VALID_VERDICTS:
                errors.append(f"{pattern}.{dt}: invalid verdict '{verdict}'")
                continue
            high = cell.get("high", 0)
            medium = cell.get("medium", 0)
            low = cell.get("low", 0)
            # Guardrail: contracts cap
            for tier_name, tier_val in [("high", high), ("medium", medium), ("low", low)]:
                if not isinstance(tier_val, int) or tier_val < 0:
                    errors.append(f"{pattern}.{dt}.{tier_name}: invalid ({tier_val})")
                    continue
                if tier_val > max_contracts:
                    errors.append(f"{pattern}.{dt}.{tier_name}={tier_val} > max_contracts={max_contracts}")
                    continue
            result[(pattern, dt)] = (verdict, int(high), int(medium), int(low))

    if errors:
        logger.warning("[ConfigLoader] auth_matrix validation errors: %s", errors[:5])
        return None

    # Completeness: must have all 70 cells (10 patterns × 7 day types)
    if len(result) < 70:
        logger.warning("[ConfigLoader] auth_matrix: only %d/70 cells — incomplete", len(result))
        return None

    return result


# ── Targets ──────────────────────────────────────────────────────────

def load_targets() -> Optional[Dict[str, Dict]]:
    """Load targets.yaml → dict matching _TARGETS shape.

    Returns None if file missing/invalid (caller uses hardcoded fallback).
    """
    data = _load_yaml("targets.yaml")
    if data is None:
        return None

    day_types = data.get("day_types")
    if not isinstance(day_types, dict):
        logger.warning("[ConfigLoader] targets: missing 'day_types' key")
        return None

    result: Dict[str, Dict] = {}
    errors = []

    for dt, spec in day_types.items():
        if dt not in _VALID_DAY_TYPES:
            errors.append(f"unknown day_type: {dt}")
            continue
        if not isinstance(spec, dict):
            errors.append(f"{dt}: not a dict")
            continue
        # Validate R-multiples are in range (guardrail)
        for rkey in ("t1_r", "t2_r", "t3_r"):
            rv = spec.get(rkey)
            if rv is not None and (not isinstance(rv, (int, float)) or rv <= 0 or rv > 10.0):
                errors.append(f"{dt}.{rkey}={rv} out of range (0, 10]")
                continue
        # Validate contracts
        contracts = spec.get("contracts", 0)
        if not isinstance(contracts, int) or contracts < 0:
            errors.append(f"{dt}.contracts={contracts} invalid")
            continue
        result[dt] = dict(spec)

    if errors:
        logger.warning("[ConfigLoader] targets validation errors: %s", errors[:5])
        return None

    # Completeness
    if not _VALID_DAY_TYPES.issubset(result.keys()):
        missing = _VALID_DAY_TYPES - result.keys()
        logger.warning("[ConfigLoader] targets: missing day_types %s", missing)
        return None

    return result


# ── Stop Params ──────────────────────────────────────────────────────

def load_stop_params() -> Optional[Dict[str, Any]]:
    """Load stop_params.yaml → flat dict with all stop parameters.

    Returns None if file missing/invalid (caller uses hardcoded fallback).
    """
    data = _load_yaml("stop_params.yaml")
    if data is None:
        return None

    errors = []
    guardrails = data.get("guardrails", {})
    max_stop = guardrails.get("max_stop_ticks", 20)
    max_t2 = guardrails.get("max_t2_ticks", 50)
    max_atr_mult = guardrails.get("max_atr_multiplier", 5.0)

    # S2 adaptive
    s2 = data.get("s2_adaptive", {})
    if not isinstance(s2, dict):
        errors.append("s2_adaptive: not a dict")
    else:
        for key in ("mes_tick", "floor_ticks", "floor_ticks_min_backstop", "floor_atr_k"):
            if key not in s2:
                errors.append(f"s2_adaptive.{key} missing")
        atr_mult = s2.get("atr_multipliers", {})
        if not isinstance(atr_mult, dict):
            errors.append("s2_adaptive.atr_multipliers: not a dict")
        else:
            for fam, val in atr_mult.items():
                if not isinstance(val, (int, float)) or val <= 0 or val > max_atr_mult:
                    errors.append(f"s2_adaptive.atr_multipliers.{fam}={val} out of range")

    # S4 patterns
    s4 = data.get("s4_patterns", {})
    if not isinstance(s4, dict):
        errors.append("s4_patterns: not a dict")
    else:
        for pid, ticks in s4.items():
            if not isinstance(ticks, dict):
                errors.append(f"s4_patterns.{pid}: not a dict")
                continue
            st = ticks.get("stop_ticks", 0)
            if st > max_stop:
                errors.append(f"s4_patterns.{pid}.stop_ticks={st} > max={max_stop}")
            t2t = ticks.get("t2_ticks", 0)
            if t2t > max_t2:
                errors.append(f"s4_patterns.{pid}.t2_ticks={t2t} > max={max_t2}")

    # min_r_t1_threshold
    rthresh = data.get("min_r_t1_threshold")
    if rthresh is not None and (not isinstance(rthresh, (int, float)) or rthresh < 0):
        errors.append(f"min_r_t1_threshold={rthresh} invalid")

    if errors:
        logger.warning("[ConfigLoader] stop_params validation errors: %s", errors[:5])
        return None

    return data


# ── S2 Firing Variant ────────────────────────────────────────────────

_VALID_S2_VARIANTS = {"A_VSA", "B_RVOL", "C_STRICT", "UNION", "INTERSECTION"}
_S2_DEFAULT = "A_VSA"
_s2_firing_cache: Optional[str] = None
_s2_firing_loaded = False


def load_s2_firing() -> str:
    """Load S2 firing variant from s2_firing.yaml.

    Returns one of: A_VSA, B_RVOL, C_STRICT, UNION, INTERSECTION.
    Default A_VSA = identical to current hardcoded behavior.
    Invalid/missing → fallback A_VSA + warning.
    """
    global _s2_firing_cache, _s2_firing_loaded
    if _s2_firing_loaded:
        return _s2_firing_cache  # type: ignore[return-value]

    _s2_firing_loaded = True
    _s2_firing_cache = _S2_DEFAULT

    data = _load_yaml("s2_firing.yaml")
    if data is None:
        return _s2_firing_cache

    variant = data.get("variant")
    if variant is None:
        logger.warning("[ConfigLoader] s2_firing: missing 'variant' key — using %s", _S2_DEFAULT)
        return _s2_firing_cache

    variant_str = str(variant).upper().strip()
    if variant_str not in _VALID_S2_VARIANTS:
        logger.warning(
            "[ConfigLoader] s2_firing: invalid variant '%s' (valid: %s) — using %s",
            variant, _VALID_S2_VARIANTS, _S2_DEFAULT,
        )
        return _s2_firing_cache

    _s2_firing_cache = variant_str
    logger.info("[ConfigLoader] s2_firing variant: %s", variant_str)
    return _s2_firing_cache


def reset_s2_firing_cache() -> None:
    """Reset s2_firing cache — for testing only."""
    global _s2_firing_cache, _s2_firing_loaded
    _s2_firing_cache = None
    _s2_firing_loaded = False
