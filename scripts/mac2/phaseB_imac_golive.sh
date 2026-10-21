#!/usr/bin/env bash
# ============================================================================
# MEMS26 — Mac-2 (iMac) TAKEOVER · Phase B-2: GO-LIVE on the iMac   (run ON the iMac, tonight)
#
# Runs AFTER phaseB_cutover_macbook.sh finished on the MacBook (its services are down and the
# cutover dump + final repo rsync have landed here). Steps:
#   1. preflight — cutover dump present + checksums, repo HEAD, MacBook really down (:8000 refused), Sierra closed here
#   2. snapshot  — scripts/mems26_snapshot.sh on the iMac (pre-go-live state)
#   3. db        — full restore into mems26_new → exact row-count check vs ROWCOUNTS_cutover.txt → atomic
#                  rename swap (mems26 → mems26_phaseA_<date>, mems26_new → mems26) → drop the Aug copy (approved)
#   4. env       — .env = MacBook's; LIVE_TRADING_ARMED forced to 0 (Michael arms, never Claude)
#   5. services  — bootstrap ALL 11 LaunchAgents (now including mobile_relay = the phone writer)
#   6. verify    — health · status · flag_guard · relay healthz · mems26_verify
#   7. sierra    — PRINTS the manual Sierra checklist for Michael (Remote Build, reload study, Inputs, feed fresh)
#   8. arm       — PRINTS the arming command (Michael only)
#
# Usage: bash scripts/mac2/phaseB_imac_golive.sh [all|preflight|snapshot|db|env|services|verify|sierra|arm]
# ============================================================================
set -u -o pipefail   # pipefail: a check piped through tee must not inherit tee's exit 0
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
MIG="${MIG:-$HOME/mems26_migration_2026-10-21}"
REPO="$HOME/Downloads/mems26_web_git"
PG=/Applications/Postgres.app/Contents/Versions/18/bin
PY=/Library/Frameworks/Python.framework/Versions/3.9/bin/python3
LA="$HOME/Library/LaunchAgents"
MACBOOK="${MACBOOK:-192.168.1.127}"
U=$(id -u)
DAY=$(date +%Y-%m-%d)
mkdir -p "$MIG/logs"
LOG="$MIG/logs/phaseB_imac_$(date +%Y%m%dT%H%M%S).log"
STEP="${1:-all}"
AGENTS="backend bridge export_promoter activity_feed mobile_relay frontend eod_handoff gap_backfill startup_check update_check agents_bootstrap"

say(){ printf '\n\033[1;35m[B2/%s]\033[0m %s\n' "$1" "$2" | tee -a "$LOG"; }
ok(){  printf '  \033[1;32m✓\033[0m %s\n' "$*" | tee -a "$LOG"; }
warn(){ printf '  \033[1;33m!\033[0m %s\n' "$*" | tee -a "$LOG"; }
bad(){ printf '  \033[1;31m✗\033[0m %s\n' "$*" | tee -a "$LOG"; }
die(){ bad "$*"; echo "log: $LOG"; exit 1; }
run(){ echo "  \$ $*" | tee -a "$LOG"; "$@" 2>&1 | tee -a "$LOG"; return "${PIPESTATUS[0]}"; }
case "$(hostname)" in *iMac*|*imac*) ;; *) die "this script runs ON the iMac only (hostname=$(hostname))";; esac
sierra_running(){ pgrep -f "SierraChart_64|Y_SierraChart" >/dev/null 2>&1; }

