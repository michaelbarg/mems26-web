#!/bin/bash
# MEMS26 Stop All — cleanly stops Bridge + Backend + Frontend
# Usage: bash scripts/stop_all.sh  OR  mems-stop

GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅${NC} $1"; }
warn() { echo -e "${YELLOW}🟡${NC} $1"; }

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "   MEMS26 Stop All — $(date '+%H:%M:%S')"
echo "═══════════════════════════════════════════════════════════════"
echo ""

for SESSION in mems26_frontend mems26_backend mems26_bridge; do
  if screen -ls 2>&1 | grep -q "$SESSION"; then
    screen -S "$SESSION" -X quit 2>/dev/null
    sleep 1
    ok "Stopped screen: $SESSION"
  else
    warn "Screen $SESSION not running"
  fi
done

sleep 2
for PROC in "next dev" "next-server" "uvicorn backend" "json_bridge.py"; do
  if pgrep -f "$PROC" > /dev/null 2>&1; then
    pkill -f "$PROC" 2>/dev/null
    sleep 1
    pgrep -f "$PROC" > /dev/null 2>&1 && pkill -9 -f "$PROC" 2>/dev/null
    ok "Killed: $PROC"
  fi
done

echo ""
ok "All MEMS26 services stopped"
echo "  Start again: mems-start"
echo "═══════════════════════════════════════════════════════════════"
