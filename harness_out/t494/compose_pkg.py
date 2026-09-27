#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-494 (27.09): compose several single-change tree variants (each a diff vs the live tree) into one package tree,
so the COMBINATION is replayed before anything goes live (branches measured alone can interact through the one
live slot). usage: compose_pkg.py <out.yaml> tree_s1.yaml tree_s2.yaml …   (paths relative to harness_out/t494)"""
import difflib, os, sys
import yaml

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
HDR = "# VARIANT"
base = open(os.path.join(ROOT, "config", "decision_tree_v3.yaml"), encoding="utf-8").read().splitlines(keepends=True)
ops = []
for f in sys.argv[2:]:
    v = [l for l in open(os.path.join(HERE, f), encoding="utf-8").read().splitlines(keepends=True) if not l.startswith(HDR)]
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=base, b=v, autojunk=False).get_opcodes():
        if tag != "equal":
            ops.append((i1, i2, v[j1:j2], f))
ops.sort(key=lambda o: (o[0], o[1]))
for a, b in zip(ops, ops[1:]):                      # no two variants may touch the same base lines
    if b[0] < a[1] or (b[0] == a[0] and b[1] == a[1] and a[1] > a[0]):
        sys.exit(f"overlap: {a[3]} [{a[0]},{a[1]}) vs {b[3]} [{b[0]},{b[1]})")
out = list(base)
for i1, i2, new, f in sorted(ops, key=lambda o: (o[0], o[1]), reverse=True):
    out[i1:i2] = new
txt = "# VARIANT (harness only, 27.09) — package of " + " + ".join(sys.argv[2:]) + " — NOT the live tree\n" + "".join(out)
yaml.safe_load(txt)
open(os.path.join(HERE, sys.argv[1]), "w", encoding="utf-8").write(txt)
print("wrote", sys.argv[1], "with", len(ops), "hunks from", ", ".join(sys.argv[2:]))
