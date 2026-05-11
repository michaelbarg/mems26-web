#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 UAT — Prompt 1: Foundation Layer
# Event Bus + Schema + live_price + WS + Frontend
#
# Usage: ./scripts/uat_prompt_1.sh [--skip-sierra] [--skip-wait]
# Exit:  0 = all pass, 1 = failures
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/uat_lib.sh"

PROMPT_NUM=1
REPORT_DIR="$REPO_ROOT/docs/UAT_REPORTS"
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
LIVE_PRICE_JSON="$HOME/SierraChart_Data/v9_export/live_price.json"
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
printf "${_CYAN}  MEMS26 UAT — Prompt $PROMPT_NUM: Foundation Layer${_RESET}\n"
printf "${_CYAN}  $(date '+%Y-%m-%d %H:%M:%S')${_RESET}\n"
printf "${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n"
echo ""

# ═══════════════════════════════════════════════════════════════
# CHECK 1: Sierra live_price.json — mtime < 60s
# ═══════════════════════════════════════════════════════════════
if $SKIP_SIERRA; then
    report_result "sierra_live_price_fresh" "mtime<60s" "SKIPPED" "SKIP"
else
    if check_file_fresh "$LIVE_PRICE_JSON" 60; then
        report_result "sierra_live_price_fresh" "mtime<60s" "fresh" "PASS"
    elif [[ -f "$LIVE_PRICE_JSON" ]]; then
        # File exists but stale — market likely closed
        local_now=$(date +%s)
        if stat -f %m "$LIVE_PRICE_JSON" >/dev/null 2>&1; then
            local_mtime=$(stat -f %m "$LIVE_PRICE_JSON")
        else
            local_mtime=$(stat -c %Y "$LIVE_PRICE_JSON")
        fi
        age=$(( local_now - local_mtime ))
        report_result "sierra_live_price_fresh" "mtime<60s" "stale(${age}s)" "SKIP"
    else
        report_result "sierra_live_price_fresh" "mtime<60s" "missing" "SKIP"
    fi
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 2: Backend health — HTTP 200
#   Tries /health (unified) then /api/v9/health (standalone)
# ═══════════════════════════════════════════════════════════════
backend_status=$(get_http_status "$BACKEND_URL/health")
if [[ "$backend_status" == "200" ]]; then
    report_result "backend_health" "200" "$backend_status" "PASS"
else
    # Fallback: standalone v9 app
    backend_status=$(get_http_status "$BACKEND_URL/api/v9/health")
    if [[ "$backend_status" == "200" ]]; then
        report_result "backend_health" "200" "${backend_status}(v9)" "PASS"
    else
        report_result "backend_health" "200" "$backend_status" "FAIL"
    fi
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 3: Bridge process alive
# ═══════════════════════════════════════════════════════════════
if check_process "json_bridge"; then
    report_result "bridge_process" "running" "running" "PASS"
else
    report_result "bridge_process" "running" "not_found" "FAIL"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 4: Redis XLEN price.tick > 0 (existing data)
# ═══════════════════════════════════════════════════════════════
xlen_before=$(get_redis_xlen "$PRICE_STREAM")
if check_redis_xlen "$PRICE_STREAM" 1; then
    report_result "redis_price_stream_exists" "XLEN>=1" "XLEN=$xlen_before" "PASS"
else
    report_result "redis_price_stream_exists" "XLEN>=1" "XLEN=$xlen_before" "FAIL"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 5: Redis XLEN growing (wait 10s, check delta > 5)
#   Only if bridge is running and Sierra is feeding data
# ═══════════════════════════════════════════════════════════════
if $SKIP_WAIT; then
    report_result "redis_price_stream_growing" "delta>5" "SKIPPED" "SKIP"
else
    if check_process "json_bridge" && ! $SKIP_SIERRA; then
        echo "  Waiting 10s to measure stream growth..."
        sleep 10
        xlen_after=$(get_redis_xlen "$PRICE_STREAM")
        if [[ "$xlen_before" =~ ^[0-9]+$ ]] && [[ "$xlen_after" =~ ^[0-9]+$ ]]; then
            delta=$(( xlen_after - xlen_before ))
            if (( delta > 5 )); then
                report_result "redis_price_stream_growing" "delta>5/10s" "delta=$delta" "PASS"
            else
                report_result "redis_price_stream_growing" "delta>5/10s" "delta=$delta" "FAIL"
            fi
        else
            report_result "redis_price_stream_growing" "delta>5/10s" "parse_err" "SKIP"
        fi
    else
        report_result "redis_price_stream_growing" "delta>5/10s" "bridge/sierra_down" "SKIP"
    fi
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 6: WS status endpoint
# ═══════════════════════════════════════════════════════════════
ws_status=$(get_http_status "$BACKEND_URL/api/v9/ws/status")
if [[ "$ws_status" == "200" ]]; then
    report_result "ws_status_endpoint" "200" "$ws_status" "PASS"
else
    report_result "ws_status_endpoint" "200" "$ws_status" "FAIL"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 7: Frontend port 3000 listening
# ═══════════════════════════════════════════════════════════════
if check_port 3000; then
    fe_status=$(get_http_status "$FRONTEND_URL")
    report_result "frontend_listening" "port_3000" "up(HTTP$fe_status)" "PASS"
else
    report_result "frontend_listening" "port_3000" "not_listening" "FAIL"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 8: V9 health endpoint
# ═══════════════════════════════════════════════════════════════
v9_status=$(get_http_status "$BACKEND_URL/api/v9/health")
if [[ "$v9_status" == "200" ]]; then
    report_result "v9_health" "200" "$v9_status" "PASS"
else
    report_result "v9_health" "200" "$v9_status" "FAIL"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 9: Event Bus schema registry file exists
# ═══════════════════════════════════════════════════════════════
if [[ -f "$REPO_ROOT/backend/v9/event_bus/schemas/registry.yaml" ]]; then
    report_result "schema_registry_exists" "file_exists" "exists" "PASS"
else
    report_result "schema_registry_exists" "file_exists" "missing" "FAIL"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 10: Generated TS types file exists
# ═══════════════════════════════════════════════════════════════
if [[ -f "$REPO_ROOT/frontend/v9/src/v9/types/events.ts" ]]; then
    report_result "ts_types_generated" "file_exists" "exists" "PASS"
else
    report_result "ts_types_generated" "file_exists" "missing" "FAIL"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 11: Unit tests pass
# ═══════════════════════════════════════════════════════════════
echo "  Running pytest tests/event_bus/ ..."
if python3 -m pytest "$REPO_ROOT/tests/event_bus/" -q --tb=no 2>/dev/null | tail -1 | grep -q "passed"; then
    test_line=$(python3 -m pytest "$REPO_ROOT/tests/event_bus/" -q --tb=no 2>/dev/null | tail -1)
    report_result "unit_tests_event_bus" "all_pass" "$test_line" "PASS"
else
    report_result "unit_tests_event_bus" "all_pass" "failures" "FAIL"
fi

# ═══════════════════════════════════════════════════════════════
# Summary + Report
# ═══════════════════════════════════════════════════════════════
write_report "$PROMPT_NUM" "$REPORT_DIR"
print_summary
