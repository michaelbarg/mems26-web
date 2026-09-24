#!/bin/bash
# sensitivity: branch ON with a different drive target R (OPENING_DRIVE_T1_R) on the 29 drive sessions; ≤2 parallel
cd /Users/michael/Downloads/mems26_web_git || exit 1
R="${1:-1.5}"; TAG="r${R/./}"
run_one() {
  d="$1"; R="$2"; TAG="$3"
  out="harness_out/t458/${TAG}_${d}.json"
  [ -s "$out" ] && { echo "skip $d"; return 0; }
  OPENING_DRIVE_BRANCH_V1=1 OPENING_DRIVE_T1_R="$R" SITUATION_VECTOR_LOG_V1=0 \
    python3 scripts/fwd_harness.py --session "$d" --variant "$TAG" --out "$out" --quiet > "harness_out/t458/${TAG}_${d}.log" 2>&1
  echo "done $d $TAG rc=$?"
}
export -f run_one
cat harness_out/t458/sessions_drive.txt | xargs -P 2 -I{} bash -c 'run_one "$@"' _ {} "$R" "$TAG"
echo "ALL DONE $TAG $(date)"
