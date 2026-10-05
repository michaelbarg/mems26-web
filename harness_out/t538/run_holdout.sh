#!/bin/bash
# T-538 — no new entries from 20:00 IL (tree root wrapper on `hour`). Holdout = the 10 newest sessions (never used to pick the rule).
# Reference = t529b (today's live config, same harness). Read-only DB, <=2 parallel.
cd /Users/michael/Downloads/mems26_web_git || exit 1
S=harness_out/t538/sessions_holdout.txt
LIVE="DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM"
echo "START $(date)" > harness_out/t538/run_holdout.out
bash harness_out/t466/run_variant.sh t538h "$LIVE DECISION_TREE_V3_PATH=/Users/michael/Downloads/mems26_web_git/config/decision_tree_v3.t538.yaml" "$S" > harness_out/t538/run_t538h.out 2>&1
echo "t538h done $(date)" >> harness_out/t538/run_holdout.out
PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py t538h t529b >> harness_out/t538/run_holdout.out 2>&1
echo "ALL DONE $(date)" >> harness_out/t538/run_holdout.out
