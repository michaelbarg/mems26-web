#!/bin/bash
# MEMS26 Status Check — run anytime to see system health
# Usage: bash scripts/check_status.sh
# Alias: mems (after adding to ~/.zshrc)

set +e
clear
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "   MEMS26 Status Check — $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════════"
echo ""

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅${NC} $1"; }
fail() { echo -e "${RED}🔴${NC} $1"; }
warn() { echo -e "${YELLOW}🟡${NC} $1"; }
info() { echo -e "${BLUE}ℹ️${NC}  $1"; }

cd /Users/michael/Downloads/mems26_web_git 2>/dev/null

# ═══ 1. SIERRA CHART
echo -e "${BLUE}━━━ Sierra Chart ━━━${NC}"
if pgrep -i Sierra > /dev/null 2>&1; then
  ok "Sierra running"
else
  info "Sierra not running (normal when market closed)"
fi

NEWEST_JSON=$(ls -t ~/SierraChart/Data/v9_export/*.json 2>/dev/null | head -1)
if [ -n "$NEWEST_JSON" ]; then
  AGE=$(($(date +%s) - $(stat -f %m "$NEWEST_JSON" 2>/dev/null || echo 0)))
  if [ $AGE -lt 30 ]; then
    ok "JSON exports fresh (${AGE}s)"
  elif [ $AGE -lt 600 ]; then
    warn "JSON exports ${AGE}s old"
  else
    info "JSON exports $((AGE/3600))h old (market closed)"
  fi
fi
echo ""

# ═══ 2. BRIDGE
echo -e "${BLUE}━━━ Bridge ━━━${NC}"
BRIDGE_PIDS=$(pgrep -f "json_bridge.py" 2>/dev/null | wc -l | tr -d ' ')
if [ "$BRIDGE_PIDS" = "1" ]; then
  PID=$(pgrep -f "json_bridge.py")
  RAM=$(ps -o rss= -p $PID 2>/dev/null | awk '{printf "%.0f MB", $1/1024}')
  ok "Bridge running (PID $PID, $RAM)"
elif [ "$BRIDGE_PIDS" = "0" ]; then
  fail "Bridge NOT running"
  echo "    Fix: screen -dmS mems26_bridge bash /tmp/start_bridge.sh"
else
  fail "Multiple bridges ($BRIDGE_PIDS) — kill all + restart"
fi

if screen -ls 2>&1 | grep -q "mems26_bridge"; then
  ok "Bridge in screen (survives terminal close)"
else
  warn "Bridge not in screen"
fi

if [ -f /tmp/bridge.log ]; then
  LAST_TS=$(tail -1 /tmp/bridge.log | grep -oE "2026-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}" | tail -1)
  if [ -n "$LAST_TS" ]; then
    LAST_EPOCH=$(date -j -f "%Y-%m-%d %H:%M:%S" "$LAST_TS" "+%s" 2>/dev/null)
    NOW_EPOCH=$(date "+%s")
    if [ -n "$LAST_EPOCH" ]; then
      LOG_AGE=$((NOW_EPOCH - LAST_EPOCH))
      if [ $LOG_AGE -lt 120 ]; then
        ok "Bridge log fresh (${LOG_AGE}s)"
      else
        info "Bridge log $((LOG_AGE/60))min old"
      fi
    fi
  fi
  # Show latest heartbeat
  HB=$(grep "\[heartbeat\]" /tmp/bridge.log | tail -1)
  [ -n "$HB" ] && info "$(echo $HB | sed 's/.*\[heartbeat\] //')"
fi
echo ""

# ═══ 3. BACKEND
echo -e "${BLUE}━━━ Backend (localhost:8000) ━━━${NC}"
BACKEND_HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 3 http://localhost:8000/health 2>/dev/null)
V9_HEALTH=$(curl -s -m 3 http://localhost:8000/api/v9/health 2>/dev/null)
if pgrep -f "uvicorn backend" > /dev/null 2>&1 || [ "$BACKEND_HEALTH_CODE" = "200" ]; then
  ok "Backend running"
  if echo "$V9_HEALTH" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
    ok "V9 routes mounted"
  else
    warn "Backend up but V9 not mounted"
  fi
else
  fail "Backend NOT running"
  echo "    Fix: source .env && nohup python3 -m uvicorn backend.main:app --port 8000 > /tmp/backend.log 2>&1 &"
fi
echo ""

# ═══ 4. FRONTEND
echo -e "${BLUE}━━━ Frontend (localhost:3000) ━━━${NC}"
if pgrep -f "next dev" > /dev/null 2>&1; then
  ok "Frontend running"
  if curl -s -m 3 http://localhost:3000 2>/dev/null | grep -q "<html"; then
    ok "localhost:3000 serving HTML"
  else
    fail "Frontend process alive but not serving"
  fi
else
  fail "Frontend NOT running"
  echo "    Fix: cd frontend/v9 && screen -dmS mems26_frontend bash -c 'npm run dev 2>&1 | tee /tmp/frontend.log'"
fi

if screen -ls 2>&1 | grep -q "mems26_frontend"; then
  ok "Frontend in screen"
fi
echo ""

# ═══ 5. RENDER
echo -e "${BLUE}━━━ Render (production) ━━━${NC}"
RENDER_HEALTH=$(curl -s -m 5 https://mems26-web.onrender.com/health 2>/dev/null)
if [ -n "$RENDER_HEALTH" ]; then
  ok "Render reachable"
  if echo "$RENDER_HEALTH" | grep -q "v9_mounted"; then
    ok "V9 deployed on Render"
  else
    warn "V9 NOT deployed (still V8)"
  fi
else
  fail "Render unreachable"
fi
echo ""

# ═══ 6. REDIS
echo -e "${BLUE}━━━ Redis (Upstash) ━━━${NC}"
[ -f .env ] && set -a && source .env && set +a 2>/dev/null
if [ -n "$UPSTASH_REDIS_REST_URL" ] && [ -n "$UPSTASH_REDIS_REST_TOKEN" ]; then
  REDIS_RESP=$(curl -s -m 3 -X POST -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
    -H "Content-Type: application/json" \
    -d '["KEYS","mems26:v9:*"]' "$UPSTASH_REDIS_REST_URL" 2>/dev/null)
  KEY_COUNT=$(echo "$REDIS_RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('result',[])))" 2>/dev/null || echo 0)
  if [ "$KEY_COUNT" -gt 0 ] 2>/dev/null; then
    ok "Redis: $KEY_COUNT V9 keys"
  else
    warn "Redis: 0 V9 keys"
  fi
  unset UPSTASH_REDIS_REST_TOKEN
else
  fail "Redis credentials missing"
fi
echo ""

# ═══ 7. GIT
echo -e "${BLUE}━━━ Git ━━━${NC}"
BRANCH=$(git branch --show-current 2>/dev/null)
info "Branch: $BRANCH"
UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ "$UNCOMMITTED" = "0" ]; then
  ok "Working tree clean"
else
  warn "$UNCOMMITTED uncommitted changes"
fi
info "Last: $(git log -1 --format='%h %s' 2>/dev/null)"
echo ""

# ═══ LINKS
echo -e "${BLUE}━━━ Quick Links ━━━${NC}"
echo "  📺 Dashboard:   http://localhost:3000"
echo "  📊 API docs:    http://localhost:8000/docs"
echo "  🌐 Production:  https://mems26-web.onrender.com"
echo ""
echo -e "${BLUE}━━━ Commands ━━━${NC}"
echo "  Bridge log:     screen -r mems26_bridge  (Ctrl+A,D detach)"
echo "  Frontend log:   screen -r mems26_frontend"
echo "  Restart bridge: screen -S mems26_bridge -X quit && screen -dmS mems26_bridge bash /tmp/start_bridge.sh"
echo ""
echo "═══════════════════════════════════════════════════════════════"
