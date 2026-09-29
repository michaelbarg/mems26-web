#!/bin/bash
# T-514 (29.09 07:45, before the open): the two fixes proposed after 28.09's two live losses, measured day-total
# vs the live configuration (tree 3.1.0 == harness_out/t494/tree_pkg.yaml, 0 differences on 2,621 vectors).
#   ref  t494pkg  — extended with 28.09 (only the missing sessions run)
#   A    t514tbr  — auction_B_trend_break only WITH the directional hint (28.09 17:25 VEGAS LONG had rel_bias=none)
#   B    t514xs   — ELQ_EXPENSIVE_STOP_V1=1: the expensive-stop arm blocks (28.09 16:50 #2483 rr 2.37)
cd /Users/michael/Downloads/mems26_web_git || exit 1
S=harness_out/t514/sessions.txt
run() { bash harness_out/t466/run_variant.sh "$1" "$2" $S > "harness_out/t514/run_$1.out" 2>&1; echo "$1 done $(date)"; }
run t494pkg "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_pkg.yaml"
run t514tbr "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t514/tree_tbr.yaml"
run t514xs  "DECISION_TREE_V3=1 ELQ_EXPENSIVE_STOP_V1=1"
echo "QUEUE DONE $(date)"
