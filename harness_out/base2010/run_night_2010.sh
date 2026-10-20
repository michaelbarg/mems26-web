#!/bin/bash
# Night 20→21.10 — base-20.10 on every session, then the T-616 variants on the recent sessions (the 78 live-DB days:
# 20.10 · 19.10 · 16–12.10 · sessions70 06-15→10-09). One variant at a time vs the same-night base (BRIEF §2).
# Outside the harness ban only (16:00–23:05 IL weekdays) · ≤2 parallel · resumable (existing outputs skipped).
#   base2010   — the 20.10 demo .env snapshot (T-615 mirrors: T-595 closed bars, BE_AFTER_T1_RULE_V1)
#   t616saa    — + STRUCTURAL_ANCHOR_STOP_AUTHORITY_V1=1   (the producer's structural stop stands)
#   t616drv    — + OPENING_DRIVE_STRICT_V1=1                (Dalton: a tested open is a Test-Drive)
#   t616edge   — + DECISION_TREE_V3_PATH=t616_edge          (the failed-extension flip only at the edge)
#   t616nocap  — + OPENING_STOP_CAP_PTS=25                  (no 15pt opening cap; the 25pt max stays)
#   t616all    — saa + drv + edge together
#   t617t2     — + TOUCH2_EDGE_TOL_MAX_ATR=0.5              (T-617: TOUCH2 "at the edge" ≤ ½ATR even on a wide IB)
#   t617all    — t616all + t617t2 (what would be enabled if everything passes)
cd /Users/michael/Downloads/mems26_web_git || exit 1
ENVF=/Users/michael/mems26_snapshots/20261020T153114Z_base-20.10/.env
OUT=harness_out/base2010
export ENVF OUT
in_rth() {
  local dow hm
  dow=$(TZ=Asia/Jerusalem date +%u); hm=$(TZ=Asia/Jerusalem date +%H%M)
  [ "${HARNESS_ALLOW_RTH:-0}" = "1" ] && return 1
  [ "$dow" -le 5 ] && [ "$hm" -ge 1600 ] && [ "$hm" -lt 2305 ]
}
past_cutoff() {   # stop starting new sessions after 05:30 IL (the morning agents / pre-open window)
  local hm; hm=$(TZ=Asia/Jerusalem date +%H%M)
  [ "$hm" -ge 0530 ] && [ "$hm" -lt 1600 ]
}
export -f in_rth past_cutoff
if in_rth; then echo "REFUSED: $(TZ=Asia/Jerusalem date +%H:%M) IL is inside the harness ban 16:00–23:05 (weekdays)."; exit 2; fi
run_one() {
  tag="$1"; envs="$2"; d="$3"; db="$4"
  out="$OUT/hist_${tag}_${d}.json"
  [ -s "$out" ] && { echo "skip $tag $d"; return 0; }
  if past_cutoff; then echo "CUTOFF 05:30 — not starting $tag $d"; return 0; fi
  while in_rth; do echo "WAITING before $tag $d"; sleep 600; done
  if [ "$db" = "hist" ]; then dbu="DATABASE_URL=postgresql://localhost/mems26_hist"; else dbu=""; fi
  env $dbu $envs SITUATION_VECTOR_LOG_V1=0 nice -n 10 \
    python3 scripts/fwd_harness.py --env "$ENVF" --session "$d" --variant "$tag" --out "$out" --quiet \
    > "$OUT/hist_${tag}_${d}.log" 2>&1
  echo "done $tag $d $db rc=$? $(TZ=Asia/Jerusalem date +%H:%M:%S)"
}
export -f run_one
recent() {
  for d in 2026-10-20 2026-10-19 2026-10-16 2026-10-15 2026-10-14 2026-10-13 2026-10-12; do echo "$d live"; done
  sort -r /Users/michael/mems26_hist/sessions70.txt | sed 's/$/ live/'
}
allsess() {
  recent
  sort -r /Users/michael/mems26_hist/hist_sessions.txt | sed 's/$/ hist/'
}
run_tag() {   # run_tag <tag> "<env assignments>" <recent|all> — two workers over an interleaved session list
  local tag="$1" envs="$2" set="$3" lst
  lst="$OUT/.sessions_${tag}.txt"
  echo "=== $tag ($set) start $(TZ=Asia/Jerusalem date +%H:%M:%S) — ${envs:-<base>}"
  { if [ "$set" = "all" ]; then allsess; else recent; fi; } | awk 'NF==2 && !seen[$1]++' > "$lst"
  for k in 0 1; do
    awk -v k="$k" 'NR % 2 == k' "$lst" | while read -r d db; do run_one "$tag" "$envs" "$d" "$db"; done &
  done
  wait
  echo "=== $tag done $(TZ=Asia/Jerusalem date +%H:%M:%S) ($(ls "$OUT"/hist_${tag}_*.json 2>/dev/null | wc -l | tr -d ' ') json)"
}
run_tag base2010 "" all
run_tag t616saa "STRUCTURAL_ANCHOR_STOP_AUTHORITY_V1=1" recent
run_tag t616drv "OPENING_DRIVE_STRICT_V1=1" recent
run_tag t616edge "DECISION_TREE_V3_PATH=config/decision_tree_v3.t616_edge.yaml" recent
run_tag t616nocap "OPENING_STOP_CAP_PTS=25" recent
run_tag t617t2 "TOUCH2_EDGE_TOL_MAX_ATR=0.5" recent
run_tag t616all "STRUCTURAL_ANCHOR_STOP_AUTHORITY_V1=1 OPENING_DRIVE_STRICT_V1=1 DECISION_TREE_V3_PATH=config/decision_tree_v3.t616_edge.yaml" recent
run_tag t617all "STRUCTURAL_ANCHOR_STOP_AUTHORITY_V1=1 OPENING_DRIVE_STRICT_V1=1 DECISION_TREE_V3_PATH=config/decision_tree_v3.t616_edge.yaml TOUCH2_EDGE_TOL_MAX_ATR=0.5" recent
echo "ALL DONE night 20.10 $(date)"
