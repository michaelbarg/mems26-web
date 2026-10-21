# -*- coding: utf-8 -*-
"""T-622d: tree VARIANTS for measurement only (the live config/decision_tree_v3.yaml is untouched).

Michael 11.09: "ביום נורמלי אנחנו צריכים לסחור את ההיפוך ב-VAH ו-VAL עד ל-POC ... לא נכון להיכנס באזור ה-POC".
On the Normal responsive row the location rule already takes SHORT near/above VAH and LONG near/below VAL; T-529
(03.10) lets a failed-extension double through ANYWHERE else (mid_value, the far side of value). T-616 edge (20.10,
Michael "כרגע אני צריך שתבצע", turned off 21.10 04:42 by the night acceptance rule) applied "the flip only at the
edge it failed from" to the T-329 path and left T-529 untouched. 20.10 18:15 #3558-like DOUBLE_TOP_AA_SHORT 7756.75
(34pt under its top 7791.75) goes through T-529 once the day stays Normal (fix 2 single) and loses 215$.

normal_edge : live tree + on the Normal responsive row the failed-extension exemption is gone (location decides).
edge_both   : config/decision_tree_v3.t616_edge.yaml (T-329 at the edge only) + the same Normal-row change.
"""
import yaml

REPO = "/Users/michael/Downloads/mems26_web_git"
OUT = REPO + "/harness_out/t621"
block_old = '''  responsive_normal: &responsive_normal
    split: direction
    branches:
      LONG:
        split: zone
        branches:
          near_val|below_value: *take_location
          unknown: *kinds_normal
          "*": *location_fallback
      SHORT:
        split: zone
        branches:
          near_vah|above_value: *take_location
          unknown: *kinds_normal
          "*": *location_fallback
      "*": *skip_stand_down
'''
block_new = '''  # T-622d VARIANT (measurement only): Normal day — the reversal at VAH/VAL only, never in the POC area or on the far
  # side of value (Michael 11.09); T-529's failed-extension exemption does not apply on the Normal row
  normal_edge_only: &normal_edge_only
    split: edge
    branches:
      failed_extension:
        leaf: SKIP
        id: normal_failed_ext_far
        note: "T-622d: Normal day — a failed-extension double is taken only at the edge (VAH/VAL), not in the POC area (Michael 11.09)"
      "*": *skip_location
  responsive_normal: &responsive_normal
    split: direction
    branches:
      LONG:
        split: zone
        branches:
          near_val|below_value: *take_location
          unknown: *kinds_normal
          "*": *normal_edge_only
      SHORT:
        split: zone
        branches:
          near_vah|above_value: *take_location
          unknown: *kinds_normal
          "*": *normal_edge_only
      "*": *skip_stand_down
'''
for src, dst, ver_old, ver_new in [
        (REPO + "/config/decision_tree_v3.yaml", OUT + "/decision_tree_v3.t622_normal_edge.yaml",
         'version: "3.4.0"', 'version: "3.4.0-t622d-normal-edge"'),
        (REPO + "/config/decision_tree_v3.t616_edge.yaml", OUT + "/decision_tree_v3.t622_edge_both.yaml",
         'version: "3.4.0-t616edge"', 'version: "3.4.0-t616edge-t622d"')]:
    s = open(src, encoding="utf-8").read()
    assert s.count(block_old) == 1, f"responsive_normal block not found exactly once in {src}"
    assert s.count(ver_old) == 1, f"version line not found in {src}"
    s = s.replace(block_old, block_new).replace(ver_old, ver_new, 1)
    yaml.safe_load(s)
    open(dst, "w", encoding="utf-8").write(s)
    print("ok", dst)
