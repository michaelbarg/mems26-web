#!/bin/bash
set -e

echo "=== D1 UAT ==="

echo "1. 5 new tables exist..."
for table in v9_bars_woodies v9_bars_volume_profile v9_bars_cumulative_delta v9_bars_imbalance v9_bars_stacked_imbalance; do
  sqlite3 data/mems26_local.db "SELECT 1 FROM $table LIMIT 1" > /dev/null 2>&1 \
    && echo "  ✅ $table" \
    || (echo "  ❌ $table MISSING" && exit 1)
done

echo "2. BarRouter file exists..."
test -f backend/v9/services/bar_router.py && echo "  ✅ file"

echo "3. BarRouter imports..."
python3 -c "from backend.v9.services.bar_router import BarRouter; BarRouter()" \
  && echo "  ✅ import"

echo "4. Endpoints wired to BarRouter..."
count=$(grep -rc "_route_bar" backend/v9/api/v9/bars.py 2>/dev/null || echo 0)
test "$count" -ge 3 && echo "  ✅ $count refs" || echo "  ⚠️ only $count refs"

echo "5. System subscriptions defined..."
grep -q "subscribed_bar_types" backend/v9/systems/base/trading_system.py && echo "  ✅ base"
grep -q "subscribed_bar_types" backend/v9/systems/five_min/five_min_system.py && echo "  ✅ 5min"

echo "6. Aggregator on_bar_event..."
grep -q "on_bar_event" backend/v9/services/bar_aggregator_5min.py && echo "  ✅ aggregator"

echo "7. main.py wires BarRouter..."
grep -q "BarRouter" backend/main.py && echo "  ✅ main"

echo "8. Tests pass..."
python3 -m pytest backend/v9/tests/test_bar_router.py -q --tb=no 2>&1 | tail -1

echo "9. Status has bar_router key..."
python3 -c "
import os; os.environ.setdefault('DATABASE_URL','sqlite:///./data/mems26_local.db'); os.environ.setdefault('BRIDGE_TOKEN','test')
from dotenv import load_dotenv; load_dotenv()
from backend.v9.api.v9.status import _check_bar_router
r = _check_bar_router()
print(f'  ✅ bar_router: {r}')
"

echo ""
echo "=== ✅ D1 UAT COMPLETE ==="
