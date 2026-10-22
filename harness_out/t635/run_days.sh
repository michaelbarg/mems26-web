#!/bin/bash
# T-635 (22.10 night, cowork-iMac) — the three per-trade fixes from the six-dimension zoom-in
# (docs/reports/day_reviews/TRADE_ZOOM_DECISIONS_2026-10-22.md), each alone and together, vs the LIVE config of
# 22.10 (ENVF = the iMac .env frozen 22.10 15:22 outside the repo — n2rsNx + SWING_TRAIL_SIDE_GUARD_V1 + T612 +
# LADDER_221 + BE_AFTER_T1_RULE_V1 …), on the faithful harness (T-620; T-623 mono fix via the m-prefix).
# First the per-trade days (22.10 · 21.10 · 20.10 · 19.10) — do #3582/#3515 flip (D1), #3483/#3501/#3508/#3515/#3574
# (D2), #3558/#3660/#3670/#3696 (D3) and do #3544/#3687/#3702 survive — then the 78 recent sessions.
# Outside the harness ban (15:55–23:05 IL weekdays); resumable (existing outputs are skipped).
# Usage: run_days.sh [--recent] tag [tag …]   (one tag at a time, 2 workers)
cd /Users/michael/Downloads/mems26_web_git || exit 1
ENVF=/Users/michael/mems26_snapshots/t635_live_2026-10-22.env
OUT=harness_out/t635/days
mkdir -p "$OUT"
export ENVF OUT
in_ban() {
  local dow hm; dow=$(TZ=Asia/Jerusalem date +%u); hm=$(TZ=Asia/Jerusalem date +%H%M)
  [ "$dow" -le 5 ] && [ "$hm" -ge 1555 ] && [ "$hm" -lt 2305 ]
}
export -f in_ban
if in_ban; then echo "REFUSED: $(TZ=Asia/Jerusalem date +%H:%M) IL is inside the harness ban"; exit 2; fi
RECENT=0
if [ "$1" = "--recent" ]; then RECENT=1; shift; fi
export RECENT
envs_of() {
  case "$1" in
    live)  echo "X_T635=0" ;;                                   # the live .env as is (the reference)
    d1)    echo "BE_BEFORE_T1_V1=1" ;;                          # S6 before T1: BE at max(1R,0.6 ATR), 2-bar step trail from 1.5R
    d1be)  echo "BE_BEFORE_T1_V1=1 BE_BEFORE_T1_TRAIL_R=99" ;;  # BE only (no pre-T1 trail)
    d1t2)  echo "BE_BEFORE_T1_V1=1 BE_BEFORE_T1_TRAIL_R=2.0" ;; # step trail only from 2R
    d1a2)  echo "BE_BEFORE_T1_V1=1 BE_BEFORE_T1_ARM_R=2.0 BE_BEFORE_T1_TRAIL_R=2.5" ;;   # arm only at 2R (T-598: BE at 1R gives winners away)
    d1a2b) echo "BE_BEFORE_T1_V1=1 BE_BEFORE_T1_ARM_R=2.0 BE_BEFORE_T1_TRAIL_R=99" ;;    # BE at 2R only, no trail
    d23a2) echo "BE_BEFORE_T1_V1=1 BE_BEFORE_T1_ARM_R=2.0 BE_BEFORE_T1_TRAIL_R=2.5 MID_VALUE_EDGE_TEST_V1=1 WAIT_FOR_TEST_V1=1" ;;
    d2)    echo "MID_VALUE_EDGE_TEST_V1=1" ;;                   # inside value only as the test of an edge
    d3)    echo "WAIT_FOR_TEST_V1=1" ;;                         # no entry 0–1 bars after an impulse
    d23)   echo "MID_VALUE_EDGE_TEST_V1=1 WAIT_FOR_TEST_V1=1" ;;
    d123)  echo "BE_BEFORE_T1_V1=1 MID_VALUE_EDGE_TEST_V1=1 WAIT_FOR_TEST_V1=1" ;;
    d123b) echo "BE_BEFORE_T1_V1=1 BE_BEFORE_T1_TRAIL_R=99 MID_VALUE_EDGE_TEST_V1=1 WAIT_FOR_TEST_V1=1" ;;
    # T-628 per trade (C4): the two opening/extension flags re-measured on the same base, for the per-trade read
    og)    echo "OPENING_HALF_RANGE_GATE_V1=1" ;;
    fe)    echo "EDGE_FAILED_EXT_LIVE_V1=1" ;;
    m?*)   echo "HARNESS_MONO_FIX_V1=1 $(envs_of "${1#m}")" ;;
  esac
}
export -f envs_of
run_one() {
  tag="$1"; d="$2"; out="$OUT/${tag}_${d}.json"
  [ -s "$out" ] && return 0
  if in_ban; then echo "BAN — not starting $tag $d"; return 0; fi
  env $(envs_of "$tag") SITUATION_VECTOR_LOG_V1=0 nice -n 10 \
    python3 scripts/fwd_harness.py --env "$ENVF" --session "$d" --variant "$tag" --out "$out" --quiet \
    > "$OUT/${tag}_${d}.log" 2>&1
  echo "done $tag $d rc=$? $(TZ=Asia/Jerusalem date +%H:%M:%S)"
}
export -f run_one
sessions() {
  for d in 2026-10-22 2026-10-21 2026-10-20 2026-10-19; do echo "$d"; done
  [ "$RECENT" = "1" ] && return 0
  for d in 2026-10-16 2026-10-15 2026-10-14 2026-10-13 2026-10-12; do echo "$d"; done
  sort -r /Users/michael/mems26_hist/sessions70.txt
}
run_tag() {
  local tag="$1" lst="$OUT/.sessions_$1.txt"
  sessions | awk 'NF==1 && !seen[$1]++' > "$lst"
  echo "=== $tag start $(TZ=Asia/Jerusalem date +%H:%M:%S) — $(envs_of "$tag")"
  for k in 0 1; do
    awk -v k="$k" 'NR % 2 == k' "$lst" | while read -r d; do run_one "$tag" "$d"; done &
  done
  wait
  echo "=== $tag done $(TZ=Asia/Jerusalem date +%H:%M:%S) ($(ls "$OUT"/${tag}_*.json 2>/dev/null | wc -l | tr -d ' ') json)"
}
TAGS=("$@")
for t in "${TAGS[@]}"; do
  run_tag "$t"
done
echo "ALL DONE $(TZ=Asia/Jerusalem date +%H:%M:%S)"
