#!/usr/bin/env bash
# ============================================================================
# MEMS26 — Mac-2 (iMac) TAKEOVER · Phase A: prepare the iMac   (run ON the iMac)
#
# Michael ruling 21.10.2026: the iMac takes over trading with the FULL identity of
# the MacBook (same repo path ~/Downloads/mems26_web_git, same .env, same 11
# LaunchAgents, MACHINE_TAG=מק-1, Render relay mems26-mobile). The MacBook keeps
# trading today; the cutover is tonight after 23:00 (phaseB_*).
#
# Phase A is SAFE to run while the MacBook trades:
#   · never opens Sierra on the iMac (Teton = single login — opening it would
#     kick the MacBook's feed), never arms (LIVE_TRADING_ARMED forced to 0),
#     never starts the phone relay (one writer to PHONE_THREAD only).
#   · idempotent — re-run any step.
#
# Usage:  bash scripts/mac2/phaseA_imac_prepare.sh [all|check|pydeps|node|npm|db|env|plists|sierra|services|verify]
# Logs:   ~/mems26_migration_2026-10-21/logs/phaseA_<ts>.log
# ============================================================================
set -u -o pipefail   # pipefail: a check piped through tee must not inherit tee's exit 0 (COWORK_DAILY_READ trap)
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
MIG="${MIG:-$HOME/mems26_migration_2026-10-21}"
REPO="$HOME/Downloads/mems26_web_git"
PG=/Applications/Postgres.app/Contents/Versions/18/bin
PY=/Library/Frameworks/Python.framework/Versions/3.9/bin/python3
LA="$HOME/Library/LaunchAgents"
U=$(id -u)
mkdir -p "$MIG/logs"
LOG="$MIG/logs/phaseA_$(date +%Y%m%dT%H%M%S).log"
STEP="${1:-all}"

say(){ printf '\n\033[1;36m[A/%s]\033[0m %s\n' "$1" "$2" | tee -a "$LOG"; }
ok(){  printf '  \033[1;32m✓\033[0m %s\n' "$*" | tee -a "$LOG"; }
warn(){ printf '  \033[1;33m!\033[0m %s\n' "$*" | tee -a "$LOG"; }
bad(){ printf '  \033[1;31m✗\033[0m %s\n' "$*" | tee -a "$LOG"; }
die(){ bad "$*"; echo "log: $LOG"; exit 1; }
run(){ echo "  \$ $*" | tee -a "$LOG"; "$@" 2>&1 | tee -a "$LOG"; return "${PIPESTATUS[0]}"; }

case "$(hostname)" in *iMac*|*imac*) ;; *) die "this script runs ON the iMac only (hostname=$(hostname))";; esac

sierra_running(){ pgrep -f "SierraChart_64|Y_SierraChart" >/dev/null 2>&1; }          # any Sierra instance
sierra1_running(){ pgrep -f 'Y_SierraChart\)\.app|Y:\\SierraChart\\' >/dev/null 2>&1; }  # the trading instance (~/SierraChart) only
pg_dialog_note(){
  warn "Postgres.app on the iMac shows a one-time PERMISSION DIALOG on the iMac SCREEN for every new client"
  warn "executable (psql, pg_restore, Python). If the command below looks stuck → click 'Allow' on the iMac."
}

# ---------------------------------------------------------------- check
step_check(){
  say check "preconditions"
  [ -d "$REPO/.git" ] && ok "repo present: $REPO ($(cd "$REPO" && git log -1 --format='%h %ci'))" || die "repo missing at $REPO — run the rsync from the MacBook first"
  [ -f "$REPO/.env" ] && ok ".env present ($(wc -l < "$REPO/.env" | tr -d ' ') lines)" || die ".env missing in repo copy"
  [ -d "$MIG/db/mems26_full" ] && ok "full dump present: $(du -sh "$MIG/db/mems26_full" | cut -f1)" || die "dump missing: $MIG/db/mems26_full"
  if (cd "$MIG/db" && shasum -a 256 -c ../SHA256SUMS_db.txt --quiet >>"$LOG" 2>&1); then ok "dump checksums verified ($(wc -l < "$MIG/SHA256SUMS_db.txt" | tr -d ' ') files)"; else die "dump checksum MISMATCH — re-rsync $MIG from the MacBook"; fi
  pgrep -f "bin/postgres -D" >/dev/null && ok "Postgres.app server running" || die "Postgres.app not running — open Postgres.app on the iMac"
  [ -x "$PG/pg_restore" ] && ok "pg_restore $("$PG/pg_restore" --version | awk '{print $3}')" || die "pg_restore not found at $PG"
  [ -x "$PY" ] && ok "python $("$PY" --version 2>&1)" || die "framework python 3.9 missing ($PY) — the LaunchAgents hard-code it"
  if sierra1_running; then die "the trading Sierra (Y_SierraChart → ~/SierraChart) is RUNNING on the iMac — close it. It must stay closed until the cutover tonight (Teton single login)."
  elif sierra_running; then warn "a Sierra instance is running on the iMac ($(pgrep -fl 'Menu Helper' | grep -o 'Y_SierraChart[0-9]*' | head -1)) — not the trading one; make sure it is NOT logged into the live Teton account while the MacBook trades"
  else ok "Sierra not running on the iMac (correct for Phase A)"; fi
  if launchctl list 2>/dev/null | grep -q "com.mems26"; then warn "mems26 agents loaded on the iMac: $(launchctl list | grep com.mems26 | awk '{print $3}' | tr '\n' ' ')"; else ok "no mems26 agents loaded yet"; fi
}

