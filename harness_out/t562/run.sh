#!/bin/bash
# T-562 (Michael 07.10 17:52) — ONE allow: INITIATIVE_SHORT on a Variation day 18-19h (BRIEF §2.2 #1), vs the SAME-MORNING
# reference. Then, if the window allows, T-561 (second slot for OPEN_DRIVE/C/Trend_Normal/with) vs the same reference.
# Sequential; run_variant.sh refuses/stops inside 16:00–23:05 IL on weekdays. Outputs: harness_out/t466/<tag>_*.json.
cd /Users/michael/Downloads/mems26_web_git || exit 1
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t529/sessions.txt
VAR=/Users/michael/Downloads/mems26_web_git/config/decision_tree_v3.t562_allow.yaml
echo "=== T562/T561 start $(date) ==="
bash harness_out/t466/run_variant.sh t562ref "$REF" "$SESS" || exit $?
bash harness_out/t466/run_variant.sh t562a "$REF DECISION_TREE_V3_PATH=$VAR" "$SESS" || exit $?
echo "--- T562 allow vs ref ---"; python3 harness_out/t494/cmp_vs_live.py t562a t562ref
bash harness_out/t466/run_variant.sh t561s2 "$REF HARNESS_SECOND_SLOT_PATHS=opening_type=OPEN_DRIVE/phase=C/day_type=Trend_Normal/rel_bias=with" "$SESS" || exit $?
echo "--- T561 second slot vs ref ---"; python3 harness_out/t494/cmp_vs_live.py t561s2 t562ref
echo "ALL DONE $(date)"
