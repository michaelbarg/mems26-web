"""decision_tree.py — DECISION_TREE_V3: one nested tree, walked once per candidate (Michael 25.09 12:10:
"ממש צריך להיות עץ! ולא טבלה שפועלת — או הטבלה צריכה להיות שכל קוביה שם מתפצלת לענפים ועצים").

Order of the questions (the doctrine's order, fixed): opening type → phase → day type → structure (what the
price actually did: IB extension none/up/down/two_sided) → pattern → the pattern's own circumstances
(rel_bias · zone · edge · test · volume · stop size). Every node asks ONE question; a leaf is an explicit
action — TAKE (with its stop/target/size policy) · SHADOW · SKIP — plus `measured` (n, win, Σ$, source, date).
Not a score: the tree never sums anything; it answers "in this circumstance, do this".

Schema (config/decision_tree_v3.yaml):
    node := {split: <feature>, branches: {<value>: node, "*": node}, note?: str}
          | {leaf: TAKE|SHADOW|SKIP, stop?: str, target?: str, size_frac?: float, id?: str, note?: str, measured?: {...}}
    <value> may be a single value, a "|"-separated list ("LONG|SHORT"), or "*" (default).
    numeric features (R_atr, hour) accept "<=x" / ">x" branch keys, tried in file order.

    from backend.v9.services.decision_tree import load_tree, walk, features_of_setup
    leaf, path = walk(tree, vector)        # path = [(feature, value_taken), ...]
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)
_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "decision_tree_v3.yaml"
_CACHE: Optional[Dict[str, Any]] = None
FEATURES = ("opening_type", "phase", "day_type", "structure", "pattern", "kind", "direction", "rel_bias",
            "zone", "prior_zone", "poc_side", "value_migration", "edge", "test", "volume", "delta", "R_atr", "hour", "system")


def value_migration(vah: float, val: float, prev_vah: float, prev_val: float) -> str:
    """Today's developing value vs yesterday's (Dalton): higher · lower · overlap_high · overlap_low · inside ·
    outside · unknown. The read that says whether the market is accepting new prices or rotating in old value."""
    try:
        vah, val, pvah, pval = float(vah or 0), float(val or 0), float(prev_vah or 0), float(prev_val or 0)
    except (TypeError, ValueError):
        return "unknown"
    if not (vah > val > 0 and pvah > pval > 0):
        return "unknown"
    if val >= pvah:
        return "higher"
    if vah <= pval:
        return "lower"
    if vah > pvah and val >= pval:
        return "overlap_high"
    if val < pval and vah <= pvah:
        return "overlap_low"
    if vah <= pvah and val >= pval:
        return "inside"
    return "outside"


def poc_side(price: float, poc: float, tol: float) -> str:
    """Where the entry sits vs the day's point of control: above · at · below · unknown."""
    try:
        price, poc = float(price or 0), float(poc or 0)
    except (TypeError, ValueError):
        return "unknown"
    if price <= 0 or poc <= 0:
        return "unknown"
    return "above" if price > poc + tol else "below" if price < poc - tol else "at"


def enabled() -> bool:
    return os.getenv("DECISION_TREE_V3", "0").strip().lower() in ("1", "true", "yes", "shadow")


def is_shadow() -> bool:
    return os.getenv("DECISION_TREE_V3", "0").strip().lower() == "shadow"


def load_tree(path: Optional[str] = None) -> Dict[str, Any]:
    """The tree from config/decision_tree_v3.yaml; DECISION_TREE_V3_PATH (replay variants) overrides the file."""
    global _CACHE
    if _CACHE is not None and path is None:
        return _CACHE
    if path is None and os.getenv("DECISION_TREE_V3_PATH"):
        path = os.getenv("DECISION_TREE_V3_PATH")
        _use_cache = True
    else:
        _use_cache = path is None
    with open(Path(path) if path else _PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    root = data.get("root") if isinstance(data, dict) else None
    if not isinstance(root, dict):
        raise ValueError("decision_tree_v3.yaml: missing 'root' node")
    if _use_cache:
        _CACHE = root
    return root


def invalidate_cache() -> None:
    global _CACHE
    _CACHE = None


def _match(key: str, value: Any) -> bool:
    """Does branch key `key` accept `value`?"""
    if key == "*":
        return True
    ks = str(key)
    if ks.startswith("<=") or ks.startswith(">"):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False
        if ks.startswith("<="):
            return v <= float(ks[2:])
        return v > float(ks[1:])
    sv = "" if value is None else str(value)
    return any(sv.upper() == alt.strip().upper() for alt in ks.split("|"))


def walk(tree: Dict[str, Any], vector: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Tuple[str, Any]]]:
    """Walk from the root to a leaf. Unknown feature values fall to the node's "*" branch; a node without a
    matching branch and without "*" is a SKIP leaf (never silently TAKE)."""
    node = tree; path: List[Tuple[str, Any]] = []; depth = 0
    while True:
        if "leaf" in node:
            leaf = dict(node); leaf.setdefault("id", "/".join(f"{f}={v}" for f, v in path) or "root")
            return leaf, path
        feat = node.get("split")
        branches = node.get("branches") or {}
        if not feat or not isinstance(branches, dict):
            return {"leaf": "SKIP", "id": "malformed", "note": "node without split/branches"}, path
        value = vector.get(feat)
        chosen = None; key_taken = None
        for key, child in branches.items():
            if key == "*":
                continue
            if _match(str(key), value):
                chosen, key_taken = child, str(key); break
        if chosen is None and "*" in branches:
            chosen, key_taken = branches["*"], "*"
        if chosen is None:
            return {"leaf": "SKIP", "id": "/".join(f"{f}={v}" for f, v in path) + f"/{feat}=?", "note": f"no branch for {feat}={value}"}, path
        path.append((feat, value if key_taken != "*" else f"*({value})"))
        node = chosen; depth += 1
        if depth > 32:
            return {"leaf": "SKIP", "id": "too-deep", "note": "tree deeper than 32"}, path


