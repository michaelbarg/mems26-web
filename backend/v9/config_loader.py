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


# ── Pattern T1 Overrides ───────────────────────────────────────────────

_pattern_t1_cache: Optional[Dict] = None
_pattern_t1_loaded = False


def load_pattern_t1_points() -> Dict[str, Dict[str, float]]:
    """Load pattern_t1_points from targets.yaml.

    Returns nested dict: {pattern_name: {day_type: points}}.
    Empty dict on missing/invalid (fail-open, no overrides applied).
    """
    global _pattern_t1_cache, _pattern_t1_loaded
    if _pattern_t1_loaded:
        return _pattern_t1_cache or {}

    _pattern_t1_loaded = True
    _pattern_t1_cache = {}

    data = _load_yaml("targets.yaml")
    if data is None:
        return _pattern_t1_cache

    overrides = data.get("pattern_t1_points")
    if not isinstance(overrides, dict):
        return _pattern_t1_cache

    for pattern, dt_map in overrides.items():
        if not isinstance(dt_map, dict):
            continue
        clean = {}
        for dt, pts in dt_map.items():
            if isinstance(pts, (int, float)) and pts > 0:
                clean[dt] = float(pts)
        if clean:
            _pattern_t1_cache[pattern] = clean

    if _pattern_t1_cache:
        logger.info("[ConfigLoader] pattern_t1_points: %d patterns loaded", len(_pattern_t1_cache))
    return _pattern_t1_cache


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

# ── Stop Anchors V2 (config/stop_anchors.yaml) ───────────────────────

def load_stop_anchors() -> Optional[Dict[str, Any]]:
    """Load stop_anchors.yaml → validated dict, or None (caller falls back to
    legacy behavior). Spec + provenance locked by Michael+research 2026-06-07.
    Gated at the call site by env STOP_ANCHORS_V2 — this loader is inert until
    the flag is on. Schema-validation rejects an out-of-range config entirely.
    """
    data = _load_yaml("stop_anchors.yaml")
    if data is None:
        return None

    errors = []
    g = data.get("guardrails", {})
    max_contracts = g.get("max_contracts", 3)
    max_risk = g.get("max_risk_points", 30)
    t1_min, t1_max = g.get("t1_r_min", 0.2), g.get("t1_r_max", 1.5)
    off_max = g.get("anchor_offset_ticks_max", 6)

    p = data.get("principles", {})
    off = p.get("anchor_offset_ticks", 3)
    if not (0 <= off <= off_max):
        errors.append(f"anchor_offset_ticks={off} out of range")
    # 07-23 calibration override (32-session study: 6T/10T confirmed too tight,
    # 16T best — biggest single lever +12R): env-tunable, applied AFTER schema
    # validation so the yaml stays the ruled base. Bounded 0..20. Sim first;
    # live per Michael's word.
    try:
        import os as _os
        _ov = _os.getenv("STOP_ANCHOR_OFFSET_TICKS_OVERRIDE")
        if _ov:
            _ovi = int(_ov)
            if 0 < _ovi <= 20:
                p["anchor_offset_ticks"] = _ovi
                data["principles"] = p
    except (TypeError, ValueError):
        pass

    if not (0 < data.get("risk_cap_points", 0) <= max_risk):
        errors.append(f"risk_cap_points={data.get('risk_cap_points')} out of range")

    for name in ("contract_ladder", "t1_ladder_continuation", "t1_ladder_continuation_v2"):
        rows = data.get(name)
        if not isinstance(rows, list) or not rows:
            errors.append(f"{name}: missing/empty"); continue
        for r in rows:
            if "max_risk_points" not in r:
                errors.append(f"{name}: row missing max_risk_points")
            if name == "contract_ladder" and not (1 <= r.get("contracts", 0) <= max_contracts):
                errors.append(f"contract_ladder.contracts={r.get('contracts')} out of range")
            if name.startswith("t1_ladder_continuation") and not (t1_min <= r.get("t1_r", 0) <= t1_max):
                errors.append(f"t1_ladder.t1_r={r.get('t1_r')} out of range")

    mc = data.get("mode_caps", {})
    for k in ("strategic", "tactical"):
        if not (1 <= mc.get(k, 0) <= max_contracts):
            errors.append(f"mode_caps.{k}={mc.get(k)} out of range")

    anchors = data.get("anchors", {})
    if not isinstance(anchors, dict) or len(anchors) < 14:
        errors.append(f"anchors: expected 14 patterns, got {len(anchors) if isinstance(anchors, dict) else 'non-dict'}")

    if errors:
        logger.warning("[ConfigLoader] stop_anchors validation errors: %s", errors[:6])
        return None
    return data
