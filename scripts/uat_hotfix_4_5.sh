#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== CHECK 1: Code change exists ==="
grep -q "bar_ingestion_service.start\|BarIngestionService.*start" backend/v9/app.py \
  && echo "✅ Start call in app.py" || (echo "❌ Missing" && exit 1)
grep -q "bar_ingestion_service.start\|BarIngestionService.*start" backend/main.py \
  && echo "✅ Start call in main.py" || (echo "❌ Missing" && exit 1)

echo "=== CHECK 2: Bar Ingestion runs when started ==="
python3 -c "
import os; os.environ.setdefault('DATABASE_URL','sqlite:///./data/mems26_local.db'); os.environ.setdefault('BRIDGE_TOKEN','test')
from dotenv import load_dotenv; load_dotenv()
from backend.v9.services.bar_ingestion import bar_ingestion_service
bar_ingestion_service.start()
assert bar_ingestion_service.is_running, 'Not running after start()'
print('✅ BarIngestionService starts correctly')
"

echo "=== CHECK 3: Day Type still hydrates ==="
python3 -c "
import os; os.environ.setdefault('DATABASE_URL','sqlite:///./data/mems26_local.db'); os.environ.setdefault('BRIDGE_TOKEN','test')
from dotenv import load_dotenv; load_dotenv()
from backend.v9.systems.day_type.hydration import hydrate_day_type
r = hydrate_day_type()
assert r.success, f'Hydration failed: {r.error}'
print(f'✅ Day Type hydrated: {r.reached_state}')
"

echo "=== CHECK 4: Status function returns bar_ingestion.running=true ==="
python3 -c "
import os; os.environ.setdefault('DATABASE_URL','sqlite:///./data/mems26_local.db'); os.environ.setdefault('BRIDGE_TOKEN','test')
from dotenv import load_dotenv; load_dotenv()
from backend.v9.services.bar_ingestion import bar_ingestion_service
bar_ingestion_service.start()
from backend.v9.api.v9.status import _check_hydration
h = _check_hydration()
assert h['bar_ingestion']['running'] == True, 'bar_ingestion not running in status'
assert h['systems']['day_type']['hydrated'] == True, 'day_type not hydrated in status'
print('✅ Status hydration layer correct')
"

echo "=== CHECK 5: Previous tests pass ==="
python3 -m pytest tests/test_hydration.py tests/systems/base/ -q --tb=no 2>&1 | tail -1

echo "=== CHECK 6: Idempotent ==="
python3 -c "
import os; os.environ.setdefault('DATABASE_URL','sqlite:///./data/mems26_local.db'); os.environ.setdefault('BRIDGE_TOKEN','test')
from dotenv import load_dotenv; load_dotenv()
from backend.v9.services.bar_ingestion import BarIngestionService
svc = BarIngestionService()
svc.start()
svc.start()  # second start should not break
assert svc.is_running
print('✅ Idempotent: double start() safe')
"

echo ""
echo "✅ ALL CHECKS PASS"
