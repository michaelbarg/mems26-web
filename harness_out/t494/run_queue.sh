#!/bin/bash
# T-494 (27.09) ordered queue, after live0927, one variant at a time (≤2 procs each)
cd /Users/michael/Downloads/mems26_web_git || exit 1
while pgrep -f "run_all.sh" >/dev/null; do sleep 20; done
run() { bash harness_out/t466/run_variant.sh "$1" "$2" harness_out/t493/sessions.txt > "harness_out/t494/run_$1.out" 2>&1; echo "$1 done $(date)"; }
run t494s4 "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_s4.yaml"
run t494s1 "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_s1.yaml"
run t494s3 "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_s3.yaml"
run t494s2 "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_s2.yaml"
run t494t2 "DECISION_TREE_V3=1 TOUCH2_V1=1"
echo "QUEUE DONE $(date)"
