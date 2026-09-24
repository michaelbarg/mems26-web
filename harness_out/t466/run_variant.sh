#!/bin/bash
# Night 24→25.09 — replay one flag variant on the clean sessions (fwd_harness, read-only DB).
# usage: run_variant.sh <TAG> "<ENV assignments>"     e.g.  run_variant.sh sbl "STRUCTURE_BEFORE_LABEL_V1=1"
# Outside RTH only · ≤2 parallel · SITUATION_VECTOR_LOG_V1=0 · outputs harness_out/t466/<TAG>_<session>.{json,log}
cd /Users/michael/Downloads/mems26_web_git || exit 1
TAG="$1"; ENVS="$2"; SESS="${3:-harness_out/t458/sessions.txt}"
export TAG ENVS
run_one() {
  d="$1"
  out="harness_out/t466/${TAG}_${d}.json"
  [ -s "$out" ] && { echo "skip $d"; return 0; }
  env $ENVS SITUATION_VECTOR_LOG_V1=0 \
    python3 scripts/fwd_harness.py --session "$d" --variant "$TAG" --out "$out" --quiet \
    > "harness_out/t466/${TAG}_${d}.log" 2>&1
  echo "done $d $TAG rc=$?"
}
export -f run_one
cat "$SESS" | xargs -P 2 -I{} bash -c 'run_one "$@"' _ {}
echo "ALL DONE $TAG $(date)"