# ---------------------------------------------------------------- preflight
step_preflight(){
  say preflight "cutover dump · repo · MacBook down · Sierra closed"
  [ -d "$MIG/db/mems26_cutover" ] || die "cutover dump missing ($MIG/db/mems26_cutover) — run phaseB_cutover_macbook.sh ship on the MacBook"
  (cd "$MIG/db" && shasum -a 256 -c ../SHA256SUMS_cutover.txt --quiet >>"$LOG" 2>&1) && ok "cutover dump checksums OK ($(du -sh "$MIG/db/mems26_cutover" | cut -f1))" || die "cutover dump checksum mismatch"
  [ -f "$MIG/db/ROWCOUNTS_cutover.txt" ] && ok "row-count reference: $(wc -l < "$MIG/db/ROWCOUNTS_cutover.txt" | tr -d ' ') tables" || die "ROWCOUNTS_cutover.txt missing"
  ok "repo HEAD $(cd "$REPO" && git log -1 --format='%h %ci') · dirty(non-harness)=$(cd "$REPO" && git status --porcelain | grep -v harness_out | wc -l | tr -d ' ')"
  if curl -s -m 3 "http://$MACBOOK:8000/api/v9/health" >/dev/null 2>&1; then die "the MacBook backend still answers on $MACBOOK:8000 — finish phaseB_cutover_macbook.sh stop first (never two live machines)"; else ok "MacBook :8000 not answering (down, as required)"; fi
  sierra_running && die "Sierra already running on the iMac — close it; it is opened only in step 'sierra' after services are up" || ok "Sierra closed on the iMac"
  pgrep -f "bin/postgres -D" >/dev/null && ok "Postgres running" || die "Postgres.app not running"
  [ -x /usr/local/bin/npm ] && ok "node $(/usr/local/bin/node --version)" || warn "no /usr/local/bin/npm — the frontend agent will fail until node 24 is installed (Phase A step node)"
}

step_snapshot(){ say snapshot "iMac pre-go-live snapshot"; ( cd "$REPO" && run bash scripts/mems26_snapshot.sh "imac-pre-golive-$DAY" | tail -2 ) || warn "snapshot script returned non-zero (continuing)"; }

# ---------------------------------------------------------------- db
step_db(){
  say db "restore cutover dump → mems26_new (nothing else may use the DB now)"
  for a in $AGENTS; do launchctl bootout "gui/$U/com.mems26.$a" >/dev/null 2>&1 && echo "    bootout $a (Phase A verification instance)" | tee -a "$LOG"; done
  pkill -f "uvicorn backend.main" 2>/dev/null; sleep 2
  run "$PG/psql" -d postgres -q -c "select pg_terminate_backend(pid) from pg_stat_activity where datname in ('mems26','mems26_new') and pid<>pg_backend_pid()" >/dev/null
  run "$PG/psql" -d postgres -q -c "DROP DATABASE IF EXISTS mems26_new" && run "$PG/psql" -d postgres -q -c "CREATE DATABASE mems26_new" || die "could not create mems26_new"
  local t0; t0=$(date +%s)
  "$PG/pg_restore" -j 4 --no-owner -d mems26_new "$MIG/db/mems26_cutover" > "$MIG/logs/pg_restore_cutover.log" 2>&1
  local rc=$? errs; errs=$(grep -c "ERROR" "$MIG/logs/pg_restore_cutover.log")
  echo "  pg_restore rc=$rc errors=$errs time=$(( $(date +%s)-t0 ))s" | tee -a "$LOG"
  [ "$errs" = 0 ] || { grep ERROR "$MIG/logs/pg_restore_cutover.log" | head -5 | tee -a "$LOG"; die "restore had errors — do NOT swap; inspect $MIG/logs/pg_restore_cutover.log"; }
  run "$PG/psql" -d mems26_new -q -c "ANALYZE" >/dev/null
  say db "exact row-count verification vs the MacBook's cutover counts"
  local mism=0 n=0
  while IFS='|' read -r t ref; do
    [ -n "$t" ] || continue; n=$((n+1))
    local got; got=$("$PG/psql" -d mems26_new -At -c "select count(*) from \"$t\"" 2>/dev/null)
    [ "$got" = "$ref" ] || { mism=$((mism+1)); bad "$t: iMac=$got MacBook=$ref"; }
  done < "$MIG/db/ROWCOUNTS_cutover.txt"
  [ "$mism" = 0 ] && ok "all $n tables match the MacBook exactly" || die "$mism tables differ — do NOT swap"
  say db "atomic swap: mems26 → mems26_phaseA_$DAY · mems26_new → mems26"
  run "$PG/psql" -d postgres -q -c "select pg_terminate_backend(pid) from pg_stat_activity where datname in ('mems26','mems26_new') and pid<>pg_backend_pid()" >/dev/null
  "$PG/psql" -d postgres -At -c "select 1 from pg_database where datname='mems26'" | grep -q 1 && run "$PG/psql" -d postgres -q -c "ALTER DATABASE mems26 RENAME TO mems26_phaseA_${DAY//-/}"
  run "$PG/psql" -d postgres -q -c "ALTER DATABASE mems26_new RENAME TO mems26" || die "rename swap failed"
  ok "mems26 is now the cutover copy · previous Phase-A copy kept as mems26_phaseA_${DAY//-/} (drop after a clean first day)"
  if "$PG/psql" -d postgres -At -c "select 1 from pg_database where datname='mems26_imac_old_aug2026'" | grep -q 1; then run "$PG/psql" -d postgres -q -c "DROP DATABASE mems26_imac_old_aug2026" && ok "dropped the stale Aug-2026 iMac DB (approved by Michael 21.10)"; fi
  "$PG/psql" -d postgres -At -c "select datname||' '||pg_size_pretty(pg_database_size(datname)) from pg_database where datname like 'mems26%'" | sed 's/^/    /' | tee -a "$LOG"
}

