#!/bin/bash
# T-515: (1) the reference re-run TODAY on all 61 sessions — history tables drifted since Sunday (25.09 S1 conf 0.75 vs 1.0
# at 18:55), so every comparison uses a same-day reference; (2) TURN_EXIT_V1 on the live tree (harness-only exit rule).
cd /Users/michael/Downloads/mems26_web_git || exit 1
while ! grep -q "QUEUE DONE" harness_out/t515/run_queue.out 2>/dev/null; do sleep 10; done
run() { bash harness_out/t466/run_variant.sh "$1" "$2" harness_out/t515/sessions.txt > "harness_out/t515/run_$1.out" 2>&1; echo "$1 done $(date)"; }
run t515ref "DECISION_TREE_V3=1"
run t515x "DECISION_TREE_V3=1 TURN_EXIT_V1=1"
echo "QUEUE2 DONE $(date)"
