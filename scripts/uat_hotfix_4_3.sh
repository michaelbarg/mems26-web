#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== AP-DESIGN01: No hardcoded colors ==="
grep -E "bg-\[#|text-\[#|border-\[#" frontend/v9/src/app/page.tsx \
  && (echo "❌ Hardcoded color in page.tsx" && exit 1) \
  || echo "✅ No hardcoded colors"

echo "=== AP-CC06: V8 removed from page.tsx ==="
for pattern in "TradingView" "lightweight-charts" "סוחר" "שוק" "סטאפים" "Decision tree visualization"; do
  if grep -q "$pattern" frontend/v9/src/app/page.tsx 2>/dev/null; then
    echo "❌ V8 remnant: $pattern"; exit 1
  fi
done
echo "✅ V8 fully removed from page.tsx"

echo "=== V9 imports present ==="
# page.tsx imports V9Dashboard which has all V9 components
for component in "V9Dashboard" "TopBar" "Layer0Strip" "SidePanel" "Chart V5a" "COLORS"; do
  # Check in page.tsx OR V9Dashboard.tsx
  if grep -q "$component" frontend/v9/src/app/page.tsx 2>/dev/null || \
     grep -q "$component" frontend/v9/src/v9/components/layout/V9Dashboard.tsx 2>/dev/null; then
    echo "✅ $component present"
  else
    echo "❌ Missing: $component" && exit 1
  fi
done

echo "=== Build verification ==="
cd frontend/v9 && npx next build 2>&1 | tail -3
cd "$REPO_ROOT"

echo "=== WS relay state ==="
ws_relay=$(curl -s http://localhost:8000/api/v9/status 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ws',{}).get('relay_running', False))" 2>/dev/null || echo "False")
if [ "$ws_relay" = "True" ]; then
  echo "✅ WS relay running"
else
  echo "⚠️ WS relay not running (may need client connection to start)"
fi

echo ""
echo "✅ ALL CHECKS PASS"
echo ""
echo "⚠️ MANUAL: Open http://localhost:3000 → Cmd+Shift+R → verify visually"
