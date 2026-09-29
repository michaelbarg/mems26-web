#!/bin/bash
# T-515 (29.09): run_queue.sh was stopped after amw (amwe carried the range-mid veto, measured −204.90$ net) — this closes
# queue 1 once amw finishes, so queue 2 (the same-day reference t515ref + t515x) starts.
cd /Users/michael/Downloads/mems26_web_git || exit 1
while ! grep -q "ALL DONE t515amw" harness_out/t515/run_t515amw.out 2>/dev/null; do sleep 10; done
echo "t515amw done $(date)" >> harness_out/t515/run_queue.out
echo "QUEUE DONE $(date) (amwe dropped)" >> harness_out/t515/run_queue.out
