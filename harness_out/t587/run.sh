#!/bin/bash
# T-588 (fix-agent, the 17→18.10 night run fired late, Sun 18.10 09:55 IL — the Mac was unreachable all week) —
# BRIEF §2.2 #3: the ZLR SHORT permit ALONE (Normal day, phase C, 18:00–19:59 IL, inside value where the
# T-319b location rule skips: SKIP → TAKE; 27 vectors on the reference, 0 outside context, 0 policy drift —
# harness_out/t587/make_variant_zlr.out). Whole-day replay on the 70 sessions of cowork's 18.10 queue
# (harness_out/t586/sessions70.txt = 67 + 07/08/09.10) against the SAME-NIGHT reference t567ref (live config,
# tree 3.4.0; the 3 new sessions were run by cowork at 09:49 today; the only backend change since the 08.10
# reference is backend/v9/api/v9/bars.py = the live ingest path, which fwd_harness.py does not import).
# Runs beside cowork's run_day.sh (1 variant at a time) ⇒ 2 variants in parallel, the BRIEF's cap. Sunday ⇒ no RTH.
# usage: nohup bash harness_out/t587/run.sh > harness_out/t587/run.out 2>&1 &
cd /Users/michael/Downloads/mems26_web_git || exit 1
export LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t586/sessions70.txt
echo "=== t587z start $(date '+%H:%M:%S') ==="
bash harness_out/t466/run_variant.sh t587z "$REF DECISION_TREE_V3_PATH=config/decision_tree_v3.t587_allow.yaml" "$SESS" || { echo "=== t587z STOPPED rc=$? $(date '+%H:%M:%S') ==="; exit 1; }
echo "--- t587z vs t567ref ---"
python3 harness_out/t494/cmp_vs_live.py t587z t567ref
python3 harness_out/t566/holdout.py t587z t567ref
python3 harness_out/t569/equity_1c.py t587z | grep -E 'sessions ·|max closed-day|worst 10|holdout-10|^  2026'
echo "=== t587z done $(date '+%H:%M:%S') ==="
