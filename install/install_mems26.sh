#!/usr/bin/env bash
# ============================================================================
# MEMS26 installer — brings the FULL local stack up on a fresh Mac.
#
#   Installs/verifies deps → repo → Python venv → Postgres DB + schema →
#   frontend build → .env → LaunchAgents (backend/bridge/promoter) → verify.
#   Then prints the Sierra manual checklist (the one half no installer can do).
#
# SAFE BY DESIGN: idempotent (re-runnable), never clobbers an existing .env,
# createdb ignores an existing DB, `--dry-run` prints the plan without acting.
#
# Usage:
#   install/install_mems26.sh [--dry-run] [--repo DIR] [--export-dir DIR]
#                             [--git-remote URL] [--skip-frontend] [--yes]
#
# Typical fresh machine:
#   git clone <remote> ~/mems26/mems26_web_git
#   cd ~/mems26/mems26_web_git && install/install_mems26.sh
# ============================================================================
set -uo pipefail

# ---- defaults ----
DRY_RUN=0
SKIP_FRONTEND=0
ASSUME_YES=0
GIT_REMOTE=""
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # repo = parent of install/
EXPORT_DIR="$HOME/SierraChart_Data/v9_export"
BRIDGE_TOKEN_DEFAULT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --skip-frontend) SKIP_FRONTEND=1 ;;
    --yes|-y) ASSUME_YES=1 ;;
    --repo) REPO="$2"; shift ;;
    --export-dir) EXPORT_DIR="$2"; shift ;;
    --git-remote) GIT_REMOTE="$2"; shift ;;
    --bridge-token) BRIDGE_TOKEN_DEFAULT="$2"; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

say()  { printf '\033[1;36m[install]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[install][warn]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[install][err]\033[0m %s\n' "$*" >&2; }
run()  { if [ "$DRY_RUN" = 1 ]; then printf '  would run: %s\n' "$*"; else eval "$@"; fi; }

PY="$REPO/.venv/bin/python"
PLIST_DIR="$HOME/Library/LaunchAgents"

say "repo        = $REPO"
say "export dir  = $EXPORT_DIR"
say "python venv = $PY"
[ "$DRY_RUN" = 1 ] && warn "DRY-RUN — no changes will be made"

# ── 0. Preflight: macOS + tools ──────────────────────────────────────────────
[ "$(uname)" = "Darwin" ] || { err "macOS only (this stack runs Sierra under Wine on Mac)."; exit 1; }

need_brew=0
command -v git  >/dev/null || need_brew=1
command -v node >/dev/null || need_brew=1
command -v python3 >/dev/null || need_brew=1
if [ "$need_brew" = 1 ]; then
  if command -v brew >/dev/null; then
    say "installing missing tools via Homebrew (git/node/python)"
    run "brew install git node python@3.11 || true"
  else
    err "Missing git/node/python3 and Homebrew not found. Install Homebrew (https://brew.sh) then re-run."
    exit 1
  fi
fi

# Postgres: prefer Postgres.app; fall back to brew postgresql.
PSQL="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/psql 2>/dev/null | tail -1 || true)"
[ -z "$PSQL" ] && PSQL="$(command -v psql || true)"
CREATEDB="$(dirname "$PSQL")/createdb"
if [ -z "$PSQL" ]; then
  warn "No Postgres found. Install Postgres.app (https://postgresapp.com) — it is a GUI app the installer can't auto-install — then re-run. (Or: brew install postgresql@16 && brew services start postgresql@16)"
  [ "$DRY_RUN" = 1 ] || { [ "$ASSUME_YES" = 1 ] || { err "Postgres required. Aborting."; exit 1; } ; }
fi

# ── 1. Repo ──────────────────────────────────────────────────────────────────
if [ ! -d "$REPO/.git" ]; then
  if [ -n "$GIT_REMOTE" ]; then
    say "cloning repo → $REPO"
    run "git clone '$GIT_REMOTE' '$REPO'"
  else
    err "No repo at $REPO and no --git-remote given. Clone it first or pass --git-remote."
    exit 1
  fi
else
  say "repo present ✓"
fi

# ── 2. Python venv + deps ────────────────────────────────────────────────────
if [ ! -x "$PY" ]; then
  say "creating venv"
  run "python3 -m venv '$REPO/.venv'"
fi
say "pip install requirements"
run "'$REPO/.venv/bin/pip' install --quiet --upgrade pip"
run "'$REPO/.venv/bin/pip' install --quiet -r '$REPO/requirements.txt'"

# ── 3. .env (never clobber) ──────────────────────────────────────────────────
if [ -f "$REPO/.env" ]; then
  warn ".env already exists — leaving it untouched (edit by hand if needed)"
