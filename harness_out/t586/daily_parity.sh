#!/bin/bash
# T-586 · the daily demo-parity check (readiness criterion §6.3): replay the session with the frozen RC config and compare
# the demo books with it, trade by trade. Run after 23:05 IL (the harness ban) — by the night agent or by hand.
# usage: daily_parity.sh [YYYY-MM-DD=today] [RC_TAG=rc1]   → harness_out/t466/<RC_TAG>_<d>.json + harness_out/t586/parity_<d>.txt
cd /Users/michael/Downloads/mems26_web_git || exit 1
D="${1:-$(TZ=Asia/Jerusalem date +%F)}"; TAG="${2:-rc1}"
# RC-1 = the live tree + the ruled flags; add the ruled extras here when Michael rules them (e.g. TREE_SKIP_KINDS=REVERSAL,EDGE_FADE)
RC_ENV='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
[ -f harness_out/t586/rc_env.txt ] && RC_ENV="$RC_ENV $(cat harness_out/t586/rc_env.txt)"
export LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8
printf '%s\n' "$D" > /tmp/daily_parity_sessions.txt
bash harness_out/t466/run_variant.sh "$TAG" "$RC_ENV" /tmp/daily_parity_sessions.txt | tail -2
MODE=$(grep -E '^MEMS26_MODE=' .env | cut -d= -f2)
{
  echo "== daily parity $D · mode=$MODE · rc=$TAG · $(date '+%F %T')"
  python3 harness_out/t586/parity.py --mode "$MODE" --from "$D" --to "$D" --ref "$TAG" --detail
} | tee "harness_out/t586/parity_${D}.txt"
