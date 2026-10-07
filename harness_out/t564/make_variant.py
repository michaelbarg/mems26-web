# -*- coding: utf-8 -*-
"""T-564 (Michael 07.10 17:52): ONE allow-list entry as a tree variant — INITIATIVE_SHORT on a Variation day between
18:00 and 19:59 IL (BRIEF §2.2, calibration context (Variation, 18-19h, INITIATIVE_SHORT, SHORT)). Builds
config/decision_tree_v3.t564_allow.yaml from the live 3.4.0 by text: the Variation row gets a `pattern` branch
INITIATIVE_SHORT → hour 18|19 → TAKE (exit 1.5R/2.5R like the row's own BREAK leaf); everything else, including
INITIATIVE_SHORT at other hours, keeps the row's existing rel_bias logic. The live file is never touched.
Then verifies on every t529b vector that the ONLY decisions that change are INITIATIVE_SHORT · phase C ·
Variation|Normal_Variation · hour 18/19, and reports leaf counts."""
import glob, json, os, sys
ROOT = "/Users/michael/Downloads/mems26_web_git"; os.chdir(ROOT); sys.path.insert(0, ROOT)
SRC = "config/decision_tree_v3.yaml"; DST = "config/decision_tree_v3.t564_allow.yaml"
t = open(SRC, encoding="utf-8").read()
OLD = ('  variation_row: &variation_row\n    split: pattern\n    branches:\n'
       '      VAR_CONT:            # T-458א producer (flag VAR_CONT_V1, measured Δ+16$ net ⇒ OFF): kinds/location skipped, bias kept\n'
       '        split: rel_bias\n        branches:\n          against: *skip_bias\n'
       '          "*": {leaf: TAKE, note: "VAR_CONT: structural pullback-continuation with the extension"}\n'
       '      "*":\n        split: rel_bias\n        branches:\n          with: *take_with_hint\n'
       '          against: *against_fallback\n          "*": *kinds_variation\n')
NEW = ('  var_default: &var_default        # T-564 variant: the row\'s existing bias logic, reused under the allow branch\n'
       '    split: rel_bias\n    branches:\n      with: *take_with_hint\n      against: *against_fallback\n      "*": *kinds_variation\n'
       '  variation_row: &variation_row\n    split: pattern\n    branches:\n'
       '      VAR_CONT:            # T-458א producer (flag VAR_CONT_V1, measured Δ+16$ net ⇒ OFF): kinds/location skipped, bias kept\n'
       '        split: rel_bias\n        branches:\n          against: *skip_bias\n'
       '          "*": {leaf: TAKE, note: "VAR_CONT: structural pullback-continuation with the extension"}\n'
       '      INITIATIVE_SHORT:    # T-564 (Michael 07.10 17:52, BRIEF §2.2 allow #1): measurement variant, not live\n'
       '        split: hour\n        branches:\n          "18|19":\n            leaf: TAKE\n'
       '            id: allow_initiative_short_variation_1819\n            exit: {t1_r: 1.5, t2_r: 2.5}\n'
       '            note: "T-564 allow: INITIATIVE_SHORT on a Variation day 18:00-19:59 IL regardless of the hint (calibration: train +35$/cand)"\n'
       '          "*": *var_default\n'
       '      "*": *var_default\n')
assert t.count(OLD) == 1, "variation_row block not found verbatim - the live file changed; stop"
v = t.replace(OLD, NEW, 1).replace('version: "3.4.0"', 'version: "3.4.0-t564_allow"', 1)
open(DST, "w", encoding="utf-8").write(v); print("wrote", DST)

import yaml
from backend.v9.services import decision_tree as dt3
live = yaml.safe_load(open(SRC, encoding="utf-8")); var = yaml.safe_load(open(DST, encoding="utf-8"))
print("leaves live=%d variant=%d" % (len(dt3.leaves(live["root"])), len(dt3.leaves(var["root"]))))
# verification on every t529b vector: which decisions change, and are they all the intended context
changed, same, n = [], 0, 0
for p in sorted(glob.glob("harness_out/t466/t529b_2026-*.json")):
    j = json.load(open(p))
    for r in j.get("routes") or []:
        tv = r.get("tree_v3")
        if not isinstance(tv, dict) or not isinstance(tv.get("vec"), dict):
            continue
        n += 1; vec = tv["vec"]
        l0, _ = dt3.walk(live["root"], vec); l1, _ = dt3.walk(var["root"], vec)
        a0, a1 = str(l0.get("leaf")).upper(), str(l1.get("leaf")).upper()
        if a0 == a1:
            same += 1
        else:
            changed.append((os.path.basename(p)[6:16], r.get("il", "")[:5], vec.get("pattern"), vec.get("phase"), vec.get("day_type"),
                            vec.get("hour"), vec.get("rel_bias"), a0, a1))
print("vectors %d · same %d · changed %d" % (n, same, len(changed)))
bad = [c for c in changed if not (c[2] == "INITIATIVE_SHORT" and c[3] == "C" and c[4] in ("Variation", "Normal_Variation") and c[5] in (18, 19) and c[7] == "SKIP" and c[8] == "TAKE")]
print("changed outside the intended context: %d" % len(bad))
for c in changed[:40]:
    print("   ", c)
print("VERDICT:", "OK - only the allow context flips SKIP->TAKE" if not bad else "FAIL - unintended changes, do not run")