# ---------------------------------------------------------------- env
step_env(){
  say env ".env is the MacBook's (shipped by rsync) — force LIVE_TRADING_ARMED=0; Michael arms in step arm"
  sed -i '' 's/^LIVE_TRADING_ARMED=.*/LIVE_TRADING_ARMED=0/' "$REPO/.env"
  for k in LIVE_TRADING_ARMED MACHINE_TAG RENDER_MOBILE_URL MEMS26_MODE V9_EXPORT_DIR SIERRA_LIVE_ACCOUNT; do echo "    $(grep "^$k=" "$REPO/.env")" | tee -a "$LOG"; done
  mkdir -p "$HOME/SierraChart_Data/v9_export" "$HOME/SierraChart_Data/v9_archive"
  for p in "$MIG"/launchagents/com.mems26.*.plist; do cp "$p" "$LA/"; done; ok "11 plists in place"
}

# ---------------------------------------------------------------- services
step_services(){
  say services "bootstrap ALL agents on the iMac (this is the moment the iMac becomes THE machine)"
  grep -q '^LIVE_TRADING_ARMED=0' "$REPO/.env" || die "refusing: .env not disarmed"
  for a in $AGENTS; do
    local p="$LA/com.mems26.$a.plist"; [ -f "$p" ] || { warn "missing plist $a"; continue; }
    if launchctl print "gui/$U/com.mems26.$a" >/dev/null 2>&1; then launchctl kickstart -k "gui/$U/com.mems26.$a" && echo "    kickstart $a" | tee -a "$LOG"; else launchctl bootstrap "gui/$U" "$p" && echo "    bootstrap $a" | tee -a "$LOG" || bad "bootstrap failed: $a"; fi
  done
  sleep 30
  launchctl list | grep com.mems26 | awk '{printf "    %-8s %-4s %s\n",$1,$2,$3}' | tee -a "$LOG"
  ok "loaded: $(launchctl list | grep -c com.mems26)/11"
}

# ---------------------------------------------------------------- verify
step_verify(){
  say verify "backend · relay · flag_guard · mems26_verify"
  curl -s -m 5 http://127.0.0.1:8000/api/v9/health | tee -a "$LOG"; echo
  curl -s -m 5 http://127.0.0.1:8000/api/v9/status | "$PY" -c "import sys,json; d=json.load(sys.stdin); print('  status.mode =', d.get('mode'))" 2>&1 | tee -a "$LOG"
  ( cd "$REPO" && run "$PY" scripts/flag_guard.py | tail -2 )
  local R; R=$(grep '^RENDER_MOBILE_URL=' "$REPO/.env" | cut -d= -f2)
  echo "  relay → $R/healthz : $(curl -s -m 8 "$R/healthz" | head -c 160)" | tee -a "$LOG"
  echo "  relay log tail:"; tail -3 /tmp/mobile_relay.log 2>/dev/null | sed 's/^/    /' | tee -a "$LOG"
  ( cd "$REPO" && bash scripts/mems26_verify.sh 2>&1 | tail -20 | tee -a "$LOG" ) || true
  echo "  (DLL/feed lines turn green only after step sierra)"
}

