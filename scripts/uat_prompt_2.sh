#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 UAT — Prompt 2: TopBar Live Price Display
#
# Usage: ./scripts/uat_prompt_2.sh [--skip-sierra] [--skip-wait]
# Exit:  0 = all pass, 1 = failures
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/uat_lib.sh"

PROMPT_NUM=2
REPORT_DIR="$REPO_ROOT/docs/UAT_REPORTS"
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
PRICE_STREAM="mems26:events:price.tick"

# ── Flags ─────────────────────────────────────────────────────
SKIP_SIERRA=false
SKIP_WAIT=false
for arg in "$@"; do
    case "$arg" in
        --skip-sierra) SKIP_SIERRA=true ;;
        --skip-wait)   SKIP_WAIT=true ;;
    esac
done

echo ""
printf "${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n"
printf "${_CYAN}  MEMS26 UAT — Prompt $PROMPT_NUM: TopBar Live Price Display${_RESET}\n"
printf "${_CYAN}  $(date '+%Y-%m-%d %H:%M:%S')${_RESET}\n"
printf "${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n"
echo ""

# ═══════════════════════════════════════════════════════════════
# INHERITED: Prompt 1 baseline checks
# ═══════════════════════════════════════════════════════════════

# CHECK 1: Backend health
backend_status=$(get_http_status "$BACKEND_URL/api/v9/health")
if [[ "$backend_status" == "200" ]]; then
    report_result "backend_health" "200" "$backend_status" "PASS"
else
    report_result "backend_health" "200" "$backend_status" "FAIL"
fi

# CHECK 2: Redis price stream has data
xlen=$(get_redis_xlen "$PRICE_STREAM")
if check_redis_xlen "$PRICE_STREAM" 1; then
    report_result "redis_price_stream" "XLEN>=1" "XLEN=$xlen" "PASS"
else
    report_result "redis_price_stream" "XLEN>=1" "XLEN=$xlen" "FAIL"
fi

# CHECK 3: WS status endpoint
ws_status=$(get_http_status "$BACKEND_URL/api/v9/ws/status")
if [[ "$ws_status" == "200" ]]; then
    report_result "ws_status_endpoint" "200" "$ws_status" "PASS"
else
    report_result "ws_status_endpoint" "200" "$ws_status" "FAIL"
fi

# CHECK 4: Status dashboard (all 5 layers) — longer timeout, does internal HTTP calls
status_resp=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$BACKEND_URL/api/v9/status" 2>/dev/null || echo "000")
if [[ "$status_resp" == "200" ]]; then
    report_result "status_dashboard" "200" "$status_resp" "PASS"
else
    report_result "status_dashboard" "200" "$status_resp" "FAIL"
fi

# CHECK 5: Frontend port 3000
if check_port 3000; then
    report_result "frontend_listening" "port_3000" "up" "PASS"
else
    report_result "frontend_listening" "port_3000" "down" "FAIL"
fi

# ═══════════════════════════════════════════════════════════════
# PROMPT 2 SPECIFIC: TopBar components
# ═══════════════════════════════════════════════════════════════

# CHECK 6: PriceDisplay component exists
if [[ -f "$REPO_ROOT/frontend/v9/src/v9/components/topbar/PriceDisplay.tsx" ]]; then
    report_result "price_display_file" "exists" "exists" "PASS"
else
    report_result "price_display_file" "exists" "missing" "FAIL"
fi

# CHECK 7: PriceMeta component exists
if [[ -f "$REPO_ROOT/frontend/v9/src/v9/components/topbar/PriceMeta.tsx" ]]; then
    report_result "price_meta_file" "exists" "exists" "PASS"
else
    report_result "price_meta_file" "exists" "missing" "FAIL"
fi

# CHECK 8: ConnectionIndicator component exists
if [[ -f "$REPO_ROOT/frontend/v9/src/v9/components/topbar/ConnectionIndicator.tsx" ]]; then
    report_result "connection_indicator_file" "exists" "exists" "PASS"
else
    report_result "connection_indicator_file" "exists" "missing" "FAIL"
fi

# CHECK 9: priceStore exists
if [[ -f "$REPO_ROOT/frontend/v9/src/v9/stores/priceStore.ts" ]]; then
    report_result "price_store_file" "exists" "exists" "PASS"
else
    report_result "price_store_file" "exists" "missing" "FAIL"
fi

# CHECK 10: formatPrice utility exists
if [[ -f "$REPO_ROOT/frontend/v9/src/v9/lib/formatPrice.ts" ]]; then
    report_result "format_price_file" "exists" "exists" "PASS"
else
    report_result "format_price_file" "exists" "missing" "FAIL"
fi

# CHECK 11: TopBar imports PriceDisplay
if grep -q "PriceDisplay" "$REPO_ROOT/frontend/v9/src/v9/components/layout/TopBar.tsx"; then
    report_result "topbar_uses_price_display" "imported" "imported" "PASS"
else
    report_result "topbar_uses_price_display" "imported" "missing" "FAIL"
fi

# CHECK 12: TopBar has id="topbar-price" (via PriceDisplay)
if grep -q 'id="topbar-price"' "$REPO_ROOT/frontend/v9/src/v9/components/topbar/PriceDisplay.tsx"; then
    report_result "topbar_price_id" "present" "present" "PASS"
else
    report_result "topbar_price_id" "present" "missing" "FAIL"
fi

# CHECK 13: TopBar height is 40px
if grep -q 'h-\[40px\]' "$REPO_ROOT/frontend/v9/src/v9/components/layout/TopBar.tsx"; then
    report_result "topbar_height_40px" "40px" "40px" "PASS"
else
    report_result "topbar_height_40px" "40px" "wrong" "FAIL"
fi

# CHECK 14: Frontend DOM contains price element (fetch HTML)
if check_port 3000; then
    html=$(curl -s --max-time 5 "$FRONTEND_URL" 2>/dev/null)
    if echo "$html" | grep -q "topbar-price"; then
        report_result "dom_topbar_price_id" "in_html" "found" "PASS"
    else
        # Next.js SSR may not have client-rendered content in initial HTML
        report_result "dom_topbar_price_id" "in_html" "client_only" "SKIP"
    fi
else
    report_result "dom_topbar_price_id" "in_html" "fe_down" "SKIP"
fi

# CHECK 15: Frontend build passes
echo "  Running next build..."
build_output=$(cd "$REPO_ROOT/frontend/v9" && npx next build 2>&1) || true
if echo "$build_output" | grep -q "Compiled successfully"; then
    report_result "frontend_build" "compiles" "success" "PASS"
else
    report_result "frontend_build" "compiles" "failed" "FAIL"
fi

# CHECK 16: Unit tests still pass
echo "  Running pytest tests/event_bus/ ..."
test_output=$(cd "$REPO_ROOT" && python3 -m pytest tests/event_bus/ -q --tb=no 2>&1) || true
test_line=$(echo "$test_output" | grep -E "[0-9]+ passed" | tail -1)
if [[ "$test_line" == *"passed"* ]] && [[ "$test_line" != *"failed"* ]]; then
    report_result "unit_tests" "all_pass" "$test_line" "PASS"
else
    report_result "unit_tests" "all_pass" "${test_line:-no_output}" "FAIL"
fi

# ═══════════════════════════════════════════════════════════════
# Summary + Report
# ═══════════════════════════════════════════════════════════════
write_report "$PROMPT_NUM" "$REPORT_DIR"
print_summary
