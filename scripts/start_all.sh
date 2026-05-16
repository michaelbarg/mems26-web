#!/bin/bash
# MEMS26 Start All — launches Bridge + Backend + Frontend in screen sessions
# Usage: bash scripts/start_all.sh  OR  mems-start

set +e
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "   MEMS26 Start All — $(date '+%H:%M:%S')"
echo "═══════════════════════════════════════════════════════════════"
echo ""

GREEN='\033[0;32m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅${NC} $1"; }
fail() { echo -e "${RED}🔴${NC} $1"; }
info() { echo -e "${BLUE}ℹ️${NC}  $1"; }

cd /Users/michael/Downloads/mems26_web_git
[ -f .env ] && set -a && source .env && set +a

# ═══ BRIDGE ═══
echo -e "${BLUE}━━━ Bridge ━━━${NC}"
if pgrep -f "json_bridge.py" > /dev/null 2>&1; then
  ok "Bridge already running (PID $(pgrep -f json_bridge.py | head -1))"
else
  cat > /tmp/start_bridge.sh << 'BRIDGE_EOF'
#!/bin/bash
cd /Users/michael/Downloads/mems26_web_git
[ -f .env ] && set -a && source .env && set +a
export V9_EXPORT_DIR="${V9_EXPORT_DIR:-/Users/michael/SierraChart_Data/v9_export}"
export CLOUD_URL="${CLOUD_URL:-https://mems26-web.onrender.com}"
export BRIDGE_TOKEN="${BRIDGE_TOKEN:-michael-mems26-2026}"
export V9_DISABLE_WATCHDOG="${V9_DISABLE_WATCHDOG:-1}"
echo "=== Bridge starting at $(date) ===" >> /tmp/bridge.log
exec python3 bridge/json_bridge.py 2>&1 | tee -a /tmp/bridge.log
BRIDGE_EOF
  chmod +x /tmp/start_bridge.sh
  screen -dmS mems26_bridge bash /tmp/start_bridge.sh
  sleep 3
  if pgrep -f "json_bridge.py" > /dev/null 2>&1; then
    ok "Bridge started (PID $(pgrep -f json_bridge.py | head -1))"
  else
    fail "Bridge failed — check /tmp/bridge.log"
  fi
fi
echo ""

# ═══ BACKEND ═══
echo -e "${BLUE}━━━ Backend ━━━${NC}"
if pgrep -f "uvicorn backend" > /dev/null 2>&1; then
  ok "Backend already running (port 8000)"
else
  screen -dmS mems26_backend bash -c "cd /Users/michael/Downloads/mems26_web_git && [ -f .env ] && set -a && source .env && set +a; python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 2>&1 | tee /tmp/backend.log"
  sleep 5
  if pgrep -f "uvicorn backend" > /dev/null 2>&1; then
    ok "Backend started (port 8000)"
  else
    fail "Backend failed — check /tmp/backend.log"
  fi
fi
echo ""

# ═══ FRONTEND ═══
echo -e "${BLUE}━━━ Frontend ━━━${NC}"
if pgrep -f "next dev" > /dev/null 2>&1; then
  ok "Frontend already running (port 3000)"
else
  screen -dmS mems26_frontend bash -c "cd /Users/michael/Downloads/mems26_web_git/frontend/v9 && npm run dev 2>&1 | tee /tmp/frontend.log"
  info "Waiting for Next.js to compile..."
  for i in $(seq 1 10); do
    sleep 3
    if curl -s -m 2 http://localhost:3000 > /dev/null 2>&1; then
      ok "Frontend ready (port 3000)"
      break
    fi
    [ "$i" -eq 10 ] && fail "Frontend slow — check /tmp/frontend.log"
  done
fi
echo ""

echo -e "${BLUE}━━━ Stack Ready ━━━${NC}"
echo "  📺 Dashboard:    http://localhost:3000"
echo "  📊 API:          http://localhost:8000/docs"
echo ""
echo "  Status:  mems       Stop:  mems-stop"
echo "═══════════════════════════════════════════════════════════════"
