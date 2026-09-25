#!/bin/bash
# T-480 first doctrinal splits — three tree variants, day-total replay on the 58 clean sessions, sequential (≤2 procs)
cd /Users/michael/Downloads/mems26_web_git || exit 1
for v in v1 v2 v3b; do
  bash harness_out/t466/run_variant.sh "t3$v" "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t480/tree_$v.yaml" > "harness_out/t480/run_$v.out" 2>&1
  echo "variant $v finished $(date)"
done
echo "SPLITS DONE $(date)"
