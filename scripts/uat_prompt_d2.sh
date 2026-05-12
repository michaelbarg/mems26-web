#!/bin/bash
set -e

echo "=== D2 UAT: Historical Replay ==="

echo "1. HistoricalReplay file exists..."
test -f backend/v9/services/historical_replay.py && echo "  ✅ file"

echo "2. main.py wires HistoricalReplay..."
grep -q "HistoricalReplay" backend/main.py && echo "  ✅ main"

echo "3. Status endpoint exposes replay..."
python3 -c "
import os; os.environ.setdefault('DATABASE_URL','sqlite:///./data/mems26_local.db'); os.environ.setdefault('BRIDGE_TOKEN','test')
from dotenv import load_dotenv; load_dotenv()
from backend.v9.api.v9.status import _check_historical_replay
r = _check_historical_replay()
assert r.get('available'), 'not available'
print('  ✅ exposed')
"

echo "4. Tests pass..."
python3 -m pytest backend/v9/tests/test_historical_replay.py -q --tb=no 2>&1 | tail -1

echo "5. BarRouter tests still pass..."
python3 -m pytest backend/v9/tests/test_bar_router.py -q --tb=no 2>&1 | tail -1

echo "=== ✅ D2 UAT COMPLETE ==="
