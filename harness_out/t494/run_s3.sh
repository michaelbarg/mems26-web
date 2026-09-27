#!/bin/bash
cd /Users/michael/Downloads/mems26_web_git || exit 1
while pgrep -f "run_splits.sh" >/dev/null || pgrep -f "run_all.sh" >/dev/null; do sleep 20; done
bash harness_out/t466/run_variant.sh "t494s3" "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_s3.yaml" harness_out/t493/sessions.txt > harness_out/t494/run_s3.out 2>&1
echo "S3 DONE $(date)"
