#!/bin/bash
# T-514 (29.09 08:05): is S5 still worth its slot? live0927 (tree 3.0.0) and S5-alone on 28.09, then the package WITHOUT S5 (S1+S7) on all 61.
cd /Users/michael/Downloads/mems26_web_git || exit 1
S=harness_out/t514/sessions.txt
run() { bash harness_out/t466/run_variant.sh "$1" "$2" $S > "harness_out/t514/run_$1.out" 2>&1; echo "$1 done $(date)"; }
run live0927 "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t514/tree_300.yaml"
run t494s5 "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_s5.yaml"
run t514p17 "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t514/tree_p17.yaml"
echo "QUEUE3 DONE $(date)"
