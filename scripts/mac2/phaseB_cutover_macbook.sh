#!/usr/bin/env bash
# ============================================================================
# MEMS26 — Mac-2 (iMac) TAKEOVER · Phase B-1: CUTOVER, MacBook side   (run ON the MacBook)
#
# Tonight ≥ 23:05 IL (after the 23:00 close). Order of operations (Michael ruling 21.10):
#   1. preflight  — flat, no working orders, git clean+pushed, iMac reachable, iMac Sierra closed
#   2. snapshot   — scripts/mems26_snapshot.sh (rollback point for .env/DLL/LaunchAgents)
#   3. stop       — Michael closes Sierra on the MacBook (releases the single Teton login),
#                   then ALL 11 com.mems26.* LaunchAgents are booted out and retired
#   4. dump       — fresh FULL pg_dump (nothing writes any more → exact)
#   5. ship       — final rsync of the repo (+harness_out) and of the migration dir to the iMac
#   6. handoff    — prints the iMac command (phaseB_imac_golive.sh)
# After this script the MacBook is a DEV machine only. Rollback = mems26_restore.sh + re-bootstrap the
# retired plists (kept in ~/Library/LaunchAgents/_retired_mems26_<date>/).
#
# Usage:  bash scripts/mac2/phaseB_cutover_macbook.sh [all|preflight|snapshot|stop|dump|ship|handoff]
#   env:  FORCE=1 (skip the ≥23:00 clock check)  SKIP_SIERRA_WAIT=1 (don't wait for Sierra to close)
# ============================================================================
set -u -o pipefail   # pipefail: a check piped through tee must not inherit tee's exit 0
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
MIG="${MIG:-$HOME/mems26_migration_2026-10-21}"
REPO="$HOME/Downloads/mems26_web_git"
PG=/Applications/Postgres.app/Contents/Versions/18/bin
IMAC="${IMAC:-192.168.1.14}"
SSH="ssh -o BatchMode=yes -o ConnectTimeout=8 michael@$IMAC"
LA="$HOME/Library/LaunchAgents"
U=$(id -u)
DAY=$(date +%Y-%m-%d)
mkdir -p "$MIG/logs" "$MIG/db"
LOG="$MIG/logs/phaseB_macbook_$(date +%Y%m%dT%H%M%S).log"
STEP="${1:-all}"

say(){ printf '\n\033[1;35m[B1/%s]\033[0m %s\n' "$1" "$2" | tee -a "$LOG"; }
ok(){  printf '  \033[1;32m✓\033[0m %s\n' "$*" | tee -a "$LOG"; }
warn(){ printf '  \033[1;33m!\033[0m %s\n' "$*" | tee -a "$LOG"; }
bad(){ printf '  \033[1;31m✗\033[0m %s\n' "$*" | tee -a "$LOG"; }
die(){ bad "$*"; echo "log: $LOG"; exit 1; }
run(){ echo "  \$ $*" | tee -a "$LOG"; "$@" 2>&1 | tee -a "$LOG"; return "${PIPESTATUS[0]}"; }
case "$(hostname)" in *MacBarg*|*macbarg*|*MacBook*) ;; *) die "this script runs ON the MacBook (MacBarg) only (hostname=$(hostname))";; esac
sierra_running(){ pgrep -f "SierraChart_64|Y_SierraChart" >/dev/null 2>&1; }

