#!/bin/bash
# T-598 (fix-agent, night 18→19.10) — BRIEF §2.3 variant 1: stop → BE after +1R (BE_AFTER_MFE_R_V1=1.0), whole-day
# replay on the 71 sessions of cowork's 18.10 queue (harness_out/t586/sessions70.txt = 67 + 07/08/09.10 + 07.08 which
# T-597 un-crashed at 19:52 today) against a SAME-NIGHT reference t598ref = the live config (tree 3.4.0 + .env +
# REF env) on the harness as it is on disk tonight — t567ref (08.10) predates T-591 (replay window, 16:17 today) and
# T-597, and the working tree carries another session's uncommitted edit of five_min_system.py (18 lines), so the
# reference is re-run on exactly the same code as the variant (provenance below). Sequential, 2 workers each, beside
# cowork's hist_* sweep (2 workers) ⇒ 4 harness workers on 8 cores, outside RTH (Sunday → Monday night).
# usage: nohup bash harness_out/t598/run.sh > harness_out/t598/run.out 2>&1 &
cd /Users/michael/Downloads/mems26_web_git || exit 1
export LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t586/sessions70.txt
prov() {
  echo "--- provenance $1 $(date '+%Y-%m-%d %H:%M:%S') HEAD=$(git rev-parse --short HEAD) ---"
  md5 -q scripts/fwd_harness.py backend/v9/systems/five_min/five_min_system.py config/decision_tree_v3.yaml .env \
      backend/v9/services/trade_manager/be_after_mfe.py 2>&1 | paste -sd' ' -
  git status --short backend scripts config | head -20
}
prov start
echo "=== t598ref start $(date '+%H:%M:%S') ==="
bash harness_out/t466/run_variant.sh t598ref "$REF" "$SESS" || { echo "=== t598ref STOPPED rc=$? $(date '+%H:%M:%S') ==="; exit 1; }
echo "=== t598ref done $(date '+%H:%M:%S') ==="
prov mid
echo "=== t598be start $(date '+%H:%M:%S') ==="
bash harness_out/t466/run_variant.sh t598be "$REF BE_AFTER_MFE_R_V1=1.0" "$SESS" || { echo "=== t598be STOPPED rc=$? $(date '+%H:%M:%S') ==="; exit 1; }
echo "=== t598be done $(date '+%H:%M:%S') ==="
prov end
echo "--- t598be vs t598ref ---"
python3 harness_out/t494/cmp_vs_live.py t598be t598ref
python3 harness_out/t566/holdout.py t598be t598ref
echo "--- t598ref vs t567ref (reference drift since 08.10: T-591/T-597/worktree) ---"
python3 harness_out/t494/cmp_vs_live.py t598ref t567ref
echo "=== ALL DONE $(date '+%H:%M:%S') ==="
