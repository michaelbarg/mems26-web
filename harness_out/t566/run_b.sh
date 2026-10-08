#!/bin/bash
# T-566b — the tighten with 0.5 × ATR of room beyond the return bar (STRUCTURE_EXIT_TIGHTEN_ROOM_ATR=0.5) vs t564ref.
cd /Users/michael/Downloads/mems26_web_git || exit 1
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t564/sessions.txt
echo "=== T566b start $(date) ==="
bash harness_out/t466/run_variant.sh t566b "$REF STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1=1 STRUCTURE_EXIT_TIGHTEN_ROOM_ATR=0.5" "$SESS" || exit $?
echo "--- T566b room 0.5 ATR vs t564ref ---"; python3 harness_out/t494/cmp_vs_live.py t566b t564ref
echo "ALL DONE $(date)"
