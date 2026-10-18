#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super-agent T1 — build a DECISION_TREE_V3 yaml from a learned cell policy (t1_cells.py --out): the tree asks the
policy's questions in the doctrine's order and answers TAKE only inside the listed cells; everything else is SKIP
(id t1_policy). Measurement variant — never live without a ruling.
usage: build_tree.py <policy.json> <out.yaml> [--version=3.5.0-t1] [--cells=hindsight|forward]"""
import sys, json, yaml
pol = json.load(open(sys.argv[1])); out = sys.argv[2]
opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[3:] if a.startswith("--")}
cells = list(pol["hindsight_cells"].keys()) if opt.get("cells") == "hindsight" else list(pol["cells"])
key = pol["key"]
def node(depth, prefix):
    """nested split on key[depth]; leaf TAKE when the full path is a policy cell."""
    if depth == len(key):
        return {"leaf": "TAKE", "id": "t1_policy:" + "|".join(prefix), "note": "learned cell (forward-only)"}
    vals = sorted({c.split("|")[depth] for c in cells if c.split("|")[:depth] == prefix})
    branches = {v: node(depth + 1, prefix + [v]) for v in vals}
    branches["*"] = {"leaf": "SKIP", "id": "t1_policy", "note": "outside the learned cells"}
    return {"split": key[depth], "branches": branches}
tree = {"version": opt.get("version", "3.5.0-t1"),
        "seeded_from": f"t1_cells.py policy {sys.argv[1]} — {len(cells)} cells, key {key}, rate>={pol['rate']}, nmin>={pol['nmin']}",
        "root": node(0, [])}
yaml.safe_dump(tree, open(out, "w"), allow_unicode=True, sort_keys=False, width=200)
print(f"{out}: {len(cells)} TAKE cells over {key}")
