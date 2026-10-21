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
# T-622d tree VARIANTS (measurement only — config/decision_tree_v3.yaml untouched): built by
# /Users/michael/mems26_t622_tree_variant.py; T616_EDGE = the T-616 edge tree Michael ruled ON 20.10 night
T622_NEDGE=/Users/michael/Downloads/mems26_web_git/harness_out/t621/decision_tree_v3.t622_normal_edge.yaml
T622_BOTH=/Users/michael/Downloads/mems26_web_git/harness_out/t621/decision_tree_v3.t622_edge_both.yaml
T616_EDGE=/Users/michael/Downloads/mems26_web_git/config/decision_tree_v3.t616_edge.yaml
T624_TAC=/Users/michael/Downloads/mems26_web_git/harness_out/t621/decision_tree_v3.t624_tactical.yaml
T624_TACZ=/Users/michael/Downloads/mems26_web_git/harness_out/t621/decision_tree_v3.t624_tactical_zlr.yaml
T624_STEPS=/Users/michael/Downloads/mems26_web_git/harness_out/t621/decision_tree_v3.t624_steps.yaml
T624_TSTEPS=/Users/michael/Downloads/mems26_web_git/harness_out/t621/decision_tree_v3.t624_tactical_steps.yaml
export T622_NEDGE T622_BOTH T616_EDGE T624_TAC T624_TACZ T624_STEPS T624_TSTEPS
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
    # T-622b: EDGE_FADE_TARGETS_V1 repaired (the chain is final — no R-clamp; stop beyond the probed extreme)
    eftx) echo "EDGE_FADE_TARGETS_V1=1 EDGE_FADE_STOP_MODE=extreme" ;;
    # T-622c: fix 5 strict / split on top of the strong package (fix 2 single + the Normal-day runner)
    n2r5p) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=1 TOUCH2_STRUCT_STOP_MODE=probe" ;;
    n2r5t) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=touch2 TOUCH2_STRUCT_STOP_MODE=probe" ;;
    n2r5d) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=dt" ;;
    n25se) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DOUBLE_TOP_STRUCT_STOP_V1=1 EDGE_FADE_TARGETS_V1=1 EDGE_FADE_STOP_MODE=extreme" ;;
    # T-622d: the Normal-day edge rule (Michael 11.09 "לא נכון להיכנס באזור ה-POC") — on the Normal responsive row
    # T-529's failed-extension exemption is gone (20.10 18:15 DT −215$ at mid_value); T-616 edge = the same principle
    # on the T-329 path (Michael ruled it ON 20.10 night); "both" = the two together
    nedge) echo "DECISION_TREE_V3_PATH=$T622_NEDGE" ;;
    n2rsn) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DECISION_TREE_V3_PATH=$T622_NEDGE" ;;
    edge) echo "DECISION_TREE_V3_PATH=$T616_EDGE" ;;
    n2rse) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DECISION_TREE_V3_PATH=$T616_EDGE" ;;
    n2rsb) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 DECISION_TREE_V3_PATH=$T622_BOTH" ;;
    # the five keys Michael ruled ON 20.10 night (T-616/T-617/T-618; off since 21.10 04:42 by the night acceptance
    # rule — mine, not his) re-measured on the faithful harness (T-620): each alone + the whole night set
    saa) echo "STRUCTURAL_ANCHOR_STOP_AUTHORITY_V1=1" ;;
    t2tol) echo "TOUCH2_EDGE_TOL_MAX_ATR=0.5" ;;
    t1fr) echo "T1_FRONT_RUN_TICKS=2" ;;
    night) echo "OPENING_DRIVE_STRICT_V1=1 STRUCTURAL_ANCHOR_STOP_AUTHORITY_V1=1 DECISION_TREE_V3_PATH=$T616_EDGE TOUCH2_EDGE_TOL_MAX_ATR=0.5 T1_FRONT_RUN_TICKS=2" ;;
    # fix 1 on top of the Normal-day package — 19.10: the up-extension was accepted 18:30 and failed 19:05 (back in the
    # IB), and ~30 shorts 19:05–20:45 were refused by tree:bias (the hint stayed LONG); 20.10's R1 is the same root
    n2rs1) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 IB_EXT_ACCEPTED_HINT_V1=1" ;;
    # the night set (+1,960$ vs base, last10 +981) on top of the Normal-day package (+3,043$, last10 +16) — and
    # without its edge tree (n2rs + the T-616 edge tree alone was −1,259$ vs n2rs)
    n2rsN) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 $(envs_of night)" ;;
    n2rsNx) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 OPENING_DRIVE_STRICT_V1=1 STRUCTURAL_ANCHOR_STOP_AUTHORITY_V1=1 TOUCH2_EDGE_TOL_MAX_ATR=0.5 T1_FRONT_RUN_TICKS=2" ;;
    n2rs1n) echo "DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 IB_EXT_ACCEPTED_HINT_V1=none" ;;
    # T-624 the tactical path after a FAILED IB extension (Michael 21.10 "אני רוצה לתקן נתיב") — always with the H15
    # TREND_STEP mirror (the "steps"; the live main.py subscriber the harness never ran); run them as m-tags, vs mts
    ts) echo "HARNESS_TREND_STEP_V1=1" ;;
    tsb) echo "HARNESS_TREND_STEP_V1=1 TACTICAL_EFFORT_MODE=bar DECISION_TREE_V3_PATH=$T624_TAC" ;;
    tss) echo "HARNESS_TREND_STEP_V1=1 TACTICAL_EFFORT_MODE=step DECISION_TREE_V3_PATH=$T624_TAC" ;;
    tsn) echo "HARNESS_TREND_STEP_V1=1 TACTICAL_EFFORT_MODE=none DECISION_TREE_V3_PATH=$T624_TAC" ;;
    tsbz) echo "HARNESS_TREND_STEP_V1=1 TACTICAL_EFFORT_MODE=bar DECISION_TREE_V3_PATH=$T624_TACZ" ;;
    tssz) echo "HARNESS_TREND_STEP_V1=1 TACTICAL_EFFORT_MODE=step DECISION_TREE_V3_PATH=$T624_TACZ" ;;
    # T-624b the steps filter — EVERY TREND_STEP needs effort and result (mts vs mbase: the steps as live since 19.10
    # are −1,227$ on 78 sessions, 10 trades −720$ direct)
    tsfs) echo "HARNESS_TREND_STEP_V1=1 TACTICAL_EFFORT_MODE=step TACTICAL_EFFORT_SCOPE=steps DECISION_TREE_V3_PATH=$T624_STEPS" ;;
    tsfb) echo "HARNESS_TREND_STEP_V1=1 TACTICAL_EFFORT_MODE=bar TACTICAL_EFFORT_SCOPE=steps DECISION_TREE_V3_PATH=$T624_STEPS" ;;
    tstfs) echo "HARNESS_TREND_STEP_V1=1 TACTICAL_EFFORT_MODE=step TACTICAL_EFFORT_SCOPE=steps DECISION_TREE_V3_PATH=$T624_TSTEPS" ;;
    n2rsts) echo "HARNESS_TREND_STEP_V1=1 DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1" ;;
    n2rstss) echo "HARNESS_TREND_STEP_V1=1 DAYTYPE_SIDES_ACCEPTED_V1=single NORMAL_DAY_RUNNER_OTHER_SIDE_V1=1 TACTICAL_EFFORT_MODE=step DECISION_TREE_V3_PATH=$T624_TAC" ;;
    # T-623: "m" + any tag = the same envs on the harness with the monotonic-clock fix (confluence join on the fake
    # clock, ATR caches cleared per bar) — compare m-tags only with m-tags (mbase is their base)
    m?*) echo "HARNESS_MONO_FIX_V1=1 $(envs_of "${1#m}")" ;;
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
