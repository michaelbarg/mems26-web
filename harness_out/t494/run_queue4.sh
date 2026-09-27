#!/bin/bash
# T-500/T-494 (27.09 15:05) — fourth queue, after queue3: the two remaining "tree said TAKE, a gate after it
# refused winners" paths from the 27.09 audit (gate_audit_live0927.txt):
#   t494s6 — auction_B_trend_break skips extreme_chase_guard (10 refused, 8 reached 1.5R, +498$ cand.)
#   t494s7 — exit ladder 1.5R/2.5R on take_failed_ext + the BREAK kinds leaves (RR refused +510$ / +450$ cand.)
cd /Users/michael/Downloads/mems26_web_git || exit 1
while ! grep -q "QUEUE3 DONE" harness_out/t494/run_queue3.out 2>/dev/null; do sleep 15; done
run() { bash harness_out/t466/run_variant.sh "$1" "$2" harness_out/t493/sessions.txt > "harness_out/t494/run_$1.out" 2>&1; echo "$1 done $(date)"; }
run t494s6 "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_s6.yaml"
run t494s7 "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_s7.yaml"
echo "QUEUE4 DONE $(date)"
