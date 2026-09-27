#!/bin/bash
# T-493 (27.09): replay of the live configuration loaded 25.09 19:15 (tree V3 decides, structure split,
# ELQ leaf policy, V2 branch TAKE) on all clean sessions + the pre-tree baseline for 25.09. ≤2 parallel.
cd /Users/michael/Downloads/mems26_web_git || exit 1
env DECISION_TREE_V3=0 SITUATION_VECTOR_LOG_V1=0 python3 scripts/fwd_harness.py --session 2026-09-25 --variant r15 --out harness_out/t458/r15_2026-09-25.json --quiet > harness_out/t458/r15_2026-09-25.log 2>&1
echo "baseline 25.09 rc=$?"
sort -u harness_out/t458/sessions.txt > harness_out/t493/sessions.txt
bash harness_out/t466/run_variant.sh live0927 "DECISION_TREE_V3=1" harness_out/t493/sessions.txt
echo "LIVE0927 DONE $(date)"