# ---------------------------------------------------------------- preflight
step_preflight(){
  say preflight "clock · flat · git · iMac"
  local hm; hm=$(date +%k%M | tr -d ' ')   # %k = hour without leading zero → plain decimal
  # ≥ 23:35: the 23:00 close has passed AND the 23:20 EOD-journal scheduled task (git pull/commit/push on this repo) has finished
  if [ "${FORCE:-0}" != 1 ] && [ "$hm" -lt 2335 ] && [ "$hm" -gt 600 ]; then die "it is $(date +%H:%M) IL — the cutover starts at 23:35 (after the close and after the 23:20 EOD-journal task); FORCE=1 only on Michael's word"; fi
  ok "clock $(date '+%F %H:%M %Z')"
  local st="$HOME/SierraChart_Data/v9_export/sierra_state.json"
  if [ -f "$st" ]; then
    python3 - "$st" <<'EOF' 2>&1 | tee -a "$LOG"
import json,sys,time,os
p=sys.argv[1]; d=json.load(open(p)); age=time.time()-os.path.getmtime(p)
q=d.get('position_qty'); wo=d.get('working_orders', d.get('orders'))
n_wo = len(wo) if isinstance(wo,list) else wo
print(f"  sierra_state: position_qty={q} working_orders={n_wo} is_sim={d.get('is_sim')} age={age:.0f}s")
sys.exit(0 if (q in (0,None)) else 3)
EOF
    [ "${PIPESTATUS[0]}" = 0 ] && ok "flat per sierra_state.json" || die "NOT FLAT — position open; do not cut over with an open position"
  else warn "no sierra_state.json (Sierra already closed?) — confirm flat with Michael"; fi
  local act; act=$(curl -s -m 5 http://127.0.0.1:8000/api/v9/trades/active 2>/dev/null | head -c 200)
  case "$act" in ""|null|"{}"|"[]") ok "backend /trades/active = ${act:-<no answer>} (no live trade)";; *) die "backend reports an active trade: $act";; esac
  ( cd "$REPO" && local d; d=$(git status --porcelain | grep -vE "harness_out|^.. docs/|^\?\? outputs/|^\?\? \"Claude outputs" | wc -l | tr -d ' ')
    [ "$d" = 0 ] && ok "git: no uncommitted code" || { warn "git: $d uncommitted code/config files:"; git status --porcelain | grep -vE "harness_out|^.. docs/" | head -8 | tee -a "$LOG"; [ "${ACK_DIRTY:-0}" = 1 ] || die "commit+push them first (or ACK_DIRTY=1 to ship the dirty tree as-is via rsync)"; }
    local up; up=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "?"); [ "$up" = 0 ] && ok "git: everything pushed" || die "git: $up unpushed commits — git push first" )
  $SSH 'echo ok' >/dev/null 2>&1 && ok "iMac reachable at $IMAC" || die "iMac not reachable over SSH ($IMAC)"
  if $SSH 'pgrep -f "SierraChart_64|Y_SierraChart" >/dev/null'; then die "Sierra is ALREADY running on the iMac — it must open only after the MacBook's Sierra is closed (single Teton login)"; else ok "iMac Sierra closed (correct)"; fi
  $SSH "test -f $MIG/db/.restored_mems26_full" && ok "iMac Phase A restore marker present" || warn "iMac Phase A marker missing — Phase A not completed there (golive will still do a full restore)"
}

# ---------------------------------------------------------------- snapshot
step_snapshot(){ say snapshot "out-of-git surfaces → ~/mems26_snapshots"; ( cd "$REPO" && run bash scripts/mems26_snapshot.sh "cutover-to-imac-$DAY" | tail -3 ); }

# ---------------------------------------------------------------- stop
step_stop(){
  say stop "1) Michael: on the MacBook's Sierra → File ▸ Disconnect, then QUIT Sierra (frees the Teton login for the iMac)"
  if sierra_running && [ "${SKIP_SIERRA_WAIT:-0}" != 1 ]; then
    echo "  waiting up to 15 min for Sierra to quit on the MacBook… (SKIP_SIERRA_WAIT=1 to skip)"
    for i in $(seq 1 90); do sierra_running || break; sleep 10; done
    sierra_running && die "Sierra still running on the MacBook — quit it, then re-run: $0 stop"
  fi
  ok "Sierra not running on the MacBook"
  say stop "2) boot out + retire ALL com.mems26.* LaunchAgents on the MacBook"
  local RET="$LA/_retired_mems26_$DAY"; mkdir -p "$RET"
  for p in "$LA"/com.mems26.*.plist; do [ -f "$p" ] || continue; local L; L=$(basename "$p" .plist)
    launchctl bootout "gui/$U/$L" >/dev/null 2>&1 && echo "    bootout $L" | tee -a "$LOG" || echo "    (not loaded) $L" | tee -a "$LOG"
    mv "$p" "$RET/"
  done
  sleep 2
  for pat in "uvicorn backend.main" "json_bridge" "v9_export_promoter" "mobile_relay.py" "trade_activity_feed" "next dev" "npm run dev" "gap_backfill.py"; do pkill -f "$pat" 2>/dev/null; done
  sleep 1
  local left; left=$(launchctl list | grep -c com.mems26 || true)
  [ "$left" = 0 ] && ok "no mems26 agents loaded; plists retired to $RET ($(ls "$RET" | wc -l | tr -d ' '))" || die "$left mems26 agents still loaded"
  lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1 && die "something still listens on :8000" || ok "ports 8000/3000 free"
}

