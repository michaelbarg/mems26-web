"""DaltonPlaybook — session-phase decision tree (Michael ruling 09.09).

Pure function: intent(phase, opening_type, day_type, ...) → Intent.
Replaces compass/playbook/location_gate with one gate.

    from backend.v9.services.dalton_playbook import intent, load_config
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional, Set

import yaml

logger = logging.getLogger(__name__)

_CONFIG: Optional[Dict] = None
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "dalton_playbook.yaml"


def load_config() -> Dict:
    global _CONFIG
    if _CONFIG is None:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            _CONFIG = yaml.safe_load(f)
    return _CONFIG


@dataclass
class Intent:
    bias: str  # LONG | SHORT | BOTH | NONE
    entry_kinds: FrozenSet[str]
    stop_rule: Optional[str]
    target_rule: Optional[str]
    size_frac: float
    runner: bool
    reason: str


_STAND_DOWN = Intent(
    bias="NONE", entry_kinds=frozenset(), stop_rule=None,
    target_rule=None, size_frac=0.0, runner=False, reason="stand-down")


def enabled() -> bool:
    return os.getenv("DALTON_PLAYBOOK_V1", "0").strip().lower() in ("1", "true", "yes")


def entry_kind_for(classification: str) -> str:
    """Map a pattern classification to an entry_kind."""
    cfg = load_config()
    m = cfg.get("entry_kind_map", {})
    return m.get(classification, m.get(classification.upper(), "BREAK"))


def _resolve_phase(now_il_hhmm: str, cfg: Optional[Dict] = None) -> str:
    """Determine session phase from IL time HH:MM."""
    try:
        h, m = int(now_il_hhmm[:2]), int(now_il_hhmm[3:5])
        mins = h * 60 + m
    except (ValueError, IndexError):
        return "D"
    if mins < 16 * 60 + 30:
        return "A"  # pre-open, treat as A
    if mins < 16 * 60 + 45:
        return "A"
    if mins < 17 * 60 + 30:
        return "B"
    if mins < 21 * 60:
        return "C"
    # phase_d policy: manage_only (default) or as_phase_c
    if cfg and cfg.get("phase_d") == "as_phase_c":
        return "C"
    return "D"


def _resolve_bias(rule_bias: str, opening_type: str, day_type: str,
                  direction_hint: Optional[str] = None) -> str:
    """Resolve bias keywords to LONG/SHORT/BOTH/NONE."""
    if rule_bias in ("LONG", "SHORT", "BOTH", "NONE"):
        return rule_bias
    if rule_bias == "drive_direction":
        # Drive direction from opening_type: OPEN_DRIVE → same as the gap/first-bar
        return direction_hint or "BOTH"
    if rule_bias == "reversal_direction":
        # Opposite of drive
        if direction_hint == "LONG":
            return "SHORT"
        if direction_hint == "SHORT":
            return "LONG"
        return "BOTH"
    if rule_bias == "trend_direction":
        return direction_hint or "BOTH"
    if rule_bias.startswith("extension_direction"):
        return direction_hint or "BOTH"
    return rule_bias


def _match_condition(cond: str, opening_type: str, day_type: str,
                     vector: Optional[Dict] = None) -> bool:
    """Evaluate a rule condition string.

    Supports legacy forms (opening_type ==, day_type in, etc.) and new
    ``expr:`` form that evaluates a safe AST expression over the situation
    vector (T-391). Unknown names or None values in comparisons → False
    (fail-closed for the rule, not the system).
    """
    if cond == "default":
        return True
    if cond.startswith("opening_type == "):
        val = cond.split("== ", 1)[1].strip()
        return opening_type == val
    if cond.startswith("opening_type in "):
        vals = cond.split("in ", 1)[1].strip().strip("[]").split(",")
        vals = [v.strip().strip("'\"") for v in vals]
        return opening_type in vals
    if cond.startswith("day_type == "):
        val = cond.split("== ", 1)[1].strip()
        return day_type == val
    if cond.startswith("day_type in "):
        vals = cond.split("in ", 1)[1].strip().strip("[]").split(",")
        vals = [v.strip().strip("'\"") for v in vals]
        return day_type in vals
    if cond.startswith("expr:"):
        expr_str = cond[5:].strip()
        return _eval_safe_expr(expr_str, opening_type, day_type, vector or {})
    return False


# ── T-391: safe expression evaluator on the situation vector ──────────
import ast

_SAFE_NODES = frozenset({
    ast.Expression, ast.BoolOp, ast.And, ast.Or,
    ast.UnaryOp, ast.Not,
    ast.Compare,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
    ast.Name, ast.Load,
    ast.Constant,
    ast.List, ast.Tuple,
})


def validate_expr(expr_str: str) -> ast.Expression:
    """Parse and whitelist-check an expr string. Raises ValueError on unsafe nodes."""
    try:
        tree = ast.parse(expr_str, mode='eval')
    except SyntaxError as e:
        raise ValueError(f"invalid expr syntax: {e}") from e
    for node in ast.walk(tree):
        if type(node) not in _SAFE_NODES:
            raise ValueError(
                f"unsafe AST node {type(node).__name__} in expr: {expr_str}")
    return tree


def _eval_safe_expr(expr_str: str, opening_type: str, day_type: str,
                    vector: Dict) -> bool:
    """Evaluate a safe expression against the vector namespace.

    Names resolve to vector fields first, then opening_type/day_type.
    Unknown name or None in comparison → False (fail-closed for the rule).
    """
    try:
        tree = validate_expr(expr_str)
    except ValueError:
        return False  # invalid expr → rule doesn't match

    ns = dict(vector)
    ns["opening_type"] = opening_type
    ns["day_type"] = day_type

    try:
        result = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, ns)
        return bool(result)
    except (NameError, TypeError, KeyError, AttributeError):
        # Unknown name or None in comparison → False
        return False


def intent(
    *,
    opening_type: str = "UNKNOWN",
    day_type: str = "",
    now_il_hhmm: str = "17:00",
    direction_hint: Optional[str] = None,
    vector: Optional[Dict] = None,
) -> Intent:
    """Compute the playbook intent for the current session state.

    Args:
        opening_type: from opening_detector_v2 (OPEN_DRIVE, etc.)
        day_type: from get_live_day_type (Trend_Normal, etc.)
        now_il_hhmm: current IL time as "HH:MM"
        direction_hint: LONG/SHORT from the opening or trend direction
        vector: SituationVector as dict (T-390/T-391), for expr: conditions
    """
    cfg = load_config()
    phase = _resolve_phase(now_il_hhmm, cfg)
    phase_cfg = cfg.get("phases", {}).get(phase)
    if not phase_cfg:
        return Intent(bias="NONE", entry_kinds=frozenset(), stop_rule=None,
                      target_rule=None, size_frac=0.0, runner=False,
                      reason=f"phase {phase} not configured")

    for rule in phase_cfg.get("rules", []):
        cond = rule.get("condition", "default")
        if _match_condition(cond, opening_type, day_type or "", vector=vector):
            bias = _resolve_bias(
                rule.get("bias", "NONE"), opening_type, day_type or "",
                direction_hint)
            kinds = frozenset(rule.get("entry_kinds", []))
            return Intent(
                bias=bias,
                entry_kinds=kinds,
                stop_rule=rule.get("stop_rule"),
                target_rule=rule.get("target_rule"),
                size_frac=float(rule.get("size_frac", 0.0)),
                runner=bool(rule.get("runner", False)),
                reason=f"phase={phase} cond={cond} bias={bias}",
            )

    return _STAND_DOWN


def evaluate_gate(setup: Dict[str, Any], it: Intent) -> Optional[Dict[str, str]]:
    """Check if a setup passes the DaltonPlaybook gate.

    Returns None if allowed, or {blocked_by, reason} if blocked.
    """
    direction = (setup.get("direction") or "").upper()
    classification = (setup.get("classification") or setup.get("pattern") or "")
    ek = entry_kind_for(classification)

    if it.size_frac <= 0:
        return {"blocked_by": "dalton_intent:stand_down", "reason": it.reason}

    if it.bias not in ("BOTH", direction) and it.bias != "NONE":
        return {
            "blocked_by": "dalton_intent:bias",
            "reason": f"bias={it.bias} rejects {direction} ({it.reason})",
        }

    if it.entry_kinds and ek not in it.entry_kinds:
        # kinds_apply_to policy: counter_bias_only means the kinds list
        # vetoes only COUNTER-direction entries; WITH-bias entries pass.
        cfg = load_config()
        _kinds_policy = cfg.get("kinds_apply_to", "all")
        # T-473 (25.09, replay knob — env override, default = the YAML policy): "none" makes the
        # kinds list advisory everywhere (bias + stand_down + location keep vetoing). Gate scorecard
        # 25.09 on 58 sessions: dalton_intent:kind refused 292 candidates, 50% win, Σ+$2,889 at
        # 1.5R — the most expensive gate in the chain; the day-total harness decides.
        _env_policy = (os.getenv("DALTON_KINDS_APPLY_TO") or "").strip().lower()
        if _env_policy in ("none", "counter_bias_only", "all"):
            _kinds_policy = _env_policy
        # T-477 replay knob: kinds advisory only in the listed phases (e.g. "B") — the 25.09 map of
        # circumstances: OPEN_AUCTION_IN · phase B · no-hint n=300, 52%, +$4,018 independent while
        # phase C/D with-hint candidates on the same days lose; the day-total harness decides.
        _adv_phases = {x.strip().upper() for x in (os.getenv("DALTON_KINDS_ADVISORY_PHASES") or "").split(",") if x.strip()}
        if _adv_phases:
            _ph = None
            for tok in str(it.reason or "").split():
                if tok.startswith("phase="):
                    _ph = tok[6:].strip(",;)").upper()
            if _ph in _adv_phases:
                _kinds_policy = "none"
        if _kinds_policy == "none":
            pass  # advisory — never blocks
        elif _kinds_policy == "counter_bias_only":
            # WITH a DIRECTIONAL bias → any kind allowed (Dalton: trade with the
            # drive). Under bias=BOTH the kinds list STILL applies — that is where
            # BREAK on rotation days loses (replay 09.09: −$392 / −$323 by rule).
            # cowork 09.09 12:30: `it.bias in ("BOTH", direction)` had turned this
            # into kinds-advisory-for-everyone (79 approved, Σ +60 instead of +607).
            if it.bias in ("LONG", "SHORT") and it.bias == direction:
                pass  # allowed — kinds list only blocks counter
            else:
                return {
                    "blocked_by": "dalton_intent:kind",
                    "reason": f"counter-bias entry_kind={ek} not in {sorted(it.entry_kinds)} ({it.reason})",
                }
        else:
            return {
                "blocked_by": "dalton_intent:kind",
                "reason": f"entry_kind={ek} not in {sorted(it.entry_kinds)} ({it.reason})",
            }

    return None  # allowed
