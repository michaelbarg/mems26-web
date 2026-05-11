#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 Environment Check — verifies all deps + paths
#
# Usage: ./scripts/check_env.sh
# Exit:  0 = all good, 1 = missing dependencies
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

FAIL=0
WARN=0

check_ok() { printf "${GREEN}  [OK]${RESET}   %s\n" "$1"; }
check_fail() { printf "${RED}  [FAIL]${RESET} %s\n" "$1"; FAIL=1; }
check_warn() { printf "${YELLOW}  [WARN]${RESET} %s\n" "$1"; WARN=1; }

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

printf "${CYAN}═══════════════════════════════════════════════════════════════${RESET}\n"
printf "${CYAN}  MEMS26 Environment Check${RESET}\n"
printf "${CYAN}═══════════════════════════════════════════════════════════════${RESET}\n"
echo ""

# ── Python ────────────────────────────────────────────────────
echo "Python:"
if command -v python3 >/dev/null 2>&1; then
    PY_VER=$(python3 --version 2>&1)
    check_ok "python3: $PY_VER"
else
    check_fail "python3 not found"
fi

# Python packages
for pkg in fastapi uvicorn pydantic sqlalchemy redis websockets dotenv yaml; do
    if python3 -c "import $pkg" 2>/dev/null; then
        check_ok "python3 -c 'import $pkg'"
    else
        check_fail "Python package '$pkg' not installed"
    fi
done

# ── Node.js ───────────────────────────────────────────────────
echo ""
echo "Node.js:"
if command -v node >/dev/null 2>&1; then
    NODE_VER=$(node --version 2>&1)
    check_ok "node: $NODE_VER"
else
    check_fail "node not found"
fi

if command -v npm >/dev/null 2>&1; then
    NPM_VER=$(npm --version 2>&1)
    check_ok "npm: $NPM_VER"
else
    check_fail "npm not found"
fi

# Check frontend node_modules
if [[ -d "$REPO_ROOT/frontend/v9/node_modules" ]]; then
    check_ok "frontend/v9/node_modules exists"
else
    check_fail "frontend/v9/node_modules missing — run 'cd frontend/v9 && npm install'"
fi

# ── Directories ───────────────────────────────────────────────
echo ""
echo "Directories:"
for dir in \
    "$REPO_ROOT" \
    "$HOME/SierraChart_Data/v9_export" \
    "$REPO_ROOT/backend/v9" \
    "$REPO_ROOT/bridge" \
    "$REPO_ROOT/frontend/v9"; do
    if [[ -d "$dir" ]]; then
        check_ok "$dir"
    else
        check_fail "$dir missing"
    fi
done

# DLL source (outside repo, optional)
if [[ -f "$HOME/SierraChart/ACS_Source/MES_AI_DataExport.cpp" ]]; then
    check_ok "DLL source: ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp"
else
    check_warn "DLL source not found (OK if not editing DLL)"
fi

# ── Environment Variables ─────────────────────────────────────
echo ""
echo "Environment (.env):"
if [[ -f "$REPO_ROOT/.env" ]]; then
    check_ok ".env file exists"
    # Source it
    set -a; source "$REPO_ROOT/.env"; set +a

    for var in UPSTASH_REDIS_REST_URL UPSTASH_REDIS_REST_TOKEN BRIDGE_TOKEN V9_EXPORT_DIR; do
        if [[ -n "${!var:-}" ]]; then
            check_ok "$var is set"
        else
            check_fail "$var is empty or missing in .env"
        fi
    done
else
    check_fail ".env file missing"
fi

if [[ -f "$REPO_ROOT/frontend/v9/.env.local" ]]; then
    check_ok "frontend/v9/.env.local exists"
else
    check_warn "frontend/v9/.env.local missing"
fi

# ── Git hooks ─────────────────────────────────────────────────
echo ""
echo "Git hooks:"
if [[ -x "$REPO_ROOT/.git/hooks/pre-commit" ]]; then
    check_ok "pre-commit hook installed"
else
    check_warn "pre-commit hook not installed"
fi
if [[ -x "$REPO_ROOT/.git/hooks/post-commit" ]]; then
    check_ok "post-commit hook installed"
else
    check_warn "post-commit hook not installed"
fi

# ── DLL anti-pattern check ────────────────────────────────────
echo ""
echo "DLL anti-patterns:"
DLL="$HOME/SierraChart/ACS_Source/MES_AI_DataExport.cpp"
if [[ -f "$DLL" ]]; then
    if grep -q 'C:\\' "$DLL"; then
        check_fail "Windows paths found in DLL (AP-T03)"
    else
        check_ok "No Windows paths in DLL"
    fi
    if grep -v '//' "$DLL" | grep -qE 'std::max|std::min'; then
        check_fail "std::max/min found in DLL code (AP-T01)"
    else
        check_ok "No std::max/min in DLL code (comments OK)"
    fi
else
    check_warn "DLL not found, skipping anti-pattern check"
fi

# ── Summary ───────────────────────────────────────────────────
echo ""
printf "${CYAN}═══════════════════════════════════════════════════════════════${RESET}\n"
if (( FAIL == 0 )); then
    printf "${GREEN}  Environment OK${RESET}"
    if (( WARN > 0 )); then
        printf " ${YELLOW}(with warnings)${RESET}"
    fi
    echo ""
else
    printf "${RED}  Environment has issues — fix FAIL items above${RESET}\n"
fi
printf "${CYAN}═══════════════════════════════════════════════════════════════${RESET}\n"

exit $FAIL
