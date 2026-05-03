#!/bin/bash

# Auto-load environment if not already loaded (used for future psql/backup scripts)
if [ -z "$DATABASE_URL" ] && [ -f "$HOME/.mems26_env" ]; then
    source "$HOME/.mems26_env"
fi

BACKEND_URL=${BACKEND_URL:-https://mems26-web.onrender.com}

echo "=== MEMS26 Daily Health Check ==="
echo "Date: $(date)"
echo ""

echo "--- Backend ---"
curl -s -o /dev/null -w "Backend: %{http_code}\n" "$BACKEND_URL/health" || echo "Backend: DOWN"

echo ""
echo "--- Frontend ---"
curl -s -o /dev/null -w "Frontend: %{http_code}\n" https://blasttt.com || echo "Frontend: DOWN"

echo ""
echo "--- Bridge (local) ---"
if pgrep -f json_bridge.py > /dev/null; then
    echo "Bridge: RUNNING"
    tail -5 /tmp/bridge.log 2>/dev/null
else
    echo "Bridge: STOPPED"
fi

echo ""
echo "--- DB Recent Activity (via Backend API) ---"

# Last Trade
HTTP_CODE=$(curl -s -o /tmp/dc_trades.json -w "%{http_code}" --max-time 10 "$BACKEND_URL/trades?limit=1")
if [ "$HTTP_CODE" != "200" ]; then
    echo "  ⚠️ /trades: HTTP $HTTP_CODE"
else
    python3 -c "
import json
with open('/tmp/dc_trades.json') as f:
    data = json.load(f)
if isinstance(data, dict):
    data = data.get('trades', data.get('data', []))
if not data:
    print('Last Trade: NONE in DB')
else:
    t = data[0]
    ts = t.get('created_at', t.get('entry_ts', 'unknown'))
    print(f'Last Trade: {ts}')
"
fi

# Today Activity
HTTP_CODE=$(curl -s -o /tmp/dc_today.json -w "%{http_code}" --max-time 10 "$BACKEND_URL/analytics/setups/today_summary")
if [ "$HTTP_CODE" != "200" ]; then
    echo "  ⚠️ /analytics/setups/today_summary: HTTP $HTTP_CODE"
else
    python3 -c "
import json
with open('/tmp/dc_today.json') as f:
    d = json.load(f)
total = d.get('total_setups', d.get('total', 0))
closed = d.get('closed', d.get('closed_setups', 0))
wr = d.get('win_rate', d.get('win_rate_pct', 0))
pnl = d.get('total_pnl_net_usd', d.get('pnl', d.get('total_pnl', 0)))
print(f'Today: {total} setups, {closed} closed, WR {wr}%, PnL \${pnl:.2f}')
"
fi

# Recent Days
HTTP_CODE=$(curl -s -o /tmp/dc_daily.json -w "%{http_code}" --max-time 10 "$BACKEND_URL/analytics/daily?days=7")
if [ "$HTTP_CODE" != "200" ]; then
    echo "  ⚠️ /analytics/daily: HTTP $HTTP_CODE"
else
    echo "Last 7 days:"
    python3 -c "
import json
with open('/tmp/dc_daily.json') as f:
    data = json.load(f)
if isinstance(data, dict):
    data = data.get('days', data.get('data', []))
for day in data:
    dt = day.get('date', day.get('day', '?'))
    n = day.get('count', day.get('setups', day.get('total_setups', 0)))
    print(f'  {dt}: {n} setups')
"
fi

# Cleanup temp files
rm -f /tmp/dc_trades.json /tmp/dc_today.json /tmp/dc_daily.json

echo ""
echo "=== Check Complete ==="
