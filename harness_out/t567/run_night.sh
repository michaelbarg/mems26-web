#!/bin/bash
# Night 08→09.10 (cowork, Michael 08.10 "תמשיך ליישום") — the queue, one variant at a time vs the same-night
# reference, 67 sessions (harness_out/t564/sessions.txt), live config = tree 3.4.0. run_variant.sh refuses/stops
# inside 16:00–23:05 IL. Each variant: whole-day replay → cmp_vs_live (Δ gross/net, better/worse, trades
# added/removed) → holdout-10 + months (harness_out/t566/holdout.py). ≤2 parallel ⇒ sequential here (the
# reference first; nothing compares against a stale reference).
# usage: nohup bash harness_out/t567/run_night.sh > harness_out/t567/night.out 2>&1 &
cd /Users/michael/Downloads/mems26_web_git || exit 1
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t564/sessions.txt
run() {  # run <TAG> "<extra ENV>"
  echo "=== $1 start $(date '+%H:%M:%S') ==="
  bash harness_out/t466/run_variant.sh "$1" "$REF $2" "$SESS" || { echo "=== $1 STOPPED rc=$? $(date '+%H:%M:%S') ==="; return 1; }
  if [ "$1" != "t567ref" ]; then
    echo "--- $1 vs t567ref ---"; python3 harness_out/t494/cmp_vs_live.py "$1" t567ref
    LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8 python3 harness_out/t566/holdout.py "$1" t567ref | head -12
  fi
  echo "=== $1 done $(date '+%H:%M:%S') ==="
}
run t567ref ""                                                                   || exit 1
run t567a   "DECISION_TREE_V3_PATH=config/decision_tree_v3.t567a.yaml"           # 1. counter-hint SHORT, Variation C
run t567c9  "SLOT_RELEASE_BARS_V1=9"                                             # 2. slot release after 9 bars w/o 1R
run t571b   "DECISION_TREE_V3_PATH=config/decision_tree_v3.t571b.yaml"           # 3. auction_B_reversal → SKIP
run t571a   "DECISION_TREE_V3_PATH=config/decision_tree_v3.t571a.yaml"           # 3b. only ext-reject LONG → SKIP
run t566c   "STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1=accept"                            # 4. tighten after acceptance
run t567b   "ELQ_PHASE_B_EXEMPT_V1=1"                                            # 5. ELQ exempt in phase B
run t567c6  "SLOT_RELEASE_BARS_V1=6"                                             # 2b. slot release after 6 bars
echo "--- doctrine cells on the night's reference ---"
LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8 python3 scripts/doctrine_cell_audit.py --tag t567ref > harness_out/t567/doctrine_cells_t567ref.md 2>&1 && echo "cells → harness_out/t567/doctrine_cells_t567ref.md"
echo "ALL DONE $(date '+%H:%M:%S')"
