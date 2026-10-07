# -*- coding: utf-8 -*-
"""T-564b (fix-agent 08.10 01:15): the permit ALONE. t564a (cowork's variant) bundled two changes — the allow
(against-the-hint INITIATIVE_SHORT on a Variation day 18-19h: SKIP -> TAKE) AND an exit override
(exit 1.5R/2.5R) on the with-the-hint INITIATIVE_SHORT trades that the live tree already TAKEs via
take_with_hint (default exit). 07.27 showed the bundle: the same 18:35 trade changed its exit (+47.50 ->
+61.25), freed the slot and three losing trades followed (-141.25) - not the permit's doing.
Here only the `against` SKIP (skip_bias) becomes a plain TAKE (take_with_hint semantics, default exit);
with / none / failed_extension / other hours keep the live row verbatim. The live file is never touched.
Verification on every t529b vector: decisions change ONLY in the intended context SKIP->TAKE, and the
leaf's exit policy never changes where the decision did not (the check t564a lacked)."""
import glob, json, os, sys
ROOT = "/Users/michael/Downloads/mems26_web_git"; os.chdir(ROOT); sys.path.insert(0, ROOT)
SRC = "config/decision_tree_v3.yaml"; DST = "config/decision_tree_v3.t564b_allow.yaml"
t = open(SRC, encoding="utf-8").read()
OLD = ('  variation_row: &variation_row\n    split: pattern\n    branches:\n'
       '      VAR_CONT:            # T-458א producer (flag VAR_CONT_V1, measured Δ+16$ net ⇒ OFF): kinds/location skipped, bias kept\n'
       '        split: rel_bias\n        branches:\n          against: *skip_bias\n'
       '          "*": {leaf: TAKE, note: "VAR_CONT: structural pullback-continuation with the extension"}\n'
       '      "*":\n        split: rel_bias\n        branches:\n          with: *take_with_hint\n'
       '          against: *against_fallback\n          "*": *kinds_variation\n')
NEW = ('  var_default: &var_default        # T-564b variant: the row\'s existing bias logic, reused under the allow branch\n'
       '    split: rel_bias\n    branches:\n      with: *take_with_hint\n      against: *against_fallback\n      "*": *kinds_variation\n'
       '  variation_row: &variation_row\n    split: pattern\n    branches:\n'
       '      VAR_CONT:            # T-458א producer (flag VAR_CONT_V1, measured Δ+16$ net ⇒ OFF): kinds/location skipped, bias kept\n'
       '        split: rel_bias\n        branches:\n          against: *skip_bias\n'
       '          "*": {leaf: TAKE, note: "VAR_CONT: structural pullback-continuation with the extension"}\n'
       '      INITIATIVE_SHORT:    # T-564b (fix-agent 08.10): the permit ALONE - only the against-the-hint SKIP flips; measurement variant, not live\n'
       '        split: hour\n        branches:\n          "18|19":\n            split: rel_bias\n            branches:\n'
       '              with: *take_with_hint\n'
       '              against:\n                split: edge\n                branches:\n'
       '                  failed_extension: *take_failed_ext\n'
       '                  "*":\n                    leaf: TAKE\n                    id: allow_initiative_short_variation_1819\n'
       '                    note: "T-564b allow: INITIATIVE_SHORT against the hint on a Variation day 18:00-19:59 IL, taken like a with-hint entry (default exit); calibration train +35.7$/cand"\n'
       '              "*": *kinds_variation\n'
       '          "*": *var_default\n'
       '      "*": *var_default\n')
assert t.count(OLD) == 1, "variation_row block not found verbatim - the live file changed; stop"
v = t.replace(OLD, NEW, 1).replace('version: "3.4.0"', 'version: "3.4.0-t564b_allow"', 1)
open(DST, "w", encoding="utf-8").write(v); print("wrote", DST)

import yaml
from backend.v9.services import decision_tree as dt3
live = yaml.safe_load(open(SRC, encoding="utf-8")); var = yaml.safe_load(open(DST, encoding="utf-8"))
print("leaves live=%d variant=%d" % (len(dt3.leaves(live["root"])), len(dt3.leaves(var["root"]))))
changed, policy_drift, same, n = [], [], 0, 0
for p in sorted(glob.glob("harness_out/t466/t529b_2026-*.json")):
    j = json.load(open(p))
    for r in j.get("routes") or []:
        tv = r.get("tree_v3")
        if not isinstance(tv, dict) or not isinstance(tv.get("vec"), dict):
            continue
        n += 1; vec = tv["vec"]
        l0, _ = dt3.walk(live["root"], vec); l1, _ = dt3.walk(var["root"], vec)
        a0, a1 = str(l0.get("leaf")).upper(), str(l1.get("leaf")).upper()
        row = (os.path.basename(p)[6:16], r.get("il", "")[:5], vec.get("pattern"), vec.get("phase"), vec.get("day_type"),
               vec.get("hour"), vec.get("rel_bias"), a0, a1)
        if a0 != a1:
            changed.append(row)
        else:
            same += 1
            # the confound check: same decision but a different exit/skip_gates/size policy = a second change
            if any(l0.get(k) != l1.get(k) for k in ("exit", "skip_gates", "size_frac", "stop", "target")):
                policy_drift.append(row + (l0.get("exit"), l1.get("exit")))
print("vectors %d · same %d · changed %d · same-decision-but-policy-drift %d" % (n, same, len(changed), len(policy_drift)))
bad = [c for c in changed if not (c[2] == "INITIATIVE_SHORT" and c[3] == "C" and c[4] in ("Variation", "Normal_Variation")
                                  and c[5] in (18, 19) and c[6] == "against" and c[7] == "SKIP" and c[8] == "TAKE")]
print("changed outside the intended context: %d" % len(bad))
for c in changed[:40]:
    print("   ", c)
for c in policy_drift[:10]:
    print("   DRIFT", c)
print("VERDICT:", "OK - only the against-the-hint allow flips SKIP->TAKE, no policy drift" if not bad and not policy_drift
      else "FAIL - unintended changes, do not run")
