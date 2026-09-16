"""T-392: Draft decision tree v2 — evaluator + loader.

Shadow-mode only.  NOT connected to the firing path.

    from backend.v9.services.dalton_tree import evaluate, load_tree
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from backend.v9.services.dalton_playbook import _match_condition

logger = logging.getLogger(__name__)

_TREE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "config"
    / "dalton_tree_v2_draft.yaml"
)

_CACHED_TREE: Optional[List[Dict]] = None


def load_tree(path: Optional[str] = None) -> List[Dict]:
    """Load the draft decision tree from YAML.

    Returns:
        List of rule dicts, each with id/phase/condition/decision/source/measured.
    """
    global _CACHED_TREE
    if _CACHED_TREE is not None and path is None:
        return _CACHED_TREE
    p = Path(path) if path else _TREE_PATH
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    rules = data.get("rules", []) if isinstance(data, dict) else []
    if path is None:
        _CACHED_TREE = rules
    return rules


def invalidate_cache() -> None:
    """Clear the cached tree (for testing)."""
    global _CACHED_TREE
    _CACHED_TREE = None


def evaluate(
    tree: List[Dict],
    vector: Dict[str, Any],
    setup: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate the draft tree against a setup's situation vector.

    First matching rule wins.  No match -> stand_down.

    Args:
        tree:   list of rule dicts from load_tree().
        vector: SituationVector-as-dict (from setup metadata).
        setup:  the full setup dict (for direction/classification fallback).

    Returns:
        {"decision": "allow"|"block"|"stand_down", "row": rule_id, "reason": ...}
    """
    # Build a merged namespace: vector fields + setup fields for convenience
    ns = dict(vector) if vector else {}
    if "direction" not in ns:
        ns["direction"] = (setup.get("direction") or "").upper()
    if "classification" not in ns:
        ns["classification"] = (
            setup.get("classification") or setup.get("pattern") or ""
        )
    if "entry_kind" not in ns:
        ns["entry_kind"] = setup.get("entry_kind", "")

    # opening_type and day_type for _match_condition
    opening_type = ns.get("opening_type") or setup.get("opening_type") or ""
    day_type = ns.get("day_type") or setup.get("day_type") or ""

    phase = ns.get("phase") or setup.get("phase") or ""

    for rule in tree:
        # Phase filter: if rule specifies phases, check membership
        rule_phases = rule.get("phase")
        if rule_phases and phase not in rule_phases:
            continue

        cond = rule.get("condition", "")
        if not cond:
            continue

        try:
            if _match_condition(cond, opening_type, day_type, vector=ns):
                decision = rule.get("decision", "stand_down")
                return {
                    "decision": _normalize_decision(decision),
                    "row": rule.get("id", "?"),
                    "reason": rule.get("note", cond),
                }
        except Exception as exc:
            logger.debug("[DaltonTree] rule %s eval error: %s", rule.get("id"), exc)
            continue

    return {"decision": "stand_down", "row": "no_match", "reason": "no rule matched"}


def _normalize_decision(raw: str) -> str:
    """Map tree decisions to the three canonical values for comparison."""
    raw_lower = raw.lower()
    if raw_lower in ("allow", "allow_if_location_ok", "skip_no_label_gate"):
        return "allow"
    if raw_lower == "block":
        return "block"
    return "stand_down"
