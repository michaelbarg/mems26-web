#!/usr/bin/env bash
# Stage: status_check — verify all services responding
set -euo pipefail
echo "=== Service Status ==="
for ep in health api/v9/health; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "localhost:8000/$ep" 2>/dev/null || echo "000")
  echo "  /$ep → $code"
  [ "$code" = "200" ] || { echo "FAIL: /$ep not 200"; exit 1; }
done
echo ""
echo "=== 6 Systems ==="
for sys in day_type five_min footprint woodies tpo killzone; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "localhost:8000/api/v9/$sys/current" 2>/dev/null || echo "000")
  echo "  $sys → $code"
  [ "$code" = "200" ] || { echo "FAIL: $sys not 200"; exit 1; }
done
echo ""
echo "✅ All systems responding"