def structure_of(ib_high: Any, ib_low: Any, session_high: Any, session_low: Any, phase: str) -> str:
    """What the price actually did vs the completed IB: none / up / down / two_sided. Before phase C: 'forming'."""
    if phase in ("A", "B"):
        return "forming"
    try:
        ibh, ibl, sh, sl = float(ib_high or 0), float(ib_low or 0), float(session_high or 0), float(session_low or 0)
    except (TypeError, ValueError):
        return "unknown"
    if not (ibh > ibl > 0 and sh > 0 and sl > 0):
        return "unknown"
    need = max(2.0, 0.10 * (ibh - ibl)); up = sh - ibh >= need; dn = ibl - sl >= need
    return "two_sided" if (up and dn) else "up" if up else "down" if dn else "none"


def features_of_setup(setup: Dict[str, Any], *, opening_type: str, phase: str, day_type: str, structure: str,
                      dir_hint: Optional[str], zone: Optional[str], kind: str, atr: Optional[float], hour: Optional[int],
                      prior_zone: Optional[str] = None, poc_side_: Optional[str] = None, migration: Optional[str] = None) -> Dict[str, Any]:
    """The situation vector the tree walks, from what the gateway already knows about a setup."""
    direction = (setup.get("direction") or "").upper()
    meta = setup.get("metadata") if isinstance(setup.get("metadata"), dict) else {}
    try:
        entry = float(setup.get("entry_price") or 0); stop = float(setup.get("stop") or 0)
        r_atr = round(abs(entry - stop) / float(atr), 2) if atr and entry and stop else None
    except (TypeError, ValueError):
        r_atr = None
    rel = "with" if dir_hint and dir_hint == direction else ("against" if dir_hint in ("LONG", "SHORT") else "none")
    return {
        "opening_type": (opening_type or "UNKNOWN").upper(), "phase": phase, "day_type": day_type or "FORMING",
        "structure": structure, "pattern": str(setup.get("classification") or setup.get("pattern") or "?").upper(),
        "kind": kind, "direction": direction, "rel_bias": rel, "zone": zone or "unknown",
        # the day profile (T-480, Michael 25.09 17:00 "האם לעץ מחוברים גם פרופיל היום"): where the entry sits vs
        # YESTERDAY's value (the only location reference before today's VA forms), vs today's POC, and how today's
        # value is migrating against yesterday's — all splittable, none used by the seed (parity)
        "prior_zone": prior_zone or "unknown", "poc_side": poc_side_ or "unknown", "value_migration": migration or "unknown",
        "edge": "ib" if meta.get("near_ib_edge") else ("value" if (zone or "").startswith("near_") else "none"),
        "test": "retest" if meta.get("pullback_before") else ("break" if meta.get("structure_break") else "none"),
        "volume": "high" if meta.get("vol_trig") else "normal", "delta": "with" if meta.get("delta_with") else "none",
        "R_atr": r_atr, "hour": hour, "system": setup.get("firing_system"),
    }


def leaves(tree: Dict[str, Any], path: Optional[List[Tuple[str, str]]] = None) -> List[Dict[str, Any]]:
    """All leaves with their paths (for the board and the nightly measurement)."""
    path = path or []; out = []
    if "leaf" in tree:
        d = dict(tree); d["path"] = list(path); d.setdefault("id", "/".join(f"{f}={v}" for f, v in path) or "root"); return [d]
    for key, child in (tree.get("branches") or {}).items():
        out.extend(leaves(child, path + [(tree.get("split"), key)]))
    return out
