#!/usr/bin/env bash
# ============================================================================
# mems26_doctor.sh — full install/runtime diagnostic for a machine where the
# installer was run but something is stuck. READ-ONLY. Run it first; it tells
# you exactly what's present, what's missing, and the single most likely NEXT
# STEP. Safe to run any time, any number of times.
#
#   bash scripts/mems26_doctor.sh
# ============================================================================
set +e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" 2>/dev/null
[ -f .env ] && { set -a; . ./.env 2>/dev/null; set +a; }
EXPORT_DIR="${V9_EXPORT_DIR:-$HOME/SierraChart_Data/v9_export}"
PY="$REPO/.venv/bin/python"
PSQL="$(ls /Applications/Postgres.app/Contents/Versions/*/bin/psql 2>/dev/null | tail -1 || command -v psql 2>/dev/null)"
NEXT=""   # first unmet prerequisite wins

hdr(){ printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
y(){ printf '  ✅ %s\n' "$*"; }
n(){ printf '  ❌ %s\n' "$*"; [ -z "$NEXT" ] && NEXT="$1"; }
w(){ printf '  ⚠️  %s\n' "$*"; }

echo "MEMS26 doctor — $(date '+%F %T %Z') — host $(hostname) — repo $REPO"

hdr "1. Toolchain"
command -v brew   >/dev/null && y "Homebrew $(brew --version 2>/dev/null | head -1)" || w "Homebrew missing (needed only to install other tools)"
command -v git    >/dev/null && y "git $(git --version | awk '{print $3}')"        || n "install git (brew install git)"
command -v node   >/dev/null && y "node $(node -v)"                                 || n "install node (brew install node)"
command -v python3>/dev/null && y "python3 $(python3 -V 2>&1 | awk '{print $2}')"   || n "install python3 (brew install python@3.11)"

hdr "2. Postgres"
if [ -n "$PSQL" ]; then y "psql found: $PSQL"
  if "$PSQL" -tA postgresql://localhost/mems26 -c "SELECT 1" >/dev/null 2>&1; then
    TC=$("$PSQL" -tA postgresql://localhost/mems26 -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null)
    y "DB 'mems26' reachable — $TC tables"
    [ "${TC:-0}" -lt 10 ] && w "few tables — schema may be incomplete (re-run scripts/db_init.sh)"
  else
    n "DB 'mems26' unreachable — is Postgres.app running? create it: createdb mems26 && scripts/db_init.sh"
  fi
else
  n "Postgres not installed — install Postgres.app (https://postgresapp.com) then re-run installer"
fi

hdr "3. Repo + code"
if [ -d "$REPO/.git" ]; then
  y "git repo — HEAD $(git rev-parse --short HEAD 2>/dev/null) on $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
  [ -n "$(git status --porcelain 2>/dev/null)" ] && w "working tree has local changes ($(git status --porcelain | wc -l | tr -d ' ') files)"
else
  n "no git repo at $REPO — unpack the bundle / clone first"
fi
[ -f "$REPO/requirements.txt" ] && y "requirements.txt present" || n "requirements.txt missing — repo incomplete"

hdr "4. Python venv + deps"
if [ -x "$PY" ]; then
  y "venv python $("$PY" -V 2>&1 | awk '{print $2}')"
  miss=""
  for m in fastapi uvicorn sqlalchemy psycopg2 pydantic yaml httpx websockets; do
    "$PY" -c "import $m" 2>/dev/null || miss="$miss $m"
  done
  [ -z "$miss" ] && y "all core packages import" || n "pip deps missing:$miss — run: .venv/bin/pip install -r requirements.txt"
else
  n "no venv — run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
fi

hdr "5. .env"
if [ -f "$REPO/.env" ]; then
  y ".env present"
  grep -q "^DATABASE_URL=postgresql" .env && y "DATABASE_URL → Postgres ✓" || n "DATABASE_URL not set to postgresql://localhost/mems26 in .env (SQLite fallback risk!)"
  grep -q "^V9_EXPORT_DIR=" .env && y "V9_EXPORT_DIR set" || w "V9_EXPORT_DIR not in .env (defaults to ~/SierraChart_Data/v9_export)"
else
  n "no .env — copy install/env.template → .env and fill paths (installer does this)"
fi

hdr "6. LaunchAgents"
for svc in backend bridge export_promoter startup_check; do
  if launchctl list 2>/dev/null | grep -q "com.mems26.$svc"; then y "com.mems26.$svc loaded"
  elif [ -f "$HOME/Library/LaunchAgents/com.mems26.$svc.plist" ]; then w "com.mems26.$svc plist present but NOT loaded (launchctl load -w ~/Library/LaunchAgents/com.mems26.$svc.plist)"
  else n "com.mems26.$svc not installed — re-run install/install_mems26.sh"; fi
done

hdr "7. Services + ports"
if lsof -tnP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  if curl -s -m 4 http://localhost:8000/api/v9/health 2>/dev/null | grep -q '"status":"ok"'; then y "Backend :8000 health OK"
  else w "Backend :8000 listening but health not OK — tail /tmp/backend.err.log"; fi
else n "Backend :8000 not listening — check /tmp/backend.err.log; restart: launchctl kickstart -k gui/\$(id -u)/com.mems26.backend"; fi
pgrep -f json_bridge.py >/dev/null 2>&1 && y "Bridge running" || w "Bridge not running (com.mems26.bridge)"
pgrep -f v9_export_promoter.py >/dev/null 2>&1 && y "Promoter running" || w "Promoter not running"
if lsof -tnP -iTCP:3000 -sTCP:LISTEN >/dev/null 2>&1; then y "Frontend :3000 up"; else w "Frontend :3000 not up (dashboard only; cd frontend/v9 && npm run build && npm start)"; fi

hdr "8. Sierra feed"
if [ -d "$EXPORT_DIR" ]; then
  cnt=$(ls "$EXPORT_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
  if [ "$cnt" -gt 0 ]; then
    newest=0; for f in "$EXPORT_DIR"/*.json; do m=$(stat -f %m "$f" 2>/dev/null||echo 0); [ "$m" -gt "$newest" ] && newest=$m; done
    age=$(( $(date +%s) - newest ))
    y "$cnt export files; newest ${age}s old"
    [ "$age" -gt 120 ] && w "feed not fresh — normal outside RTH; during RTH check Sierra study + Input-4 + promoter"
  else
    w "export dir exists but empty — deploy the Sierra study + set Input-4 (install/SIERRA_SETUP_CHECKLIST.md)"
  fi
else
  w "export dir $EXPORT_DIR missing — Sierra study not exporting yet (see SIERRA_SETUP_CHECKLIST.md)"
fi

hdr "VERDICT"
if [ -n "$NEXT" ]; then
  printf '  ❌ NEXT STEP → %s\n' "$NEXT"
else
  printf '  ✅ core install looks complete. If the feed is empty, finish the Sierra study steps (install/SIERRA_SETUP_CHECKLIST.md).\n'
fi
printf '  logs: /tmp/backend.err.log · /tmp/bridge.err.log · /tmp/mems26_startup_report.txt\n'
