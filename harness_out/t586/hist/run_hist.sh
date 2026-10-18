#!/bin/bash
# T-586 · run fwd_harness against the SEPARATE history database (mems26_hist) — read-only there too.
# usage: run_hist.sh <TAG> "<extra ENV>" <sessions.txt>   → harness_out/t466/<TAG>_<d>.json (same layout as run_variant.sh)
# Outside RTH (16:00–23:05 IL weekdays) only; ≤2 parallel.
cd /Users/michael/Downloads/mems26_web_git || exit 1
TAG="$1"; ENVS="$2"; SESS="$3"
REF='DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM'
export TAG ENVS REF
in_rth() { local dow hm; dow=$(TZ=Asia/Jerusalem date +%u); hm=$(TZ=Asia/Jerusalem date +%H%M); [ "${HARNESS_ALLOW_RTH:-0}" = "1" ] && return 1; [ "$dow" -le 5 ] && [ "$hm" -ge 1600 ] && [ "$hm" -lt 2305 ]; }
export -f in_rth
if in_rth; then echo "REFUSED: inside the harness ban 16:00–23:05 IL"; exit 2; fi
run_one() {
  d="$1"; out="harness_out/t466/${TAG}_${d}.json"
  [ -s "$out" ] && { echo "skip $d"; return 0; }
  if in_rth; then echo "STOPPED before $d"; return 3; fi
  env $REF $ENVS DATABASE_URL=postgresql://localhost/mems26_hist SITUATION_VECTOR_LOG_V1=0 \
    python3 scripts/fwd_harness.py --session "$d" --variant "$TAG" --out "$out" --quiet > "harness_out/t466/${TAG}_${d}.log" 2>&1
  echo "done $d $TAG rc=$?"
}
export -f run_one
cat "$SESS" | xargs -P 2 -I{} bash -c 'run_one "$@"' _ {}
echo "ALL DONE $TAG $(date)"