# ---------------------------------------------------------------- dump
step_dump(){
  say dump "fresh FULL pg_dump (nothing writes now → exact) → $MIG/db/mems26_cutover"
  pgrep -f "uvicorn backend.main" >/dev/null && die "backend still running — run step stop first"
  rm -rf "$MIG/db/mems26_cutover"
  local t0; t0=$(date +%s)
  "$PG/pg_dump" -Fd -j 3 -Z 3 -f "$MIG/db/mems26_cutover" mems26 > "$MIG/logs/pg_dump_cutover.log" 2>&1 || die "pg_dump failed — $MIG/logs/pg_dump_cutover.log"
  ok "dump done in $(( $(date +%s)-t0 ))s · $(du -sh "$MIG/db/mems26_cutover" | cut -f1) · $(ls "$MIG/db/mems26_cutover" | wc -l | tr -d ' ') files"
  ( cd "$MIG/db" && find mems26_cutover -type f -exec shasum -a 256 {} \; > ../SHA256SUMS_cutover.txt )
  "$PG/psql" -d mems26 -At -c "select tablename from pg_tables where schemaname='public' order by 1" | while read -r t; do printf '%s|%s\n' "$t" "$("$PG/psql" -d mems26 -At -c "select count(*) from \"$t\"")"; done > "$MIG/db/ROWCOUNTS_cutover.txt"
  ok "exact row counts for $(wc -l < "$MIG/db/ROWCOUNTS_cutover.txt" | tr -d ' ') tables → ROWCOUNTS_cutover.txt (the iMac verifies against this)"
}

# ---------------------------------------------------------------- ship
step_ship(){
  say ship "final rsync: repo (incl. harness_out, excl. node_modules/.next/__pycache__) → iMac"
  rsync -a --delete --stats --exclude 'node_modules/' --exclude '.next/' --exclude '__pycache__/' --exclude '*.pyc' --exclude 'Claude outputs/' --exclude 'frontend/v9/test-results/' -e "ssh -o BatchMode=yes" "$REPO/" "michael@$IMAC:$REPO/" > "$MIG/logs/rsync_repo_cutover.log" 2>&1 || die "repo rsync failed — $MIG/logs/rsync_repo_cutover.log"
  ok "repo: $(grep -E 'Number of files transferred' "$MIG/logs/rsync_repo_cutover.log")"
  say ship "out-of-repo data the scripts read → iMac (delta over the Phase-A pass): ~/mems26_hist · ~/mems26_snapshots · ~/SierraChart_Data/v9_archive"
  for d in mems26_hist mems26_snapshots SierraChart_Data/v9_archive; do
    rsync -a --stats -e "ssh -o BatchMode=yes" "$HOME/$d/" "michael@$IMAC:$HOME/$d/" > "$MIG/logs/rsync_cutover_$(basename "$d").log" 2>&1 && ok "$d: $(grep -E 'Number of files transferred' "$MIG/logs/rsync_cutover_$(basename "$d").log")" || warn "$d rsync failed — see log (non-blocking)"
  done
  say ship "migration dir (cutover dump + checksums) → iMac"
  rsync -a --stats -e "ssh -o BatchMode=yes" "$MIG/" "michael@$IMAC:$MIG/" > "$MIG/logs/rsync_mig_cutover.log" 2>&1 || die "mig rsync failed"
  ok "mig: $(grep -E 'Number of files transferred' "$MIG/logs/rsync_mig_cutover.log")"
  $SSH "cd $MIG/db && shasum -a 256 -c ../SHA256SUMS_cutover.txt --quiet && echo CHECKSUMS_OK" | grep -q CHECKSUMS_OK && ok "iMac verified the cutover dump checksums" || die "checksum mismatch on the iMac"
  $SSH "cd $REPO && git log -1 --format='iMac repo HEAD %h %ci'" | tee -a "$LOG"
}

# ---------------------------------------------------------------- handoff
step_handoff(){
  say handoff "MacBook side DONE — the MacBook is now DEV-only (no agents, Sierra closed)."
  echo "  NOW on the iMac (Claude-on-iMac or Michael; or from here: ssh michael@$IMAC '…'):"
  echo "     bash $REPO/scripts/mac2/phaseB_imac_golive.sh all"
  echo "  then Michael on the iMac screen: open Sierra (Y_SierraChart) → Remote Build → reload study → verify → ARM."
  echo "  Rollback (if the iMac fails tonight): on the MacBook   for p in $LA/_retired_mems26_$DAY/*.plist; do launchctl bootstrap gui/$U \"\$p\"; done   + open Sierra here."
  echo "  log: $LOG"
}

case "$STEP" in
  all) step_preflight && step_snapshot && step_stop && step_dump && step_ship && step_handoff ;;
  preflight|snapshot|stop|dump|ship|handoff) "step_$STEP" ;;
  *) echo "usage: $0 [all|preflight|snapshot|stop|dump|ship|handoff]"; exit 2 ;;
esac
