#!/bin/bash
# T-588 step 2 (fix-agent 18.10 10:3x): t587z (the permit alone) was Δ 0.00 on all 70 sessions — 27 tree decisions
# flipped SKIP→TAKE but ZLR_SHADOW_V1=1 (Michael 07.09 "מתקנים ולא מבטלים") routes every ZLR setup to shadow, and
# the live reference holds zero live ZLR trades ⇒ the permit is inert by construction. To give the §2.2 #3 question a
# number anyway, the pair that isolates it:
#   t587s  = live config + ZLR_SHADOW_V1=0                       (ZLR un-shadowed, tree 3.4.0 as is)
#   t587sz = live config + ZLR_SHADOW_V1=0 + the permit tree     (permit on top)
# permit alone = t587sz − t587s · the shadow ruling itself = t587s − t567ref. Sequential (cowork's queue runs beside
# this one ⇒ 2 variants in parallel, the BRIEF's cap). Sunday ⇒ no RTH. Measurement only — nothing live changes.
# usage: nohup bash harness_out/t587/run2.sh > harness_out/t587/run2.out 2>&1 &
cd /Users/michael/Downloads/mems26_web_git || exit 1
export LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
SESS=harness_out/t586/sessions70.txt
run() {  # run <TAG> "<extra ENV>" <REFTAG>
  echo "=== $1 start $(date '+%H:%M:%S') ==="
  bash harness_out/t466/run_variant.sh "$1" "$REF $2" "$SESS" || { echo "=== $1 STOPPED rc=$? $(date '+%H:%M:%S') ==="; return 1; }
  echo "--- $1 vs $3 ---"; python3 harness_out/t494/cmp_vs_live.py "$1" "$3"
  python3 harness_out/t566/holdout.py "$1" "$3" | grep -E '^(sessions|months|mechanism)'
  python3 harness_out/t569/equity_1c.py "$1" | grep -E 'sessions ·|max closed-day|worst 10|holdout-10|^  2026'
  echo "=== $1 done $(date '+%H:%M:%S') ==="
}
run t587s  "ZLR_SHADOW_V1=0" t567ref
run t587sz "ZLR_SHADOW_V1=0 DECISION_TREE_V3_PATH=config/decision_tree_v3.t587_allow.yaml" t587s
echo "--- t587sz vs t567ref ---"; python3 harness_out/t494/cmp_vs_live.py t587sz t567ref
python3 harness_out/t566/holdout.py t587sz t567ref | grep -E '^(sessions|months)'
echo "ALL DONE $(date)"
