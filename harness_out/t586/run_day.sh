#!/bin/bash
# 18.10 (cowork, Michael 18.10 "תעבור על המערכת… סימולציה מלאה"): whole-day variants vs the reference t567ref on the
# 70 sessions (67 + 07/08/09.10). run_variant.sh refuses inside 16:00–23:05 IL on weekdays (Sunday today). ≤2 parallel.
# usage: nohup bash harness_out/t586/run_day.sh > harness_out/t586/day.out 2>&1 &
cd /Users/michael/Downloads/mems26_web_git || exit 1
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t586/sessions70.txt
export LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8
run() {  # run <TAG> "<extra ENV>"
  echo "=== $1 start $(date '+%H:%M:%S') ==="
  bash harness_out/t466/run_variant.sh "$1" "$REF $2" "$SESS" || { echo "=== $1 STOPPED rc=$? $(date '+%H:%M:%S') ==="; return 1; }
  echo "--- $1 vs t567ref ---"; python3 harness_out/t494/cmp_vs_live.py "$1" t567ref
  python3 harness_out/t566/holdout.py "$1" t567ref | grep -E '^(sessions|months|mechanism)'
  python3 harness_out/t569/equity_1c.py "$1" | grep -E 'sessions ·|max closed-day|worst 10|holdout-10|^  2026'
  echo "=== $1 done $(date '+%H:%M:%S') ==="
}
run t567ref ""                                                       # reference (skips existing outputs)
run t586k   "TREE_SKIP_KINDS=REVERSAL,EDGE_FADE"                      # 1. kind policy: no reversal / edge-fade entries
run t586s2  "HARNESS_SECOND_SLOT_PATHS=*"                            # 2. universal second slot (2 trades at once)
run t586ks2 "TREE_SKIP_KINDS=REVERSAL,EDGE_FADE HARNESS_SECOND_SLOT_PATHS=*"   # 3. both
echo "ALL DONE $(date)"
