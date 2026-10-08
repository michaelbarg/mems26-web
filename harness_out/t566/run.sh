#!/bin/bash
# T-566 (Michael 08.10 11:5x "לפחות היית מזיז את הסטופ") — STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1 vs the night's reference
# (t564ref = live config, tree 3.4.0). Outside RTH only; run_variant.sh refuses/stops inside 16:00–23:05.
cd /Users/michael/Downloads/mems26_web_git || exit 1
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t564/sessions.txt
echo "=== T566 start $(date) ==="
bash harness_out/t466/run_variant.sh t566 "$REF STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1=1" "$SESS" || exit $?
echo "--- T566 tighten vs t564ref ---"; python3 harness_out/t494/cmp_vs_live.py t566 t564ref
echo "ALL DONE $(date)"
