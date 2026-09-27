#!/bin/bash
# T-494/T-496 (27.09 14:55) — second queue, after the first one.
# The first queue's last step "t494t2" sets TOUCH2_V1=1 — a name no code reads (the flag is
# CEILING_FLIP_TOUCH2_V1, five_min_system.py:2022) ⇒ it would replay live0927 unchanged. Its outputs were
# pre-seeded as copies of live0927 so the step skips instantly; they are deleted here, and the two measured
# branches from the 27.09 path audit (gate_audit_live0927.txt) run instead:
#   t494t2e — TOUCH2 routed only at the phase-B open-auction EDGE_FADE leaf, ladder 1.5R/2.5R (T-496 promote)
#   t494s5  — phase-B open-auction: REVERSAL also taken (kind refusals +697$ candidate-level)
cd /Users/michael/Downloads/mems26_web_git || exit 1
while ! grep -q "QUEUE DONE" harness_out/t494/run_queue.out 2>/dev/null; do sleep 15; done
rm -f harness_out/t466/t494t2_*.json harness_out/t466/t494t2_*.log
echo "t494t2 (no-op flag name) copies removed $(date)"
run() { bash harness_out/t466/run_variant.sh "$1" "$2" harness_out/t493/sessions.txt > "harness_out/t494/run_$1.out" 2>&1; echo "$1 done $(date)"; }
run t494t2e "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_t2e.yaml"
run t494s5 "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_s5.yaml"
echo "QUEUE2 DONE $(date)"