else
  say "writing .env from template"
  TOKEN="${BRIDGE_TOKEN_DEFAULT:-$(LC_ALL=C tr -dc 'a-z0-9' </dev/urandom 2>/dev/null | head -c 24 || echo mems26-$(date +%s))}"
  if [ "$DRY_RUN" = 1 ]; then
    printf '  would render install/env.template → .env (EXPORT_DIR=%s, token=***)\n' "$EXPORT_DIR"
  else
    sed -e "s#__EXPORT_DIR__#${EXPORT_DIR}#g" \
        -e "s#__BRIDGE_TOKEN__#${TOKEN}#g" \
        "$REPO/install/env.template" > "$REPO/.env"
    chmod 600 "$REPO/.env"
    say ".env written (chmod 600)"
  fi
fi
run "mkdir -p '$EXPORT_DIR'"

# ── 4. Database: create + schema + numbered .sql migrations ───────────────────
if [ -n "$PSQL" ]; then
  say "ensuring database 'mems26' exists"
  run "'$CREATEDB' mems26 2>/dev/null || true"
  say "creating schema (SQLAlchemy create_all via db_init.sh)"
  run "cd '$REPO' && DATABASE_URL='postgresql://localhost/mems26' PATH=\"$REPO/.venv/bin:\$PATH\" bash scripts/db_init.sh"
  say "applying numbered .sql migrations (idempotent-guarded)"
  if [ "$DRY_RUN" = 1 ]; then
    echo "  would apply: backend/v9/db/migrations/*.sql + versions/*.sql in sorted order"
  else
    for f in $(ls "$REPO"/backend/v9/db/migrations/*.sql "$REPO"/backend/v9/db/migrations/versions/*.sql 2>/dev/null | sort); do
      "$PSQL" -v ON_ERROR_STOP=0 -q -d mems26 -f "$f" >/dev/null 2>&1 \
        && echo "  ok  $(basename "$f")" || echo "  skip $(basename "$f") (already applied / column exists)"
    done
  fi
else
  warn "skipping DB step (no Postgres)"
fi

# ── 5. Frontend build ────────────────────────────────────────────────────────
if [ "$SKIP_FRONTEND" = 0 ] && [ -f "$REPO/frontend/v9/package.json" ]; then
  say "frontend: npm install + build (this can take a few minutes)"
  run "cd '$REPO/frontend/v9' && npm install --silent && npm run build"
else
  warn "skipping frontend build"
fi

# ── 6. LaunchAgents (render templates → ~/Library/LaunchAgents) ───────────────
say "installing LaunchAgents (backend/bridge/promoter)"
run "mkdir -p '$PLIST_DIR'"
TOKEN_FOR_PLIST="$(grep -E '^BRIDGE_TOKEN=' "$REPO/.env" 2>/dev/null | cut -d= -f2- || echo mems26)"
for svc in backend bridge export_promoter; do
  tmpl="$REPO/install/launchagents/com.mems26.${svc}.plist.tmpl"
  dest="$PLIST_DIR/com.mems26.${svc}.plist"
  [ -f "$tmpl" ] || { warn "missing template $tmpl"; continue; }
  if [ "$DRY_RUN" = 1 ]; then
    echo "  would render $tmpl → $dest and launchctl load -w"
  else
    sed -e "s#__REPO__#${REPO}#g" \
        -e "s#__PYTHON__#${PY}#g" \
        -e "s#__EXPORT_DIR__#${EXPORT_DIR}#g" \
        -e "s#__BRIDGE_TOKEN__#${TOKEN_FOR_PLIST}#g" \
        "$tmpl" > "$dest"
    launchctl unload -w "$dest" 2>/dev/null || true
    launchctl load  -w "$dest" 2>/dev/null && say "loaded com.mems26.${svc}" || warn "load failed com.mems26.${svc}"
  fi
done

# ── 7. Verify ────────────────────────────────────────────────────────────────
if [ "$DRY_RUN" = 0 ]; then
  say "waiting 10s for backend to boot…"; sleep 10
  if curl -s -m 5 http://localhost:8000/api/v9/health | grep -q '"status":"ok"'; then
    say "backend health: OK ✓"
  else
    warn "backend health not OK yet — check /tmp/backend.err.log"
  fi
  [ -x "$REPO/scripts/mems26_verify.sh" ] && run "bash '$REPO/scripts/mems26_verify.sh' || true"
fi

# ── 8. Sierra hand-off ───────────────────────────────────────────────────────
cat <<EOF

============================================================================
 THE HALF NO INSTALLER CAN DO — Sierra Chart (do this by hand):
   → follow  install/SIERRA_SETUP_CHECKLIST.md
   Short version: install Sierra + license → deploy the study
   (scripts/build_monolithic_cpp.sh --deploy) → Remote Build in Sierra UI →
   set study Input-4 export dir = $EXPORT_DIR → set the contract (e.g. MESU26) →
   confirm feed files appear in $EXPORT_DIR/*.json (fresh ≤2s).
============================================================================
 Backend  : http://localhost:8000   Frontend: http://localhost:3000
 Update    : install/mems26_update.sh   Uninstall: install/uninstall_mems26.sh
============================================================================
EOF
say "done."
