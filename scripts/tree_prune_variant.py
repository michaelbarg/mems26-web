#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tree_prune_variant.py — build a replay VARIANT of the live tree with named leaves set to SKIP.

CC_ORDER 2026-10-05 §3 stage 2: "the eight §1 leaves in SKIP, the rest of the tree identical".
The live tree is NOT touched: the variant is an expanded (anchor-free) copy written to
config/decision_tree_v3.<tag>.yaml and used only through DECISION_TREE_V3_PATH in the harness.

A prune target is either
  • a ruled leaf id            (e.g. d_with_extension — every leaf carrying that id → SKIP), or
  • a walk path                (e.g. opening_type=OPEN_AUCTION_IN/phase=C/day_type=Variation/pattern=*(ZLR)/rel_bias=with)
    where `feat=*(value)` means "the node's '*' branch, reached with that value". Pruning it precisely adds an
    explicit `value:` branch (a deep copy of the '*' subtree) so that ONLY that value is skipped and every
    other value keeps falling to '*' exactly as today.

Verification (printed): leaf counts, and a walk of every route vector in harness_out/t466/t529b_*.json through
both trees — the routes whose verdict changed, grouped by the live leaf they came from. Anything outside the
requested targets is a bug in this script and the variant must not be used.

usage: python3 scripts/tree_prune_variant.py --tag t543_prune --targets harness_out/t543/prune_targets.txt
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from backend.v9.services import decision_tree as dtree  # noqa: E402

LIVE = os.path.join(ROOT, "config", "decision_tree_v3.yaml")
_COPIES = set()   # id() of '*' copies this run created — a second target may descend into them


def parse_token(tok: str):
    feat, _, val = tok.partition("=")
    if val.startswith("*(") and val.endswith(")"):
        return feat, val[2:-1], True
    return feat, val, False


def explicit_match(branches: dict, value: str):
    for key in branches:
        if key == "*":
            continue
        if dtree._match(str(key), value):
            return key
    return None


def prune_path(root: dict, path: str, new_id: str, note: str) -> dict:
    """Descend `path` from root (creating explicit copies of '*' branches where the path says *(value)),
    then replace the leaf with SKIP. Returns the old leaf (for the report)."""
    node = root
    for tok in path.split("/"):
        feat, val, star = parse_token(tok)
        # the 3.3.0 root is an `hour` layer the walk-forward paths do not mention: pass through its '*'
        while node.get("split") != feat:
            br = node.get("branches") or {}
            if "*" not in br:
                raise SystemExit("path %s: expected split %s, node has split %s" % (path, feat, node.get("split")))
            node = br["*"]
        br = node["branches"]
        key = explicit_match(br, val)
        if star:
            if key is not None and id(br[key]) in _COPIES:
                node = br[key]                   # the copy an earlier target made for this same value
                continue
            if key is not None:
                raise SystemExit("path %s: %s=%s already has an explicit branch %r (the walk would not reach '*')" % (path, feat, val, key))
            if "*" not in br:
                raise SystemExit("path %s: no '*' branch at %s" % (path, feat))
            br[val] = copy.deepcopy(br["*"])   # a private copy: only this value changes
            _COPIES.add(id(br[val]))
            node = br[val]
        else:
            if key is None:
                raise SystemExit("path %s: no branch matches %s=%s" % (path, feat, val))
            node = br[key]
    if "leaf" not in node:
        raise SystemExit("path %s ends on a split node (%s), not a leaf" % (path, node.get("split")))
    old = dict(node)
    node.clear()
    node.update({"leaf": "SKIP", "id": new_id, "note": note, "was": {"leaf": old.get("leaf"), "id": old.get("id")}})
    return old


def prune_id(root: dict, leaf_id: str, note: str) -> int:
    """Every leaf carrying `id: leaf_id` → SKIP (keeps the id so reports still group it)."""
    n = 0
    stack = [root]
    while stack:
        node = stack.pop()
        if "leaf" in node:
            if node.get("id") == leaf_id and node.get("leaf") != "SKIP":
                node["was"] = {"leaf": node.get("leaf")}
                node["leaf"] = "SKIP"
                node["note"] = note
                n += 1
            continue
        for child in (node.get("branches") or {}).values():
            if isinstance(child, dict):
                stack.append(child)
    return n


def expand(tree: dict) -> dict:
    """Break YAML anchor sharing: every node becomes its own object."""
    return json.loads(json.dumps(tree, default=str))


def verdict(leaf: dict) -> str:
    return str(leaf.get("leaf") or "SKIP").upper()


def verify(live_root: dict, var_root: dict, glob_pat: str):
    files = sorted(glob.glob(glob_pat))
    changed = {}
    n_routes = 0
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        for r in d.get("routes") or []:
            vec = ((r.get("tree_v3") or {}).get("vec")) or None
            if not vec:
                continue
            n_routes += 1
            a, pa = dtree.walk(live_root, vec)
            b, pb = dtree.walk(var_root, vec)
            if verdict(a) != verdict(b):
                key = "%s → %s  [live leaf %s]" % (verdict(a), verdict(b), a.get("id"))
                changed[key] = changed.get(key, 0) + 1
    return n_routes, changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True, help="variant tag → config/decision_tree_v3.<tag>.yaml")
    ap.add_argument("--targets", required=True, help="file: one target per line (id:<leaf_id> or a walk path); # comments")
    ap.add_argument("--note", default="prune variant (replay only)")
    ap.add_argument("--verify-glob", default=os.path.join(ROOT, "harness_out", "t466", "t529b_*.json"))
    a = ap.parse_args(argv)

    with open(LIVE, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    live_root = data["root"]
    var_root = expand(live_root)
    n_live = len(dtree.leaves(live_root))

    targets = [l.strip() for l in open(a.targets, encoding="utf-8") if l.strip() and not l.startswith("#")]
    report = []
    for i, t in enumerate(targets, 1):
        if t.startswith("id:"):
            n = prune_id(var_root, t[3:].strip(), a.note)
            report.append("%d. id %s → SKIP (%d leaves)" % (i, t[3:].strip(), n))
        else:
            old = prune_path(var_root, t, "prune_%02d" % i, a.note)
            report.append("%d. %s : %s(%s) → SKIP" % (i, t, old.get("leaf"), old.get("id")))
    n_var = len(dtree.leaves(var_root))

    out = os.path.join(ROOT, "config", "decision_tree_v3.%s.yaml" % a.tag)
    doc = {"version": "%s-%s" % (data.get("version", "?"), a.tag),
           "note": "VARIANT for replay only (DECISION_TREE_V3_PATH). Built by scripts/tree_prune_variant.py from "
                   "config/decision_tree_v3.yaml %s; anchors expanded; targets: %s" % (data.get("version", "?"), os.path.relpath(a.targets, ROOT)),
           "root": var_root}
    with open(out, "w", encoding="utf-8") as fh:
        yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False, width=200)

    print("live leaves=%d  variant leaves=%d  (+%d explicit copies)" % (n_live, n_var, n_var - n_live))
    print("\n".join(report))
    n_routes, changed = verify(live_root, var_root, a.verify_glob)
    print("verify: %d route vectors walked; verdict changed on:" % n_routes)
    for k, v in sorted(changed.items(), key=lambda kv: -kv[1]):
        print("  %5d  %s" % (v, k))
    if not changed:
        print("  (none — the variant is identical to the live tree on these vectors)")
    print("wrote %s" % os.path.relpath(out, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
