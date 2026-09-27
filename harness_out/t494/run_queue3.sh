#!/bin/bash
# T-498 (27.09 15:00) — third queue, after queue2. The entry-confirm gate (S4_ENTRY_CONFIRM_V1) reads
# "ORDER BY ts DESC LIMIT 15" from v9_bars_5min_woodies. Live routes land 2–6 s after the bar boundary and the new
# bar's row is created 0.8–11 s after it — so live sometimes tests the FORMING bar (open≈close ⇒ passes as noise;
# #2408 25.09 19:25:06) and sometimes the closed signal bar (19:45:02 block). The harness always tests the closed
# bar (AS-OF guard) — replay is strict where live is often lenient. This run measures the gate itself: OFF vs ON.
cd /Users/michael/Downloads/mems26_web_git || exit 1
while ! grep -q "QUEUE2 DONE" harness_out/t494/run_queue2.out 2>/dev/null; do sleep 15; done
run() { bash harness_out/t466/run_variant.sh "$1" "$2" harness_out/t493/sessions.txt > "harness_out/t494/run_$1.out" 2>&1; echo "$1 done $(date)"; }
run t498ec0 "DECISION_TREE_V3=1 S4_ENTRY_CONFIRM_V1=0"
echo "QUEUE3 DONE $(date)"
