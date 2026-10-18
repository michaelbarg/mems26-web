# -*- coding: utf-8 -*-
"""fix-agent 18.10 (T-589): BRIEF §2.2 #3 — where does the live tree (3.4.0) route ZLR SHORT on a Normal day 18-19h?
Reads the same-night reference vectors (t567ref, 70 sessions) and groups them by the path the tree took."""
import glob, json, os, sys, collections
ROOT = "/Users/michael/Downloads/mems26_web_git"; os.chdir(ROOT); sys.path.insert(0, ROOT)
import yaml
from backend.v9.services import decision_tree as dt3
live = yaml.safe_load(open("config/decision_tree_v3.yaml", encoding="utf-8"))
groups = collections.Counter(); rows = []
n = 0
for p in sorted(glob.glob("harness_out/t466/t567ref_2026-*.json")):
    j = json.load(open(p))
    for r in j.get("routes") or []:
        tv = r.get("tree_v3")
        if not isinstance(tv, dict) or not isinstance(tv.get("vec"), dict):
            continue
        vec = tv["vec"]; n += 1
        if vec.get("pattern") != "ZLR" or vec.get("direction") != "SHORT":
            continue
        if vec.get("day_type") != "Normal" or vec.get("hour") not in (18, 19):
            continue
        leaf, path = dt3.walk(live["root"], vec)
        key = (vec.get("opening_type"), vec.get("phase"), vec.get("structure"), vec.get("zone"), vec.get("rel_bias"),
               vec.get("edge"), vec.get("kind"), str(leaf.get("leaf")).upper(), leaf.get("id"))
        groups[key] += 1
        rows.append((os.path.basename(p).split("_", 1)[1][:10], r.get("il", "")[:5], key, r.get("live_blocked_by"), r.get("decision")))
print("vectors total %d · ZLR SHORT Normal 18-19h: %d" % (n, len(rows)))
for k, c in groups.most_common():
    print("%3d  ot=%s phase=%s structure=%s zone=%s bias=%s edge=%s kind=%s => %s (%s)" % ((c,) + k))
print("--- by session ---")
for s, il, key, lb, dec in rows:
    print("  %s %s %s/%s/%s zone=%s bias=%s => %s id=%s blocked=%s dec=%s" % (s, il, key[0], key[1], key[2], key[3], key[4], key[7], key[8], lb, dec))
