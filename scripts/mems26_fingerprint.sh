#!/bin/bash
# mems26_fingerprint.sh — machine-identity digest (Michael 2026-08-13:
# "הפרונטאנד שם לא אותו הדבר... אני מניח שעוד הרבה דברים לא זהים").
#
# Run on BOTH machines; diff the FP| lines. Identical lines (excluding the
# WHITELIST-marked machine-specific ones) = identical machine. Read-only.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "══ MEMS26 fingerprint · $(hostname -s) · $(date '+%Y-%m-%d %H:%M:%S %Z') ══"

# 1. code
echo "FP|git.head=$(git rev-parse --short HEAD 2>/dev/null)"
echo "FP|git.branch=$(git branch --show-current 2>/dev/null)"
echo "FP|git.dirty_files=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"

# 2. study source (canonical identity)
echo "FP|study.repo_monolith=$(shasum -a256 sc_study/MES_AI_DataExport_merged.cpp 2>/dev/null | awk '{print $1}')"
echo "FP|study.deployed=$(shasum -a256 "$HOME/SierraChart/ACS_Source/MES_AI_DataExport.cpp" 2>/dev/null | awk '{print $1}')"

# 3. ruled flags
echo "FP|flags=$(python3 scripts/flag_guard.py 2>&1 | tail -1 | tr -d ' ')"

# 4. full .env identity (hash, no secrets printed). Machine-specific keys excluded.
ENV_EXCLUDE='^(MACHINE_TAG|RENDER_MOBILE_URL|SIERRA_LIVE_ACCOUNT)='
ENV_NORM=$(grep -v '^#' .env 2>/dev/null | grep -v '^[[:space:]]*$' | grep -Ev "$ENV_EXCLUDE" | sort)
echo "FP|env.vars=$(echo "$ENV_NORM" | wc -l | tr -d ' ')"
echo "FP|env.sha=$(echo "$ENV_NORM" | shasum -a256 | awk '{print $1}')"
echo "FP|env.machine_specific=$(grep -E "$ENV_EXCLUDE" .env 2>/dev/null | cut -d= -f1 | sort | tr '\n' ',')  # WHITELIST (allowed to differ)"

# 5. running backend actually newer than the code it runs
BOOT=$(grep -a "env_loader" /tmp/backend.err.log 2>/dev/null | tail -1 | grep -o "applied [0-9]* vars" || echo "no-boot-line")
echo "FP|backend.boot=$BOOT"
echo "FP|backend.http=$(curl -s -o /dev/null -w '%{http_code}' -m 4 http://localhost:8000/api/v9/health 2>/dev/null)"
BE_PID=$(lsof -ti :8000 -sTCP:LISTEN 2>/dev/null | head -1)
if [ -n "${BE_PID:-}" ]; then
  BE_START=$(ps -o lstart= -p "$BE_PID" 2>/dev/null | xargs -I{} date -j -f "%a %b %d %T %Y" "{}" +%s 2>/dev/null || echo 0)
  LAST_PULL=$(stat -f %m .git/FETCH_HEAD 2>/dev/null || echo 0)
  if [ "$BE_START" -gt 0 ] && [ "$LAST_PULL" -gt 0 ] && [ "$BE_START" -lt "$LAST_PULL" ]; then
    echo "FP|backend.staleness=STALE — backend started BEFORE last git pull → restart required"
  else
    echo "FP|backend.staleness=ok"
  fi
else
  echo "FP|backend.staleness=not-running"
fi

# 6. frontend: running + serving CURRENT code
echo "FP|frontend.http=$(curl -s -o /dev/null -w '%{http_code}' -m 4 http://localhost:3000 2>/dev/null)"
FE_DIR="frontend/v9"
FE_PID=$(lsof -ti :3000 -sTCP:LISTEN 2>/dev/null | head -1)
if [ -z "${FE_PID:-}" ]; then
  echo "FP|frontend.staleness=not-running"
elif ps -p "$FE_PID" -o command= 2>/dev/null | grep -q "dev"; then
  # next dev = hot-reload, serves current src by design
  echo "FP|frontend.staleness=ok(dev,hot-reload)"
elif [ -f "$FE_DIR/.next/BUILD_ID" ]; then
  echo "FP|frontend.build_id=$(cat "$FE_DIR/.next/BUILD_ID")"
  NEWEST_SRC=$(find "$FE_DIR/src" -name "*.ts*" -newer "$FE_DIR/.next/BUILD_ID" 2>/dev/null | wc -l | tr -d ' ')
  [ "$NEWEST_SRC" -gt 0 ] && echo "FP|frontend.staleness=STALE — $NEWEST_SRC src files newer than build → next build + restart" || echo "FP|frontend.staleness=ok(prod-build)"
else
  echo "FP|frontend.staleness=UNKNOWN — :3000 alive but no dev marker and no BUILD_ID"
fi

# 7. Sierra detection (Michael 13.08: "המערכת לא מזהה את סיירה אחרי בילד")
EXP="$HOME/SierraChart_Data/v9_export"
if [ -d "$EXP" ]; then
  NOW=$(date +%s)
  SS_AGE="missing"; [ -f "$EXP/sierra_state.json" ] && SS_AGE=$(( NOW - $(stat -f %m "$EXP/sierra_state.json") ))s
  NEWEST=$(ls -t "$EXP" 2>/dev/null | head -1)
  NEW_AGE="none"; [ -n "$NEWEST" ] && NEW_AGE=$(( NOW - $(stat -f %m "$EXP/$NEWEST") ))s
  TMP_STUCK=$(find "$EXP" -name "*.tmp" -mmin +2 2>/dev/null | wc -l | tr -d ' ')
  echo "FP|sierra.state_age=$SS_AGE"
  echo "FP|sierra.newest_export=$NEWEST ($NEW_AGE)"
  echo "FP|sierra.stuck_tmp=$TMP_STUCK  # >0 = promoter dead (Wine-rename class)"
else
  echo "FP|sierra.export_dir=MISSING ($EXP) — study Input-4 wrong path or study not loaded"
fi
for agent in export_promoter bridge backend; do
  launchctl list 2>/dev/null | grep -q "com.mems26.$agent" \
    && echo "FP|agent.$agent=loaded" || echo "FP|agent.$agent=NOT-LOADED"
done

# 8. LaunchAgents deployed vs repo
LA_MISMATCH=0; LA_TOTAL=0
for f in launchagents/com.mems26.*.plist; do
  [ -f "$f" ] || continue
  LA_TOTAL=$((LA_TOTAL+1))
  base=$(basename "$f")
  dep="$HOME/Library/LaunchAgents/$base"
  if [ ! -f "$dep" ] || ! cmp -s "$f" "$dep"; then LA_MISMATCH=$((LA_MISMATCH+1)); fi
done
echo "FP|launchagents=$((LA_TOTAL-LA_MISMATCH))/$LA_TOTAL match repo (differences can be legit per-machine paths — diff before panicking)"

echo "══ end fingerprint — diff the FP| lines between machines ══"
