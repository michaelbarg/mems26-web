# -*- coding: utf-8 -*-
"""T-619 — Michael's circumstance rulings → a decision-tree VARIANT (Michael 20.10 23:5x: "I don't need you to
test me, I need us to improve the system — so it has to be general: something that lets us improve the trees
in these circumstances").

A ruling (the "נסיבות" page, artifact db collection branch_rules) names a circumstance = a TAKE leaf of the tree
(reached by the card's representative vector vec0) and optionally one feature value inside it. Decisions:
  skip      — the circumstance goes to SKIP (id rule_<card id>)
  edge_only — inside the circumstance: LONG only at near_val|below_value, SHORT only at near_vah|above_value
  keep / measure / other — no tree change ("measure" is a request to report the number; not applied)
The change is COPY-ON-WRITE along the exact path to that leaf, so YAML-anchor subtrees shared by other paths are
untouched. Every rule is verified by walking: vec0 must reach the card's leaf on the base tree; after the change
vec0 (with the feature = value) must reach the new SKIP, and a vector outside the circumstance the old leaf.
The live config/decision_tree_v3.yaml is never written — the output is a variant file for the harness
(DECISION_TREE_V3_PATH) and, after a passing measurement + Michael's standing "execute", the demo.

usage: python3 scripts/tree_rule_variant.py --rules rules.json --out config/decision_tree_v3.rules_<tag>.yaml
                                            [--base config/decision_tree_v3.t616_edge.yaml] [--only skip,edge_only]
rules.json = [{"id", "leaf", "kind", "feature", "value", "decision", "vec0"}, …] (the branch_rules docs).
"""
import argparse, copy, json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)
import yaml  # noqa: E402
from backend.v9.services.decision_tree import walk, _match  # noqa: E402

EDGE = {"LONG": "near_val|below_value", "SHORT": "near_vah|above_value"}


def _walk_keys(node, vec):
    """[(parent_node, branch_key)] down to the leaf — the same choice rule as decision_tree.walk."""
    trail = []
    for _ in range(40):
        if "leaf" in node:
            return trail, node
        feat, branches = node.get("split"), node.get("branches") or {}
        value, key = vec.get(feat), None
        for k in branches:
            if k != "*" and _match(str(k), value):
                key = k
                break
        if key is None and "*" in branches:
            key = "*"
        if key is None:
            return trail, None
        trail.append((node, key))
        node = branches[key]
    return trail, None


def _skip(rule, why):
    return {"leaf": "SKIP", "id": "rule_" + str(rule["id"]), "note": why}


def _edge_only(orig, rule):
    return {"split": "direction", "branches": {
        d: {"split": "zone", "branches": {EDGE[d]: orig, "*": _skip(rule, "%s only at the edge (%s)" % (d, EDGE[d]))}}
        for d in ("LONG", "SHORT")} | {"*": orig}}


def apply_rule(root, rule):
    vec = dict(rule["vec0"] or {})
    trail, leaf = _walk_keys(root, vec)
    got, _ = walk(root, vec)
    if leaf is None or str(got.get("id")) != str(rule["leaf"]):
        return root, "SKIPPED: vec0 reaches %r, not the card's leaf %r (tree moved)" % (got.get("id"), rule["leaf"])
    if got.get("leaf") != "TAKE":
        return root, "SKIPPED: the leaf is %s, not TAKE" % got.get("leaf")
    why = "Michael circumstance ruling (%s) on %s%s" % (rule["decision"], rule["leaf"],
                                                         " when %s=%s" % (rule["feature"], rule["value"]) if rule.get("feature") else "")
    # a leaf without an explicit id is named by its path — pin it, so the split below does not rename it
    leaf = dict(leaf)
    leaf.setdefault("id", got.get("id"))
    new = _skip(rule, why) if rule["decision"] == "skip" else _edge_only(leaf, rule)
    if rule.get("feature"):
        new = {"split": rule["feature"], "branches": {str(rule["value"]): new, "*": leaf}}
    # copy-on-write along the path
    new_root = copy.copy(root)
    new_root["branches"] = dict(root.get("branches") or {})
    cur = new_root
    for i, (_node, key) in enumerate(trail):
        if i == len(trail) - 1:
            cur["branches"][key] = new
        else:
            child = copy.copy(cur["branches"][key])
            child["branches"] = dict(child.get("branches") or {})
            cur["branches"][key] = child
            cur = child
    # verify
    v_in = dict(vec)
    if rule.get("feature"):
        v_in[rule["feature"]] = rule["value"]
    a, _ = walk(new_root, v_in)
    if rule["decision"] == "skip":
        assert a.get("leaf") == "SKIP" and a.get("id") == "rule_" + str(rule["id"]), a
    if rule.get("feature"):
        v_out = dict(vec)
        v_out[rule["feature"]] = "__other__"
        b, _ = walk(new_root, v_out)
        assert str(b.get("id")) == str(rule["leaf"]), (b.get("id"), rule["leaf"])
    return new_root, "applied"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default=os.path.join(ROOT, "config", "decision_tree_v3.t616_edge.yaml"))
    ap.add_argument("--only", default="skip,edge_only")
    a = ap.parse_args()
    if os.path.abspath(a.out) == os.path.abspath(os.path.join(ROOT, "config", "decision_tree_v3.yaml")):
        sys.exit("refusing to write the live tree")
    base = yaml.safe_load(open(a.base, encoding="utf-8"))
    rules = [r for r in json.load(open(a.rules, encoding="utf-8")) if r.get("decision") in a.only.split(",")]
    root, log = base["root"], []
    for r in rules:
        root, st = apply_rule(root, r)
        log.append("%s %s %s=%s → %s" % (r["id"], r["decision"], r.get("feature"), r.get("value"), st))
    out = {"version": str(base.get("version")) + "-rules", "seeded_from": "%s + %d circumstance rulings" % (
        os.path.basename(a.base), sum(1 for x in log if x.endswith("applied"))), "rulings_log": log, "root": root}
    yaml.safe_dump(out, open(a.out, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False, width=140)
    chk = yaml.safe_load(open(a.out, encoding="utf-8"))
    assert "root" in chk
    print("\n".join(log) or "no applicable rulings")
    print("→", a.out)


if __name__ == "__main__":
    main()
