# -*- coding: utf-8 -*-
"""T-624: the tactical path after a FAILED IB extension — tree VARIANTS for measurement only (the live
config/decision_tree_v3.yaml is untouched).

Michael 21.10 on 19.10: "המערכת והעץ היה צריך לזהות בעצם נתיב אחר לפי איך היא מתנהגת ועליה היה לפנות אליו — כמו עסקאות
טקטיות של מערכת 4 או מדרגות שיש להן גם ווליום וגם נר שרואים גודל מאמץ מסוים וגודל תוצאה — אני רוצה לתקן נתיב".
19.10: the up-extension was accepted 18:30 and failed 19:05; every System 4 short 19:05–20:45 (GB100 · TREND_STEP · ZLR)
carried ibr failed_up / with_failed and turn down, and died on tree:bias (the hint stayed LONG).

The path: the extension failed (ib_return failed_up / failed_down) and the candidate goes with the return
(ibr_rel with_failed) ⇒ a System 4 TACTICAL pattern (woodies CONTINUATION: ZLR · TLB · TT · GB100) or a step
(TREND_STEP) whose signal bar(s) show effort and result (feature `effort`, services/effort_result.py, computed only when
TACTICAL_EFFORT_MODE is set) is TAKEN — phase C through the against-hint node, phase D through the stand-down of the
with-extension row. Everything else falls to the old node unchanged.

  decision_tree_v3.t624_tactical.yaml      — as above (ZLR stays shadow by ZLR_SHADOW_V1, Michael 07.09)
  decision_tree_v3.t624_tactical_zlr.yaml  — the same leaf also promotes ZLR in this circumstance only (T-496 promote)
"""
import yaml

REPO = "/Users/michael/Downloads/mems26_web_git"
OUT = REPO + "/harness_out/t621"
SRC = REPO + "/config/decision_tree_v3.yaml"

A_OLD = '''  against_fallback: &against_fallback
    split: edge
    branches:
      failed_extension: *take_failed_ext
      "*": *skip_bias
'''
A_NEW = '''  against_fallback_t329: &against_fallback_t329
    split: edge
    branches:
      failed_extension: *take_failed_ext
      "*": *skip_bias
  # T-624 VARIANT (measurement only; Michael 21.10 "אני רוצה לתקן נתיב"): the IB extension FAILED (the price is back
  # inside the IB) and the candidate goes with the return — a System 4 tactical trade (ZLR · TLB · TT · GB100) or a
  # step (TREND_STEP) whose signal bar(s) show effort and result goes to the tactical path; the stale hint does not
  # refuse it. Everything else falls to the T-329 node exactly as before.
  take_tactical_failed_ext: &take_tactical_failed_ext
    leaf: TAKE
    id: tactical_failed_ext__PROMOTE__
    note: "T-624: the extension failed — a System 4 tactical trade / step with the return, with effort and result"
  tactical_effort: &tactical_effort
    split: effort
    branches:
      strong: *take_tactical_failed_ext
      "*": *against_fallback_t329
  tactical_failed_ext: &tactical_failed_ext
    split: pattern
    branches:
      ZLR|TLB|TT|GB100|TREND_STEP: *tactical_effort
      "*": *against_fallback_t329
  against_fallback: &against_fallback
    split: ibr_rel
    branches:
      with_failed: *tactical_failed_ext
      "*": *against_fallback_t329
'''
D_OLD = '''        note: "phase D, the IB extended one-sidedly — with the extension (the EOD cutoff at 22:15 still applies)"
      "*": *skip_stand_down
'''
D_NEW = '''        note: "phase D, the IB extended one-sidedly — with the extension (the EOD cutoff at 22:15 still applies)"
      "*": *d_tactical
'''
D_DEF_OLD = '''  d_with_extension: &d_with_extension
'''
D_DEF_NEW = '''  # T-624 VARIANT: phase D — after a failed extension, the tactical path instead of the stand-down
  d_tactical: &d_tactical
    split: ibr_rel
    branches:
      with_failed:
        split: pattern
        branches:
          ZLR|TLB|TT|GB100|TREND_STEP:
            split: effort
            branches:
              strong: *take_tactical_failed_ext
              "*": *skip_stand_down
          "*": *skip_stand_down
      "*": *skip_stand_down
  d_with_extension: &d_with_extension
'''
VER_OLD = 'version: "3.4.0"'

# T-624b — the steps filter: EVERY TREND_STEP candidate needs effort and result on its bar(s) (the gateway computes
# the feature for it when TACTICAL_EFFORT_SCOPE=steps); without them the step is refused before the doctrine tree.
ROOT_OLD = '''    "*": *root_full
'''
ROOT_NEW = '''    "*":
      split: pattern
      branches:
        TREND_STEP:
          split: effort
          branches:
            strong: *root_full
            "*":
              leaf: SKIP
              id: step_no_effort
              note: "T-624b: a step (TREND_STEP) without effort and result on its bar(s) (Michael 21.10)"
        "*": *root_full
'''

for name, promote, tactical, steps in (("t624_tactical", "", True, False), ("t624_tactical_zlr", "zlr", True, False),
                                       ("t624_steps", "", False, True), ("t624_tactical_steps", "", True, True)):
    s = open(SRC, encoding="utf-8").read()
    for old, new in (((A_OLD, A_NEW), (D_OLD, D_NEW), (D_DEF_OLD, D_DEF_NEW)) if tactical else ()):
        assert s.count(old) == 1, f"block not found exactly once: {old[:60]!r}"
        s = s.replace(old, new)
    if steps:
        assert s.rstrip("\n").endswith(ROOT_OLD.rstrip("\n")) and s.count(ROOT_OLD) == 1, "root '*' branch not last"
        s = s.replace(ROOT_OLD, ROOT_NEW)
    if promote:
        s = s.replace("    id: tactical_failed_ext__PROMOTE__\n",
                      "    id: tactical_failed_ext\n    promote: [ZLR]   # shadow by ZLR_SHADOW_V1 (Michael 07.09) — routed in THIS circumstance only\n")
    else:
        s = s.replace("    id: tactical_failed_ext__PROMOTE__\n", "    id: tactical_failed_ext\n")
    assert s.count(VER_OLD) == 1
    s = s.replace(VER_OLD, f'version: "3.4.0-{name.replace("_", "-")}"', 1)
    yaml.safe_load(s)
    dst = f"{OUT}/decision_tree_v3.{name}.yaml"
    open(dst, "w", encoding="utf-8").write(s)
    print("ok", dst)