# ---------------------------------------------------------------- sierra (manual)
step_sierra(){
  say sierra "MICHAEL on the iMac screen (Claude-on-iMac can drive the clicks) — do in this order:"
  cat <<EOF | tee -a "$LOG"
  1. Make sure the MacBook's Sierra is CLOSED (phaseB_cutover_macbook.sh did that). Single Teton login!
  2. Open  ~/Applications/CrossOver/"SierraChart_64 (Y_SierraChart).app"  on the iMac  (= ~/SierraChart, bottle "Sierra Chart")
     · it logs in with the MacBook's Accounts4/Sierra4 config (account $(grep '^SIERRA_LIVE_ACCOUNT=' "$REPO/.env" | cut -d= -f2)); confirm the connection is UP
     · File ▸ Open Chartbook ▸ AAMichael_lap25.Cht  (the live chartbook, copied from the MacBook 08.10 state)
  3. Analysis ▸ Build Custom Studies DLL ▸ REMOTE BUILD  (source: ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp = the 20.10 source)
     · wait for "Build succeeded" · then on the chart: remove + re-add the MES_AI_DataExport study (or Reload All DLLs)
  4. Study Inputs (persist in the chartbook, should already be right): Input 4 = Y:\\SierraChart_Data\\v9_export
     · Input 21 EnableOrderPlacement and Input 22 as on the MacBook (the chartbook carries them)
     · Trade ▸ Trade Simulation Mode — set EXACTLY as Michael rules for tomorrow (today the MacBook ran DEMO/is_sim=1)
  5. Feed check (terminal):  stat -f "%Sm %N" -t "%Y-%m-%d %H:%M:%S" ~/SierraChart_Data/v9_export/sierra_state.json ~/SierraChart_Data/v9_export/5min.json
     · both must refresh every few seconds (export_promoter promotes .tmp → .json); compare to  date "+%Y-%m-%d %H:%M:%S"
     · cd $REPO && bash scripts/mems26_verify.sh   → DLL deployed==repo, feed fresh, services green
     · $PY scripts/fire_drill.py   → 🟢 GO (the only acceptable NO-GO before arming = LIVE_TRADING_ARMED)
  6. Then step 'arm' (Michael only).
EOF
}

# ---------------------------------------------------------------- arm (printed only)
step_arm(){
  say arm "ARMING = MICHAEL ONLY (standing rule: Claude never arms). When fire_drill is GO:"
  echo "    cd $REPO && sed -i '' 's/^LIVE_TRADING_ARMED=.*/LIVE_TRADING_ARMED=1/' .env && launchctl kickstart -k gui/$U/com.mems26.backend"
  echo "    sleep 20 && curl -s http://127.0.0.1:8000/api/v9/status | $PY -c 'import sys,json;print(json.load(sys.stdin).get(\"mode\"))'"
  echo "  Phone: Render page unchanged ($(grep '^RENDER_MOBILE_URL=' "$REPO/.env" | cut -d= -f2)); direct ZT bookmark → http://10.1.118.70:8000/api/v9/mobile?key=<MOBILE_ACCESS_KEY>"
  echo "  Afterwards: python3 scripts/mems26_snapshot.sh is NOT needed again; write the LIVE_CHANNEL line; update TASK_LOG/STATUS_BOARD."
  echo "  log: $LOG"
}

case "$STEP" in
  all) step_preflight && step_snapshot && step_db && step_env && step_services && step_verify && step_sierra && step_arm ;;
  preflight|snapshot|db|env|services|verify|sierra|arm) "step_$STEP" ;;
  *) echo "usage: $0 [all|preflight|snapshot|db|env|services|verify|sierra|arm]"; exit 2 ;;
esac
