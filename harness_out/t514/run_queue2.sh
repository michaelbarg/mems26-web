#!/bin/bash
# T-514 B1 (29.09 07:47): the 28.09 breakdown short (17:30 ZLR SHORT, tree TAKE with the hint, routed shadow by
# ZLR_SHADOW_V1) — would ZLR routed live on the with-hint leaf pay over 61 sessions? (T-496 promote policy)
cd /Users/michael/Downloads/mems26_web_git || exit 1
while ! grep -q "QUEUE DONE" harness_out/t514/run_queue.out 2>/dev/null; do sleep 10; done
bash harness_out/t466/run_variant.sh t514zlr "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t514/tree_zlr.yaml" harness_out/t514/sessions.txt > harness_out/t514/run_t514zlr.out 2>&1
echo "t514zlr done $(date)"; echo "QUEUE2 DONE $(date)"
