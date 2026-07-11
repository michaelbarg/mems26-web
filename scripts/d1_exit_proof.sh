#!/bin/bash
# D1-EXIT Proof Script — runs on SIM after Michael's Sierra reload.
# Validates: BUY 2 → EXIT 1 → FLATTEN_ACCOUNT → sierra_state.json updates.
#
# Prerequisites:
#   - Sierra running with new DLL (post Remote Build + reload)
#   - Backend running (port 8000)
#   - SIM account configured
#
# Usage: bash scripts/d1_exit_proof.sh

set -e
cd /Users/michael/Downloads/mems26_web_git

TOKEN="${BRIDGE_TOKEN:-michael-mems26-2026}"
BASE="http://localhost:8000"
STATE_FILE="$HOME/SierraChart_Data/v9_export/sierra_state.json"

echo "═══ D1-EXIT Proof Script ═══"
echo "$(date)"
echo ""

# 1. Pre-check: backend is running
echo "1. Pre-check: backend health..."
curl -sf "$BASE/health" > /dev/null || { echo "FAIL: backend not responding"; exit 1; }
echo "   ✅ Backend OK"

# 2. Record initial sierra_state.json
echo "2. Initial sierra_state.json..."
if [ -f "$STATE_FILE" ]; then
    cat "$STATE_FILE" | python3 -m json.tool 2>/dev/null || echo "(not valid JSON yet)"
else
    echo "   ⚠ File doesn't exist yet — will check after operations"
fi

# 3. Submit BUY 2 (market order on SIM)
echo ""
echo "3. BUY 2 contracts (SIM)..."
curl -sf -X POST "$BASE/api/v9/trade-commands/command" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"action":"BUY","contracts":2,"context":{"mode":"demo","test":"d1_exit_proof"}}' | python3 -m json.tool
echo "   Waiting 5s for DLL to process..."
sleep 5

# 4. Check sierra_state.json — should show position_qty=2
echo ""
echo "4. sierra_state.json after BUY 2..."
if [ -f "$STATE_FILE" ]; then
    cat "$STATE_FILE" | python3 -m json.tool
    echo "   Expected: position_qty=2"
else
    echo "   ⚠ State file not found"
fi

# 5. Submit EXIT 1 (partial exit)
echo ""
echo "5. EXIT 1 contract..."
curl -sf -X POST "$BASE/api/v9/trade-commands/command" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"action":"SELL","contracts":1,"context":{"mode":"demo","test":"d1_exit_proof_partial"}}' | python3 -m json.tool
echo "   Waiting 5s for DLL to process..."
sleep 5

# 6. Check sierra_state.json — should show position_qty=1
echo ""
echo "6. sierra_state.json after EXIT 1..."
if [ -f "$STATE_FILE" ]; then
    cat "$STATE_FILE" | python3 -m json.tool
    echo "   Expected: position_qty=1"
else
    echo "   ⚠ State file not found"
fi

# 7. Submit FLATTEN_ACCOUNT
echo ""
echo "7. FLATTEN_ACCOUNT..."
curl -sf -X POST "$BASE/api/v9/trade-commands/command" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"action":"FLATTEN_ACCOUNT","context":{"mode":"demo","test":"d1_exit_proof_flatten"}}' | python3 -m json.tool
echo "   Waiting 5s for DLL to process..."
sleep 5

# 8. Final check — position should be 0
echo ""
echo "8. Final sierra_state.json..."
if [ -f "$STATE_FILE" ]; then
    cat "$STATE_FILE" | python3 -m json.tool
    echo "   Expected: position_qty=0"
else
    echo "   ⚠ State file not found"
fi

# 9. Check DLL result
echo ""
echo "9. Last trade_result.json..."
RESULT="$HOME/SierraChart_Data/v9_export/signals/trade_result.json"
if [ -f "$RESULT" ]; then
    cat "$RESULT" | python3 -m json.tool
else
    echo "   ⚠ No result file"
fi

echo ""
echo "═══ Proof complete — review outputs above ═══"
echo "Timestamp: $(date)"
