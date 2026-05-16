#!/usr/bin/env bash
# MEMS26 Stage Runner — safe automation for prompt stages
# Usage: bash scripts/run_stage.sh <stage_name>
#
# Rules:
# - Never enables SHADOW/DEMO/LIVE
# - Checks git status before running
# - Captures logs
# - Runs focused tests
# - Sends Slack summary if webhook set
# - Exits non-zero on failure

set -euo pipefail

PROJ="/Users/michael/Downloads/mems26_web_git"
STAGES_DIR="$PROJ/scripts/stages"
LOG_DIR="$PROJ/docs/reports/stage_runs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── Args ──
STAGE="${1:-}"
if [ -z "$STAGE" ]; then
  echo "Usage: bash scripts/run_stage.sh <stage_name>"
  echo "Available stages:"
  ls "$STAGES_DIR"/*.sh 2>/dev/null | xargs -I{} basename {} .sh | sed 's/^/  /'
  exit 1
fi

STAGE_SCRIPT="$STAGES_DIR/${STAGE}.sh"
if [ ! -f "$STAGE_SCRIPT" ]; then
  echo "ERROR: Stage '$STAGE' not found at $STAGE_SCRIPT"
  exit 1
fi

LOG_FILE="$LOG_DIR/${STAGE}_${TIMESTAMP}.log"

# ── Safety checks ──
echo "═══ MEMS26 Stage Runner: $STAGE ═══"
echo "Time: $(date)"
echo "Log:  $LOG_FILE"
echo ""

# Git safety
cd "$PROJ"
DIRTY=$(git status --short | grep -v "^??" | wc -l | tr -d ' ')
if [ "$DIRTY" -gt 0 ]; then
  echo "WARNING: $DIRTY tracked dirty file(s):"
  git status --short | grep -v "^??"
  echo ""
  echo "Proceeding anyway (non-destructive stage)..."
fi

# Mode safety
if grep -qE "MEMS26_MODE=.*(demo|live)" .env 2>/dev/null; then
  echo "ERROR: DEMO or LIVE mode detected in .env — REFUSING to run"
  exit 1
fi

# ── Run stage ──
echo "Running: $STAGE_SCRIPT"
echo "─────────────────────────────────────"

if bash "$STAGE_SCRIPT" 2>&1 | tee "$LOG_FILE"; then
  RESULT="PASS"
  EXIT_CODE=0
else
  RESULT="FAIL"
  EXIT_CODE=1
fi

echo "─────────────────────────────────────"
echo "Result: $RESULT"
echo "Log:    $LOG_FILE"

# ── Slack notification (optional) ──
WEBHOOK="${SLACK_UAT_WEBHOOK:-${SLACK_WEBHOOK_URL:-}}"
if [ -n "$WEBHOOK" ]; then
  SUMMARY="Stage *$STAGE* $RESULT at $(date +%H:%M)"
  curl -s -X POST "$WEBHOOK" -H 'Content-type: application/json' \
    -d "{\"text\":\"$SUMMARY\"}" >/dev/null 2>&1 || true
fi

echo "═══ Stage $STAGE complete: $RESULT ═══"
exit $EXIT_CODE
