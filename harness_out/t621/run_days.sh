#!/bin/bash
# T-621 stage 3b (Michael 21.10 plan: "how much money in other circumstances") — each root fix on the 78 recent
# live-DB sessions (20.10 · 19.10 · 16–12.10 · sessions70 06-15→10-09), on the FAITHFUL harness (T-620), vs a base
# re-run tonight with the same code. Base .env = the 20.10 demo snapshot. Outside the harness ban (16:00–23:05 IL
# weekdays); resumable (existing outputs are skipped). Usage: run_days.sh tag [tag …]   (one tag at a time, 2 workers)
cd /Users/michael/Downloads/mems26_web_git || exit 1
ENVF=/Users/michael/mems26_snapshots/20261020T153114Z_base-20.10/.env
OUT=harness_out/t621/days
mkdir -p "$OUT"
export ENVF OUT
in_ban() {
  local dow hm; dow=$(TZ=Asia/Jerusalem date +%u); hm=$(TZ=Asia/Jerusalem date +%H%M)
  [ "$dow" -le 5 ] && [ "$hm" -ge 1555 ] && [ "$hm" -lt 2305 ]
}
export -f in_ban
if in_ban; then echo "REFUSED: $(TZ=Asia/Jerusalem date +%H:%M) IL is inside the harness ban"; exit 2; fi
ALL="IB_EXT_ACCEPTED_HINT_V1=1 DAYTYPE_SIDES_ACCEPTED_V1=1 OPENING_DRIVE_STRICT_V1=1 FLIP_RUNNER_ON_OPPOSITE_TAKE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=1"
envs_of() {
  case "$1" in
    base) echo "X_T621=0" ;;
    fx1) echo "IB_EXT_ACCEPTED_HINT_V1=1" ;;
    fx1n) echo "IB_EXT_ACCEPTED_HINT_V1=none" ;;
    fx2) echo "DAYTYPE_SIDES_ACCEPTED_V1=1" ;;
    fx3) echo "OPENING_DRIVE_STRICT_V1=1" ;;
    fx4) echo "FLIP_RUNNER_ON_OPPOSITE_TAKE_V1=1" ;;
    fx5) echo "DOUBLE_TOP_STRUCT_STOP_V1=1" ;;
    fx24) echo "DAYTYPE_SIDES_ACCEPTED_V1=1 FLIP_RUNNER_ON_OPPOSITE_TAKE_V1=1" ;;
    fx245) echo "DAYTYPE_SIDES_ACCEPTED_V1=1 FLIP_RUNNER_ON_OPPOSITE_TAKE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=1" ;;
    fxall) echo "$ALL" ;;
    fxalln) echo "${ALL/IB_EXT_ACCEPTED_HINT_V1=1/IB_EXT_ACCEPTED_HINT_V1=none}" ;;
    # T-622 — the Normal-day package (Michael 21.10: fixes that follow the Normal day)
    ndr) echo "NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1" ;;
    eft) echo "EDGE_FADE_TARGETS_V1=1" ;;
    nday) echo "DAYTYPE_SIDES_ACCEPTED_V1=1 EDGE_FADE_TARGETS_V1=1 NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1" ;;
    nday5) echo "DAYTYPE_SIDES_ACCEPTED_V1=1 EDGE_FADE_TARGETS_V1=1 NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=1" ;;
    nday4) echo "DAYTYPE_SIDES_ACCEPTED_V1=1 EDGE_FADE_TARGETS_V1=1 NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 FLIP_RUNNER_ON_OPPOSITE_TAKE_V1=1" ;;
    # without EDGE_FADE_TARGETS_V1: on 20.10 its POC/VAL/IB ladder was clamped to max-R, sanitized to T1 only and the
    # 5-contract PLACE rejected (T-214) — the T-354 execution path is broken, so the package is measured without it
    n2r) echo "DAYTYPE_SIDES_ACCEPTED_V1=1 NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1" ;;
    n25r) echo "DAYTYPE_SIDES_ACCEPTED_V1=1 NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=1" ;;
    # fix 2 mode "single": acceptance only when ONE side broke (a two-sided day stays Neutral — Michael 10.07)
    fx2s) echo "DAYTYPE_SIDES_ACCEPTED_V1=single" ;;
    n2rs) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1" ;;
    n25s) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=1" ;;
  esac
}
export -f envs_of
export ALL
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
  for d in 2026-10-20 2026-10-19 2026-10-16 2026-10-15 2026-10-14 2026-10-13 2026-10-12; do echo "$d"; done
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
# AGENT_BRIEF: the harness runs ≤2 in parallel — one tag at a time, two workers
for t in "${TAGS[@]}"; do
  run_tag "$t"
done
echo "ALL DONE $(TZ=Asia/Jerusalem date +%H:%M:%S)"
