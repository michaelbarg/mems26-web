#!/usr/bin/env bash
# ============================================================================
# MEMS26 update — pull the latest code from GitHub and safely restart.
#
# The "update from the dev machine" half of the story: you push from the dev
# Mac, then run THIS on the trading Mac (or it can run on a schedule — see the
# auto-deploy note in docs/plans/PORTABILITY_INSTALLABLE_APP_2026-07-03.md).
#
# Gated + safe: snapshots out-of-git surfaces first, refuses to restart while a
# trade/slot is open, verifies after. Pre-LIVE default = human-run (not auto).
#
# Usage: install/mems26_update.sh [--branch NAME] [--dry-run]
# ============================================================================
set -uo pipefail

BRANCH="release"
DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --branch) BRANCH="$2"; shift ;;
    --dry-run) DRY_RUN=1 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac; shift
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1
say()  { printf '\033[1;36m[update]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[update][warn]\033[0m %s\n' "$*"; }
run()  { if [ "$DRY_RUN" = 1 ]; then printf '  would run: %s\n' "$*"; else eval "$@"; fi; }

PSQL="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/psql 2>/dev/null | tail -1 || command -v psql || true)"

# 1. Is there anything to pull?
say "fetching origin/$BRANCH"
run "git fetch --quiet origin '$BRANCH'"
LOCAL="$(git rev-parse HEAD 2>/dev/null)"
REMOTE="$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "$LOCAL")"
if [ "$LOCAL" = "$REMOTE" ]; then
  say "already up to date ($LOCAL) — nothing to do."
  exit 0
fi
say "update available: $LOCAL → $REMOTE"

# 2. Refuse to restart with an open position/slot.
if [ -n "$PSQL" ]; then
  OPEN="$("$PSQL" -tA postgresql://localhost/mems26 -c "SELECT count(*) FROM v9_trades WHERE state NOT IN ('CLOSED','closed')" 2>/dev/null || echo '?')"
  if [ "$OPEN" != "0" ] && [ "$OPEN" != "" ]; then
    warn "There are OPEN trades ($OPEN) — refusing to restart. Flatten first, then re-run."
    exit 3
  fi
fi

# 3. Snapshot out-of-git surfaces (DLL/.env/LaunchAgents) before changing anything.
[ -x scripts/mems26_snapshot.sh ] && run "scripts/mems26_snapshot.sh 'pre-update-${REMOTE:0:8}'"

# 4. Pull (fast-forward only — no surprise merges on a trading box).
run "git merge --ff-only 'origin/$BRANCH'"

# 5. Refresh deps if they changed.
if ! git diff --quiet "$LOCAL" "$REMOTE" -- requirements.txt 2>/dev/null; then
  say "requirements.txt changed → pip install"
  run "'$REPO/.venv/bin/pip' install --quiet -r requirements.txt"
fi
if ! git diff --quiet "$LOCAL" "$REMOTE" -- frontend/v9/package.json 2>/dev/null; then
  say "frontend deps changed → npm install + build"
  run "cd frontend/v9 && npm install --silent && npm run build && cd '$REPO'"
fi

# 6. Restart backend via launchd (NOT manual nohup).
say "restarting backend"
run "launchctl kickstart -k gui/\$(id -u)/com.mems26.backend"
run "sleep 10"

# 7. Verify.
if [ "$DRY_RUN" = 0 ]; then
  curl -s -m 5 http://localhost:8000/api/v9/health | grep -q '"status":"ok"' \
    && say "health OK ✓ — now at $(git rev-parse --short HEAD)" \
    || warn "health not OK — check /tmp/backend.err.log (roll back: scripts/mems26_restore.sh)"
  [ -x scripts/mems26_verify.sh ] && bash scripts/mems26_verify.sh || true
fi
say "done."
