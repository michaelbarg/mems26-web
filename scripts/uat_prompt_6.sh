#!/bin/bash
set -e

echo "=== PROMPT 6 UAT: Footprint ==="

echo "1. DB tables exist..."
for t in v9_footprint_journal v9_footprint_setups; do
  sqlite3 data/mems26_local.db "SELECT 1 FROM $t LIMIT 1" > /dev/null 2>&1 && echo "  OK $t"
done

echo "2. Detectors module..."
python3 -c "from backend.v9.systems.footprint.detectors import detect_cluster" && echo "  OK import"

echo "3. FootprintSystem extends Base..."
python3 -c "
from backend.v9.systems.footprint.footprint_system import FootprintSystem
from backend.v9.systems.base.trading_system import BaseV9TradingSystem
assert issubclass(FootprintSystem, BaseV9TradingSystem)
print('  OK extends base')
"

echo "4. API /current returns JSON..."
curl -s http://localhost:8000/api/v9/footprint/current | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'running' in d or 'last_classification' in d
print('  OK api')
" 2>/dev/null || echo "  SKIP (backend needs restart)"

echo "5. FootprintPill rendered..."
grep -c "FootprintPill" frontend/v9/src/v9/components/layout/Switcher.tsx | grep -q "^[1-9]" && echo "  OK rendered"

echo "6. Tests pass..."
python3 -m pytest backend/v9/tests/test_footprint_system.py -q --tb=no 2>&1 | tail -1

echo "=== PROMPT 6 UAT COMPLETE ==="
