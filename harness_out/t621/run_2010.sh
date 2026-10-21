#!/bin/bash
# T-621 stage 3 (Michael 21.10 plan) — 20.10 replayed with each root fix alone, then together, on the faithful harness
# (T-620). Base = the 20.10 demo .env snapshot. Outside the harness ban only (16:00–23:05 IL weekdays).
# Usage: run_2010.sh [tag ...]   (no tags ⇒ every variant)
cd /Users/michael/Downloads/mems26_web_git || exit 1
ENVF=/Users/michael/mems26_snapshots/20261020T153114Z_base-20.10/.env
OUT=harness_out/t621
D=${D:-2026-10-20}
hm=$(TZ=Asia/Jerusalem date +%H%M); dow=$(TZ=Asia/Jerusalem date +%u)
if [ "$dow" -le 5 ] && [ "$hm" -ge 1600 ] && [ "$hm" -lt 2305 ]; then echo "REFUSED: inside the harness ban"; exit 2; fi
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
    n25s) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=1" ;;
    # T-622b: EDGE_FADE_TARGETS_V1 repaired (the chain is final — no R-clamp; stop beyond the probed extreme)
    eftx) echo "EDGE_FADE_TARGETS_V1=1 EDGE_FADE_STOP_MODE=extreme" ;;
    # T-622c: fix 5 strict / split on top of the strong package (fix 2 single + the Normal-day runner)
    n2rs) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1" ;;
    n2r5p) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=1 TOUCH2_STRUCT_STOP_MODE=probe" ;;
    n2r5t) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=touch2 TOUCH2_STRUCT_STOP_MODE=probe" ;;
    n2r5d) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=dt" ;;
    n25se) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=1 EDGE_FADE_TARGETS_V1=1 EDGE_FADE_STOP_MODE=extreme" ;;
  esac
}
run() {
  tag="$1"; out="$OUT/${tag}_${D}.json"
  env $(envs_of "$tag") SITUATION_VECTOR_LOG_V1=0 nice -n 10 python3 scripts/fwd_harness.py --env "$ENVF" --session "$D" \
    --variant "$tag" --out "$out" --quiet > "$OUT/${tag}_${D}.log" 2>&1
  echo "done $tag rc=$? $(TZ=Asia/Jerusalem date +%H:%M:%S) pnl=$(python3 -c "import json;print(json.load(open('$out'))['daily_pnl_harness'])" 2>/dev/null)"
}
TAGS=("$@"); [ ${#TAGS[@]} -eq 0 ] && TAGS=(base fx1 fx1n fx2 fx3 fx4 fx5 fx24 fx245 fxall fxalln)
for t in "${TAGS[@]}"; do run "$t" & while [ "$(jobs -r | wc -l)" -ge 2 ]; do sleep 2; done; done   # ≤2 parallel (AGENT_BRIEF)
wait
echo "ALL DONE $(TZ=Asia/Jerusalem date +%H:%M:%S)"