# ---------------------------------------------------------------- pydeps
step_pydeps(){
  say pydeps "python packages = exact MacBook freeze ($(wc -l < "$MIG/pip_freeze_macbook.txt" | tr -d ' ') pins) into framework python 3.9"
  run "$PY" -m pip install -q -r "$MIG/pip_freeze_macbook.txt" || warn "pip reported errors — see log; checking the imports that matter:"
  if "$PY" - <<'EOF' 2>&1 | tee -a "$LOG"
import importlib.util, sys
mods =["fastapi","uvicorn","sqlalchemy","psycopg2","pydantic","yaml","pandas","numpy","httpx","websockets","redis","dotenv"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
print("  imports:", "ALL OK" if not missing else "MISSING " + ", ".join(missing))
sys.exit(1 if missing else 0)
EOF
  then ok "python deps OK"; else die "python deps missing — fix before db/services"; fi
}

# ---------------------------------------------------------------- node
step_node(){
  say node "node 24.10 at /usr/local/bin (what com.mems26.frontend execs: /usr/local/bin/npm)"
  if [ -x /usr/local/bin/node ] && /usr/local/bin/node --version | grep -q "^v24"; then ok "node $(/usr/local/bin/node --version) · npm $(/usr/local/bin/npm --version)"; return 0; fi
  bad "/usr/local/bin/node (v24) missing on the iMac — needs admin ONCE (Michael / Claude-on-iMac with sudo):"
  echo "    option 1 (identical to MacBook): install the official pkg → https://nodejs.org/dist/v24.10.0/node-v24.10.0.pkg"
  echo "        curl -fsSL -o /tmp/node24.pkg https://nodejs.org/dist/v24.10.0/node-v24.10.0.pkg && sudo installer -pkg /tmp/node24.pkg -target /"
  echo "    option 2 (nvm already on the iMac): source ~/.nvm/nvm.sh && nvm install 24.10.0 && \\"
  echo "        sudo ln -sfn \$HOME/.nvm/versions/node/v24.10.0/bin/node /usr/local/bin/node && sudo ln -sfn \$HOME/.nvm/versions/node/v24.10.0/bin/npm /usr/local/bin/npm && sudo ln -sfn \$HOME/.nvm/versions/node/v24.10.0/bin/npx /usr/local/bin/npx"
  return 1
}

# ---------------------------------------------------------------- npm
step_npm(){
  say npm "frontend dependencies (fresh install — node_modules are never copied between machines)"
  [ -x /usr/local/bin/npm ] || { warn "npm missing — do step 'node' first; frontend skipped"; return 1; }
  ( cd "$REPO/frontend/v9" && if [ -f package-lock.json ]; then run /usr/local/bin/npm ci --no-audit --no-fund; else run /usr/local/bin/npm install --no-audit --no-fund; fi ) && ok "frontend node_modules installed" || die "npm install failed"
}

# ---------------------------------------------------------------- db
step_db(){
  say db "restore the MacBook's full dump (7.6 GB, 55 tables) into a fresh 'mems26'"
  if [ -f "$MIG/db/.restored_mems26_full" ]; then ok "already restored on $(cat "$MIG/db/.restored_mems26_full") — skip (delete the marker to redo)"; return 0; fi
  pg_dialog_note
  local have_old have_cur
  have_cur=$("$PG/psql" -d postgres -At -c "select 1 from pg_database where datname='mems26'" 2>>"$LOG") || die "cannot talk to Postgres (dialog not confirmed? see log)"
  have_old=$("$PG/psql" -d postgres -At -c "select 1 from pg_database where datname='mems26_imac_old_aug2026'")
  run "$PG/psql" -d postgres -q -c "select pg_terminate_backend(pid) from pg_stat_activity where datname='mems26' and pid<>pg_backend_pid()" >/dev/null
  if [ "$have_cur" = "1" ] && [ "$have_old" != "1" ]; then
    run "$PG/psql" -d postgres -c "ALTER DATABASE mems26 RENAME TO mems26_imac_old_aug2026" && ok "old iMac DB kept aside as mems26_imac_old_aug2026 (dropped tonight in Phase B)"
  elif [ "$have_cur" = "1" ]; then
    warn "a 'mems26' exists and the Aug copy was already renamed → this is a previous partial restore; dropping it"
    run "$PG/psql" -d postgres -c "DROP DATABASE mems26"
  fi
  run "$PG/psql" -d postgres -c "CREATE DATABASE mems26" || die "CREATE DATABASE failed"
  say db "pg_restore -j 4 (expect several minutes; footprint table is 6.2 GB)"
  local t0; t0=$(date +%s)
  "$PG/pg_restore" -j 4 --no-owner -d mems26 "$MIG/db/mems26_full" > "$MIG/logs/pg_restore_full.log" 2>&1
  local rc=$?; local errs; errs=$(grep -c "ERROR" "$MIG/logs/pg_restore_full.log")
  echo "  pg_restore rc=$rc errors=$errs time=$(( $(date +%s)-t0 ))s (log: $MIG/logs/pg_restore_full.log)" | tee -a "$LOG"
  [ "$errs" -gt 0 ] && { warn "first errors:"; grep "ERROR" "$MIG/logs/pg_restore_full.log" | head -5 | tee -a "$LOG"; }
  run "$PG/psql" -d mems26 -q -c "ANALYZE" >/dev/null
  local ntab; ntab=$("$PG/psql" -d mems26 -At -c "select count(*) from information_schema.tables where table_schema='public'")
  [ "$ntab" = "55" ] && ok "55 tables present" || bad "table count = $ntab (expected 55)"
  local fp tr fp_ref tr_ref
  fp=$("$PG/psql" -d mems26 -At -c "select count(*) from v9_bars_footprint"); tr=$("$PG/psql" -d mems26 -At -c "select count(*) from v9_bars_tick_reversal")
  fp_ref=$(grep '^v9_bars_footprint|' "$MIG/db/STATIC_COUNTS.txt" | cut -d'|' -f2); tr_ref=$(grep '^v9_bars_tick_reversal|' "$MIG/db/STATIC_COUNTS.txt" | cut -d'|' -f2)
  [ "$fp" = "$fp_ref" ] && ok "v9_bars_footprint rows = $fp (== MacBook)" || bad "v9_bars_footprint rows $fp ≠ MacBook $fp_ref"
  [ "$tr" = "$tr_ref" ] && ok "v9_bars_tick_reversal rows = $tr (== MacBook)" || bad "v9_bars_tick_reversal rows $tr ≠ MacBook $tr_ref"
  echo "  hot tables (iMac now vs MacBook at dump time — MacBook keeps growing today, iMac must be ≤):" | tee -a "$LOG"
  for t in v9_trades v9_system_signals v9_decision_vectors v9_tpo_journal v9_trade_management_log v9_bars_5min_continuous; do
    printf '    %-28s iMac=%-9s MacBook@dump=%s\n' "$t" "$("$PG/psql" -d mems26 -At -c "select count(*) from $t")" "$(grep "^$t|" "$MIG/db/ROWCOUNTS_at_dump.txt" | cut -d'|' -f2)" | tee -a "$LOG"
  done
  if [ "$ntab" = "55" ] && [ "$fp" = "$fp_ref" ] && [ "$errs" = "0" ]; then date '+%F %T' > "$MIG/db/.restored_mems26_full"; ok "DB restore verified"; else die "DB restore not clean — inspect $MIG/logs/pg_restore_full.log"; fi
}

# ---------------------------------------------------------------- env
step_env(){
  say env ".env = MacBook's (identity takeover) with LIVE_TRADING_ARMED forced to 0 until Michael arms at cutover"
  if cmp -s "$REPO/.env" "$MIG/env.macbook.copy"; then ok ".env identical to the MacBook copy"; else warn ".env differs from env.macbook.copy (expected only if already disarmed below) — diff:"; diff "$MIG/env.macbook.copy" "$REPO/.env" | head -6 | tee -a "$LOG"; fi
  grep -q '^LIVE_TRADING_ARMED=' "$REPO/.env" && sed -i '' 's/^LIVE_TRADING_ARMED=.*/LIVE_TRADING_ARMED=0/' "$REPO/.env"
  ok "$(grep -n '^LIVE_TRADING_ARMED=' "$REPO/.env")  ← stays 0 until Michael arms (Phase B)"
  for k in MACHINE_TAG RENDER_MOBILE_URL MEMS26_MODE V9_EXPORT_DIR DATABASE_URL SIERRA_LIVE_ACCOUNT; do echo "    $(grep "^$k=" "$REPO/.env")" | tee -a "$LOG"; done
  [ -f "$REPO/frontend/v9/.env.local" ] && ok "frontend/v9/.env.local present" || warn "frontend/v9/.env.local missing — copy $MIG/env.local.frontend.copy"
  mkdir -p "$HOME/SierraChart_Data/v9_export" "$HOME/SierraChart_Data/v9_archive" && ok "export dirs present"
}

# ---------------------------------------------------------------- plists
step_plists(){
  say plists "install the MacBook's 11 LaunchAgents verbatim (identical paths) — NOT loaded in Phase A"
  local n=0
  for p in "$MIG"/launchagents/com.mems26.*.plist; do
    plutil -lint "$p" >/dev/null 2>&1 || die "invalid plist: $p"
    cp "$p" "$LA/" && n=$((n+1))
  done
  ok "$n plists copied to $LA (loaded: $(launchctl list | grep -c com.mems26 || true))"
  grep -L "/Users/michael/Downloads/mems26_web_git" "$LA"/com.mems26.*.plist 2>/dev/null | sed 's/^/    (no repo path, fine): /' | tee -a "$LOG" >/dev/null
  return 0
}

# ---------------------------------------------------------------- sierra
step_sierra(){
  say sierra "Sierra config → iMac ~/SierraChart (chartbooks, Sierra4/Accounts4/KeyboardShortcuts4.config, SymbolSettings, ACS_Source, DLL) — the ~/SierraChart instance must be closed"
  sierra1_running && die "the trading Sierra instance (Y_SierraChart → ~/SierraChart) is running on the iMac — close it first"
  local BK="$MIG/sierra_imac_backup_$(date +%Y%m%dT%H%M%S)"; mkdir -p "$BK/Data" "$BK/ACS_Source"
  cp "$HOME"/SierraChart/*.config "$HOME"/SierraChart/DataFilesFolder.txt "$BK/" 2>/dev/null
  cp "$HOME"/SierraChart/Data/*.Cht "$HOME"/SierraChart/Data/MES_AI_DataExport_64.dll "$BK/Data/" 2>/dev/null
  cp "$HOME"/SierraChart/ACS_Source/MES_AI_DataExport.cpp "$BK/ACS_Source/" 2>/dev/null
  [ -d "$HOME/SierraChart/SymbolSettings" ] && cp -R "$HOME/SierraChart/SymbolSettings" "$BK/"
  ok "iMac's previous Sierra files backed up → $BK"
  local S="$MIG/sierra/SierraChart"
  cp "$S"/*.config "$HOME/SierraChart/" && ok "Sierra4/Accounts4/KeyboardShortcuts4.config ← MacBook"
  cp "$S"/Data/*.Cht "$HOME/SierraChart/Data/" && ok "$(ls "$S"/Data/*.Cht | wc -l | tr -d ' ') chartbooks ← MacBook (AAMichael_lap25.Cht = the live one, 08.10)"
  mkdir -p "$HOME/SierraChart/ACS_Source" && cp "$S/ACS_Source/MES_AI_DataExport.cpp" "$HOME/SierraChart/ACS_Source/" && ok "ACS_Source/MES_AI_DataExport.cpp ← MacBook (20.10 source; Remote Build it in Sierra at cutover)"
  cp "$S/Data/MES_AI_DataExport_64.dll" "$HOME/SierraChart/Data/" && ok "MES_AI_DataExport_64.dll ← MacBook (fallback binary; Remote Build replaces it)"
  [ -d "$S/SymbolSettings" ] && { rm -rf "$HOME/SierraChart/SymbolSettings"; cp -R "$S/SymbolSettings" "$HOME/SierraChart/"; ok "SymbolSettings ← MacBook"; }
  echo "  shasum source: iMac $(shasum "$HOME/SierraChart/ACS_Source/MES_AI_DataExport.cpp" | cut -c1-12) · repo monolith $(shasum "$REPO/sc_study/MES_AI_DataExport_merged.cpp" 2>/dev/null | cut -c1-12 || echo n/a)" | tee -a "$LOG"
  # stale (>1 day) exports on the iMac must not be mistaken for a live feed; fresh ones (another Sierra instance exporting) are left alone
  local nstale; nstale=$(find "$HOME/SierraChart_Data/v9_export" -maxdepth 1 -type f -mtime +1 | wc -l | tr -d ' ')
  if [ "$nstale" -gt 0 ]; then
    mkdir -p "$MIG/v9_export_stale_imac" && find "$HOME/SierraChart_Data/v9_export" -maxdepth 1 -type f -mtime +1 -exec mv {} "$MIG/v9_export_stale_imac/" \; ; ok "$nstale stale (>1d) v9_export files moved to $MIG/v9_export_stale_imac"
  fi
  local nfresh; nfresh=$(find "$HOME/SierraChart_Data/v9_export" -maxdepth 1 -type f -mmin -5 | wc -l | tr -d ' ')
  [ "$nfresh" -gt 0 ] && warn "$nfresh export files are FRESH (<5 min) — a Sierra instance on the iMac is exporting right now ($(pgrep -fl 'Menu Helper' | grep -o 'Y_SierraChart[0-9]*' | head -1))"
  return 0
}

# ---------------------------------------------------------------- services (verification only)
step_services(){
  say services "load ONLY backend (+frontend if node present) for verification — relay/bridge/feeds wait for cutover"
  pg_dialog_note
  grep -q '^LIVE_TRADING_ARMED=0' "$REPO/.env" || die "refusing: .env is not disarmed (run step env)"
  for a in backend frontend; do
    [ "$a" = frontend ] && [ ! -x /usr/local/bin/npm ] && { warn "frontend skipped (no /usr/local/bin/npm yet)"; continue; }
    if launchctl print "gui/$U/com.mems26.$a" >/dev/null 2>&1; then run launchctl kickstart -k "gui/$U/com.mems26.$a" && ok "$a restarted"; else run launchctl bootstrap "gui/$U" "$LA/com.mems26.$a.plist" && ok "$a bootstrapped"; fi
  done
  echo "  waiting 25s for the backend…"; sleep 25
  curl -s -m 5 http://127.0.0.1:8000/api/v9/health | tee -a "$LOG"; echo
  curl -s -m 5 http://127.0.0.1:8000/api/v9/status | "$PY" -c "import sys,json; d=json.load(sys.stdin); print('  status.mode =', d.get('mode'), '| keys:', len(d))" 2>&1 | tee -a "$LOG" || warn "backend not answering yet — tail -40 /tmp/backend.err.log"
}

# ---------------------------------------------------------------- verify
step_verify(){
  say verify "flag_guard · health · mems26_verify (DLL/feed lines are RED by design until Sierra runs at cutover)"
  ( cd "$REPO" && run "$PY" scripts/flag_guard.py | tail -3 )
  curl -s -m 5 http://127.0.0.1:8000/api/v9/health && echo
  ( cd "$REPO" && bash scripts/mems26_verify.sh 2>&1 | tail -25 | tee -a "$LOG" ) || true
  say verify "PHASE A SUMMARY"
  echo "  repo HEAD    : $(cd "$REPO" && git log -1 --format='%h %ci')"
  echo "  DB           : $([ -f "$MIG/db/.restored_mems26_full" ] && echo "restored $(cat "$MIG/db/.restored_mems26_full")" || echo NOT RESTORED)"
  echo "  node         : $([ -x /usr/local/bin/node ] && /usr/local/bin/node --version || echo MISSING — step node)"
  echo "  armed        : $(grep '^LIVE_TRADING_ARMED=' "$REPO/.env") (must be 0 until Phase B)"
  echo "  agents loaded: $(launchctl list | grep com.mems26 | awk '{print $3}' | tr '\n' ' ')"
  if sierra1_running; then echo "  Sierra       : trading instance (Y_SierraChart) RUNNING ❗ — must stay closed until cutover"
  elif sierra_running; then echo "  Sierra       : only $(pgrep -fl 'Menu Helper' | grep -o 'Y_SierraChart[0-9]*' | head -1) running (not the trading instance)"
  else echo "  Sierra       : closed ✓ (stays closed until cutover)"; fi
  echo "  NEXT         : tonight ≥23:35 IL — on the MacBook: bash scripts/mac2/phaseB_cutover_macbook.sh all ; then here: bash scripts/mac2/phaseB_imac_golive.sh all"
  echo "  log: $LOG"
}

case "$STEP" in
  all) step_check && step_pydeps && { step_node || true; } && { step_npm || true; } && step_db && step_env && step_plists && step_sierra && step_services && step_verify ;;
  check|pydeps|node|npm|db|env|plists|sierra|services|verify) "step_$STEP" ;;
  *) echo "usage: $0 [all|check|pydeps|node|npm|db|env|plists|sierra|services|verify]"; exit 2 ;;
esac
