#!/bin/bash
# T-561 — second live slot for ONE branch (measurement-only, harness): OPEN_DRIVE/C/Trend_Normal/with.
# Reference = the live config of the same run (tree 3.4.0 + .env); variant = same + HARNESS_SECOND_SLOT_PATHS.
# Sequential (not parallel): ref then variant. run_variant.sh refuses/stops inside 16:00–23:05 IL on weekdays.
cd /Users/michael/Downloads/mems26_web_git || exit 1
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t529/sessions.txt
echo "=== T561 start $(date) ===" 
bash harness_out/t466/run_variant.sh t561ref "$REF" "$SESS" || exit $?
bash harness_out/t466/run_variant.sh t561s2 "$REF HARNESS_SECOND_SLOT_PATHS=opening_type=OPEN_DRIVE/phase=C/day_type=Trend_Normal/rel_bias=with" "$SESS" || exit $?
python3 harness_out/t494/cmp_vs_live.py t561s2 t561ref
echo "ALL DONE $(date)"
