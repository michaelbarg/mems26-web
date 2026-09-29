#!/bin/bash
# T-515 (29.09 ~09:00, before the open): the real-time turn state (double top/bottom at the session extreme) asked
# FIRST in the tree — four variants vs the live tree (ref t494pkg, 61 sessions incl. 28.09). ≤2 parallel.
cd /Users/michael/Downloads/mems26_web_git || exit 1
run() { bash harness_out/t466/run_variant.sh "$1" "$2" "$3" > "harness_out/t515/run_$1.out" 2>&1; echo "$1 done $(date)"; }
run t515ref "DECISION_TREE_V3=1" harness_out/t515/ref_sessions.txt
for v in a am amw amwe; do run t515$v "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t515/tree_$v.yaml" harness_out/t515/sessions.txt; done
echo "QUEUE DONE $(date)"
