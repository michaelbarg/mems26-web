#!/bin/bash
# T-579 (fix-agent, night 08→09.10) — BRIEF §2.2 #2: the REACTIVE_SHORT permit ALONE (Variation day, phase C,
# 18:00–19:59 IL, against the hint: SKIP → TAKE; 13 vectors on the night's reference, 0 policy drift —
# harness_out/t579/make_variant_reactive.out). Whole-day replay on the 67 sessions of the night queue
# (harness_out/t564/sessions.txt) against the SAME-NIGHT reference t567ref (live config, tree 3.4.0).
# Runs beside cowork's queue (run_night.sh = 1 variant at a time) ⇒ 2 variants in parallel, the BRIEF's cap.
# usage: nohup bash harness_out/t579/run.sh > harness_out/t579/run.out 2>&1 &
cd /Users/michael/Downloads/mems26_web_git || exit 1
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t564/sessions.txt
echo "=== t579b start $(date '+%H:%M:%S') ==="
bash harness_out/t466/run_variant.sh t579b "$REF DECISION_TREE_V3_PATH=config/decision_tree_v3.t579b_allow.yaml" "$SESS" || { echo "=== t579b STOPPED rc=$? $(date '+%H:%M:%S') ==="; exit 1; }
echo "--- t579b vs t567ref ---"
python3 harness_out/t494/cmp_vs_live.py t579b t567ref
LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8 python3 harness_out/t566/holdout.py t579b t567ref | head -12
echo "=== t579b done $(date '+%H:%M:%S') ==="
