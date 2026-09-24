#!/bin/bash
# T-458א — replay of the VAR_CONT producer on the clean sessions (fwd_harness, read-only DB).
# Outside RTH only · ≤2 parallel · SITUATION_VECTOR_LOG_V1=0.   usage: run_varcont.sh [sessions_file]
cd /Users/michael/Downloads/mems26_web_git || exit 1
SESS="${1:-harness_out/t458/sessions.txt}"
run_one() {
  d="$1"
  out="harness_out/t458a/${TAG:-varcont}_${d}.json"
  [ -s "$out" ] && { echo "skip $d"; return 0; }
  VAR_CONT_V1=1 SITUATION_VECTOR_LOG_V1=0 \
    python3 scripts/fwd_harness.py --session "$d" --variant "${TAG:-varcont}" --out "$out" --quiet \
    > "harness_out/t458a/${TAG:-varcont}_${d}.log" 2>&1
  echo "done $d rc=$?"
}
export TAG; export -f run_one
cat "$SESS" | xargs -P 2 -I{} bash -c 'run_one "$@"' _ {}
echo "ALL DONE $(date)"
