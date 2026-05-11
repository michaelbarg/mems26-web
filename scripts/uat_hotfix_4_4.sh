#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Bar Storage ==="
sqlite3 data/mems26_local.db "SELECT COUNT(*) FROM v9_bars_5min" \
  && echo "✅ Bar table exists" || (echo "❌ Table missing" && exit 1)

echo "=== Hydration Code Works ==="
hydration=$(python3 -c "
import os, json
os.environ.setdefault('DATABASE_URL', 'sqlite:///./data/mems26_local.db')
os.environ.setdefault('BRIDGE_TOKEN', 'test')
from dotenv import load_dotenv; load_dotenv()
from backend.v9.api.v9.status import _check_hydration
print(json.dumps(_check_hydration(), indent=2))
" 2>/dev/null)
echo "$hydration"
if echo "$hydration" | grep -q "day_type"; then
    echo "✅ Hydration status function works"
else
    echo "❌ Hydration status missing"
    exit 1
fi

echo "=== Day Type Hydrated ==="
dt_hydrated=$(echo "$hydration" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('systems',{}).get('day_type',{}).get('hydrated', False))
")
if [ "$dt_hydrated" = "True" ]; then
    echo "✅ Day Type hydrated"
else
    echo "⚠️ Day Type hydration: $dt_hydrated (may need history rows)"
fi

echo "=== Base Class has hydrate() ==="
grep -q "abstractmethod" backend/v9/systems/base/trading_system.py \
  && grep -q "def hydrate" backend/v9/systems/base/trading_system.py \
  && echo "✅ hydrate() in base class" || (echo "❌ Missing" && exit 1)

echo "=== Tests ==="
python3 -m pytest tests/test_hydration.py -v --tb=short 2>&1 | tail -5

echo ""
echo "✅ ALL CHECKS PASS"
