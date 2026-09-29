#!/bin/bash
# T-515: the full real-time package — turn asked first (against/mid veto, with ⇒ TAKE + TOUCH2/ZLR) AND the open trade
# exits when the turn flips against it (TURN_EXIT_V1, harness), so the slot is free for the new direction (28.09 16:55).
cd /Users/michael/Downloads/mems26_web_git || exit 1
while ! grep -q "QUEUE2 DONE" harness_out/t515/run_queue2.out 2>/dev/null; do sleep 10; done
bash harness_out/t466/run_variant.sh t515amwx "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t515/tree_amw.yaml TURN_EXIT_V1=1" harness_out/t515/sessions.txt > harness_out/t515/run_t515amwx.out 2>&1
echo "t515amwx done $(date)"; echo "QUEUE3 DONE $(date)"
