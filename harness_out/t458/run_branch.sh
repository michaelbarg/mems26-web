#!/bin/bash
# T-458(ג) — confirmation harness of the opening-drive branch on the 59 clean sessions (15.06–23.09).
# Outside RTH only · ≤2 parallel · SITUATION_VECTOR_LOG_V1=0 · env vars on the command line override .env.
# usage: run_branch.sh <0|1>   (flag value)   → harness_out/t458/branch<flag>_<session>.{json,log}
cd /Users/michael/Downloads/mems26_web_git || exit 1
FLAG="${1:-1}"
run_one() {
  d="$1"; f="$2"
  out="harness_out/t458/branch${f}_${d}.json"
  [ -s "$out" ] && { echo "skip $d (exists)"; return 0; }
  OPENING_DRIVE_BRANCH_V1="$f" SITUATION_VECTOR_LOG_V1=0 \
    python3 scripts/fwd_harness.py --session "$d" --variant "branch${f}" --out "$out" --quiet \
    > "harness_out/t458/branch${f}_${d}.log" 2>&1
  echo "done $d flag=$f rc=$?"
}
export -f run_one
cat "${SESS:-harness_out/t458/sessions.txt}" | xargs -P 2 -I{} bash -c 'run_one "$@"' _ {} "$FLAG"
echo "ALL DONE flag=$FLAG $(date)"
