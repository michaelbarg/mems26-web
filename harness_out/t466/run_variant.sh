#!/bin/bash
# Night 24→25.09 — replay one flag variant on the clean sessions (fwd_harness, read-only DB).
# usage: run_variant.sh <TAG> "<ENV assignments>"     e.g.  run_variant.sh sbl "STRUCTURE_BEFORE_LABEL_V1=1"
# Outside RTH only · ≤2 parallel · SITUATION_VECTOR_LOG_V1=0 · outputs harness_out/t466/<TAG>_<session>.{json,log}
cd /Users/michael/Downloads/mems26_web_git || exit 1
TAG="$1"; ENVS="$2"; SESS="${3:-harness_out/t458/sessions.txt}"
export TAG ENVS
# 07.10 (cowork, after the t24 run crossed the open 15:50–16:35 on the trading machine): the harness window
# lives HERE, not in each caller's wrapper — refuse to start, and stop between sessions, inside 16:00–23:05 IL
# on weekdays (BRIEF §5 / CURSOR_README §6). A run that starts at 15:50 ends at 16:00 instead of at the open.
# Override only by an explicit HARNESS_ALLOW_RTH=1 (Michael's ruling, written).
in_rth() {
  local dow hm
  dow=$(TZ=Asia/Jerusalem date +%u); hm=$(TZ=Asia/Jerusalem date +%H%M)
  [ "${HARNESS_ALLOW_RTH:-0}" = "1" ] && return 1
  [ "$dow" -le 5 ] && [ "$hm" -ge 1600 ] && [ "$hm" -lt 2305 ]
}
export -f in_rth
if in_rth; then echo "REFUSED: $(TZ=Asia/Jerusalem date +%H:%M) IL is inside the harness ban 16:00–23:05 (weekdays). HARNESS_ALLOW_RTH=1 overrides."; exit 2; fi
run_one() {
  d="$1"
  out="harness_out/t466/${TAG}_${d}.json"
  [ -s "$out" ] && { echo "skip $d"; return 0; }
  if in_rth; then echo "STOPPED before $d: $(TZ=Asia/Jerusalem date +%H:%M) IL — inside the harness ban"; return 3; fi
  env $ENVS SITUATION_VECTOR_LOG_V1=0 \
    python3 scripts/fwd_harness.py --session "$d" --variant "$TAG" --out "$out" --quiet \
    > "harness_out/t466/${TAG}_${d}.log" 2>&1
  echo "done $d $TAG rc=$?"
}
export -f run_one
cat "$SESS" | xargs -P 2 -I{} bash -c 'run_one "$@"' _ {}
echo "ALL DONE $TAG $(date)"
