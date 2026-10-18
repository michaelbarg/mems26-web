# -*- coding: utf-8 -*-
"""T-588 (fix-agent 18.10, the 23:40 run fired late at 09:55 — the Mac was unreachable all week): BRIEF §2.2 #3 —
the ZLR SHORT permit ALONE on a Normal day 18:00-19:59 IL (same recipe as T-564b / T-579b).
Where the live tree 3.4.0 routes it today (harness_out/t587/zlr_vectors.out, 70-session reference t567ref):
28 vectors, 27 of them SKIP(location) through responsive_normal -> SHORT -> zone near_val|mid_value ->
location_fallback (edge none), one TAKE(take_with_extension) on structure=down. The calibration source
(scripts/context_table.py, train <=19.09): (Normal, 18-19, ZLR, SHORT) n=24 · +16.5$/cand (candidate level).
Here ONLY that SKIP(location) becomes a plain TAKE (default exit) for pattern=ZLR at hour 18|19; near_vah /
above_value (take_location), unknown (kinds_normal), failed_extension (take_failed_ext_t529), other hours and
other patterns keep the live row verbatim. The live file is never touched.
Verification on every t567ref vector: decisions change ONLY in the intended context SKIP->TAKE, and the
leaf's exit/skip_gates/size policy never changes where the decision did not."""
import glob, json, os, sys
ROOT = "/Users/michael/Downloads/mems26_web_git"; os.chdir(ROOT); sys.path.insert(0, ROOT)
SRC = "config/decision_tree_v3.yaml"; DST = "config/decision_tree_v3.t587_allow.yaml"
t = open(SRC, encoding="utf-8").read()
OLD = ('      SHORT:\n        split: zone\n        branches:\n'
       '          near_vah|above_value: *take_location\n'
       '          unknown: *kinds_normal\n'
       '          "*": *location_fallback\n'
       '      "*": *skip_stand_down\n'
       '  responsive_neutral: &responsive_neutral\n')
NEW = ('      SHORT:\n        split: zone\n        branches:\n'
       '          near_vah|above_value: *take_location\n'
       '          unknown: *kinds_normal\n'
       '          "*":\n'
       '            split: pattern\n            branches:\n'
       '              ZLR:               # T-588 (fix-agent 18.10): the permit ALONE - ZLR SHORT on a Normal day 18:00-19:59 IL where the location rule skips; measurement variant, not live\n'
       '                split: hour\n                branches:\n'
       '                  "18|19":\n'
       '                    split: edge\n                    branches:\n'
       '                      failed_extension: *take_failed_ext_t529\n'
       '                      "*":\n'
       '                        leaf: TAKE\n'
       '                        id: allow_zlr_short_normal_1819\n'
       '                        note: "T-588 allow: ZLR SHORT on a Normal day 18:00-19:59 IL inside value (T-319b location skip lifted), default exit; calibration train +16.5$/cand n=24"\n'
       '                  "*": *location_fallback\n'
       '              "*": *location_fallback\n'
       '      "*": *skip_stand_down\n'
       '  responsive_neutral: &responsive_neutral\n')
assert t.count(OLD) == 1, "responsive_normal SHORT block not found verbatim - the live file changed; stop"
v = t.replace(OLD, NEW, 1).replace('version: "3.4.0"', 'version: "3.4.0-t587_allow"', 1)
open(DST, "w", encoding="utf-8").write(v); print("wrote", DST)

import yaml
from backend.v9.services import decision_tree as dt3
live = yaml.safe_load(open(SRC, encoding="utf-8")); var = yaml.safe_load(open(DST, encoding="utf-8"))
print("leaves live=%d variant=%d" % (len(dt3.leaves(live["root"])), len(dt3.leaves(var["root"]))))
changed, policy_drift, same, n = [], [], 0, 0
for p in sorted(glob.glob("harness_out/t466/t567ref_2026-*.json")):
    j = json.load(open(p))
    for r in j.get("routes") or []:
        tv = r.get("tree_v3")
        if not isinstance(tv, dict) or not isinstance(tv.get("vec"), dict):
            continue
        n += 1; vec = tv["vec"]
        l0, _ = dt3.walk(live["root"], vec); l1, _ = dt3.walk(var["root"], vec)
        a0, a1 = str(l0.get("leaf")).upper(), str(l1.get("leaf")).upper()
        row = (os.path.basename(p).split("_",1)[1][:10], r.get("il", "")[:5], vec.get("pattern"), vec.get("direction"), vec.get("phase"),
               vec.get("day_type"), vec.get("hour"), vec.get("zone"), vec.get("edge"), a0, a1, l0.get("id"), l1.get("id"))
        if a0 != a1:
            changed.append(row)
        else:
            same += 1
            if any(l0.get(k) != l1.get(k) for k in ("exit", "skip_gates", "size_frac", "stop", "target")):
                policy_drift.append(row + (l0.get("exit"), l1.get("exit")))
print("vectors %d · same %d · changed %d · same-decision-but-policy-drift %d" % (n, same, len(changed), len(policy_drift)))
bad = [c for c in changed if not (c[2] == "ZLR" and c[3] == "SHORT" and c[4] == "C" and c[5] == "Normal" and c[6] in (18, 19)
                                  and c[7] not in ("near_vah", "above_value", "unknown") and c[8] != "failed_extension"
                                  and c[9] == "SKIP" and c[10] == "TAKE" and c[11] == "location" and c[12] == "allow_zlr_short_normal_1819")]
print("changed outside the intended context: %d" % len(bad))
for c in changed[:40]:
    print("   ", c)
for c in policy_drift[:10]:
    print("   DRIFT", c)
print("VERDICT:", "OK - only the ZLR SHORT Normal 18-19h location-skip flips SKIP->TAKE, no policy drift" if not bad and not policy_drift
      else "FAIL - unintended changes, do not run")
