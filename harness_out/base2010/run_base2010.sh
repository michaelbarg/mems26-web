#!/bin/bash
# base-20.10 («בסיס-20.10») replay — the DAYMAP baseline (Michael 20.10: "tomorrow morning run it on all past days and
# name the version"). ONE .env snapshot = the demo config ruled 19–20.10 (4 S1 input flags, BE_AFTER_T1_RULE_V1,
# DAYTYPE_MACHINE_CLOSED_BARS_V1, DAYTYPE_HISTORY_LIVE_LOCK_V1, LADDER_221_V1 + the live REF tree keys), with the
# T-615 harness mirrors (T-595 closed-bar feed, BE_AFTER_T1_RULE_V1 hold). Read-only DB (the harness forces
# default_transaction_read_only). Outside the harness ban only (16:00–23:05 IL weekdays), ≤2 parallel, resumable.
# Order: newest first, so 20.10 / 19.10 are ready for the 23:30 DAYMAP run.
#   live-DB sessions (mems26): 20.10, 19.10, 16–12.10, sessions70 (06-15 → 10-09)
#   history sessions (mems26_hist): hist_sessions (2025-10-01 → 2026-06-12)
# usage: harness_out/base2010/run_base2010.sh        → harness_out/base2010/hist_base2010_<D>.{json,log}
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
export -f in_rth
if in_rth; then echo "REFUSED: $(TZ=Asia/Jerusalem date +%H:%M) IL is inside the harness ban 16:00–23:05 (weekdays)."; exit 2; fi
run_one() {
  d="$1"; db="$2"
  out="$OUT/hist_base2010_${d}.json"
  [ -s "$out" ] && { echo "skip $d"; return 0; }
  while in_rth; do echo "WAITING before $d: $(TZ=Asia/Jerusalem date +%H:%M) IL — inside the harness ban"; sleep 600; done
  if [ "$db" = "hist" ]; then
    env DATABASE_URL=postgresql://localhost/mems26_hist SITUATION_VECTOR_LOG_V1=0 nice -n 10 \
      python3 scripts/fwd_harness.py --env "$ENVF" --session "$d" --variant base2010 --out "$out" --quiet \
      > "$OUT/hist_base2010_${d}.log" 2>&1
  else
    env SITUATION_VECTOR_LOG_V1=0 nice -n 10 \
      python3 scripts/fwd_harness.py --env "$ENVF" --session "$d" --variant base2010 --out "$out" --quiet \
      > "$OUT/hist_base2010_${d}.log" 2>&1
  fi
  echo "done $d $db rc=$? $(TZ=Asia/Jerusalem date +%H:%M:%S)"
}
export -f run_one
{
  for d in 2026-10-20 2026-10-19 2026-10-16 2026-10-15 2026-10-14 2026-10-13 2026-10-12; do echo "$d live"; done
  sort -r /Users/michael/mems26_hist/sessions70.txt | sed 's/$/ live/'
  sort -r /Users/michael/mems26_hist/hist_sessions.txt | sed 's/$/ hist/'
} | awk 'NF==2 && !seen[$1]++' | xargs -P 2 -L 1 bash -c 'run_one "$0" "$1"'
echo "ALL DONE base2010 $(date)"
