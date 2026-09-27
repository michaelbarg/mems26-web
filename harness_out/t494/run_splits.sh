#!/bin/bash
# T-494 (27.09): two doctrinal splits on top of the live tree, day-total on all sessions, run AFTER live0927 (≤2 procs)
cd /Users/michael/Downloads/mems26_web_git || exit 1
while pgrep -f "run_all.sh" >/dev/null; do sleep 20; done
for v in s1 s2; do
  bash harness_out/t466/run_variant.sh "t494$v" "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_$v.yaml" harness_out/t493/sessions.txt > "harness_out/t494/run_$v.out" 2>&1
  echo "split $v done $(date)"
done
bash harness_out/t466/run_variant.sh "t494t2" "DECISION_TREE_V3=1 TOUCH2_V1=1" harness_out/t493/sessions.txt > harness_out/t494/run_t2.out 2>&1
echo "ALL SPLITS DONE $(date)"
