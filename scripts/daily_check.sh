#!/bin/bash
echo "=== MEMS26 Daily Health Check ==="
echo "Date: $(date)"
echo ""

echo "--- Backend ---"
curl -s -o /dev/null -w "Backend: %{http_code}\n" https://mems26-web.onrender.com/health || echo "Backend: DOWN"

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
echo "--- DB Recent Activity ---"
python3 << 'PYEOF'
import os, psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

cur.execute("""
  SELECT MAX(created_at),
         EXTRACT(EPOCH FROM (NOW() - MAX(created_at)))/60 as min_ago
  FROM setup_attempts
""")
r = cur.fetchone()
print(f"Last setup: {r[0]} ({r[1]:.0f} min ago)")

cur.execute("""
  SELECT COUNT(*)
  FROM setup_attempts
  WHERE created_at >= CURRENT_DATE
""")
print(f"Today's setups: {cur.fetchone()[0]}")

cur.execute("""
  SELECT COUNT(*), COALESCE(SUM(pnl_usd), 0)
  FROM trades
  WHERE entry_ts >= EXTRACT(EPOCH FROM CURRENT_DATE)
""")
r = cur.fetchone()
print(f"Today's trades: {r[0]}, PnL: ${r[1]:.2f}")

cur.close()
conn.close()
PYEOF

echo ""
echo "=== Check Complete ==="
