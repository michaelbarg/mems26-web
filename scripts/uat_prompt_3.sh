#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 UAT — Prompt 3: Database + Audit Log + Spec Compliance
#
# Usage: ./scripts/uat_prompt_3.sh [--skip-sierra] [--skip-wait]
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/uat_lib.sh"

PROMPT_NUM=3
REPORT_DIR="$REPO_ROOT/docs/UAT_REPORTS"
BACKEND_URL="http://localhost:8000"
DB_FILE="$REPO_ROOT/data/mems26_local.db"

SKIP_SIERRA=false
SKIP_WAIT=false
for arg in "$@"; do
    case "$arg" in
        --skip-sierra) SKIP_SIERRA=true ;;
        --skip-wait)   SKIP_WAIT=true ;;
    esac
done

printf "\n${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n"
printf "${_CYAN}  MEMS26 UAT — Prompt $PROMPT_NUM: DB + Audit + Spec Compliance${_RESET}\n"
printf "${_CYAN}  $(date '+%Y-%m-%d %H:%M:%S')${_RESET}\n"
printf "${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n\n"

# ── INHERITED: Basic health ───────────────────────────────────
backend_status=$(get_http_status "$BACKEND_URL/api/v9/health")
if [[ "$backend_status" == "200" ]]; then
    report_result "backend_health" "200" "$backend_status" "PASS"
else
    report_result "backend_health" "200" "$backend_status" "FAIL"
fi

if check_redis_xlen "mems26:events:price.tick" 1; then
    report_result "redis_price_stream" "XLEN>=1" "OK" "PASS"
else
    report_result "redis_price_stream" "XLEN>=1" "empty" "FAIL"
fi

# ── PROMPT 3: DB Foundation ───────────────────────────────────
# CHECK: db_init.sh succeeds
echo "  Running db_init.sh..."
if "$SCRIPT_DIR/db_init.sh" > /dev/null 2>&1; then
    report_result "db_init" "exits_0" "success" "PASS"
else
    report_result "db_init" "exits_0" "failed" "FAIL"
fi

# CHECK: SQLite DB file exists
if [[ -f "$DB_FILE" ]]; then
    size=$(du -h "$DB_FILE" | cut -f1)
    report_result "db_file_exists" "exists" "${size}" "PASS"
else
    report_result "db_file_exists" "exists" "missing" "FAIL"
fi

# CHECK: audit_events table exists
if sqlite3 "$DB_FILE" "SELECT count(*) FROM v9_audit_events" > /dev/null 2>&1; then
    count=$(sqlite3 "$DB_FILE" "SELECT count(*) FROM v9_audit_events" 2>/dev/null)
    report_result "audit_table_exists" "queryable" "rows=$count" "PASS"
else
    report_result "audit_table_exists" "queryable" "error" "FAIL"
fi

# ── PROMPT 3: Audit Consumer ─────────────────────────────────
# CHECK: Audit consumer writes events (start, wait, check)
if ! $SKIP_WAIT; then
    echo "  Starting audit consumer for 10s..."
    "$SCRIPT_DIR/start_audit.sh" > /dev/null 2>&1
    sleep 10
    count_after=$(sqlite3 "$DB_FILE" "SELECT count(*) FROM v9_audit_events" 2>/dev/null || echo "0")
    "$SCRIPT_DIR/start_audit.sh" stop > /dev/null 2>&1
    if (( count_after >= 10 )); then
        report_result "audit_consumer_writes" ">=10_rows" "rows=$count_after" "PASS"
    else
        report_result "audit_consumer_writes" ">=10_rows" "rows=$count_after" "FAIL"
    fi
else
    report_result "audit_consumer_writes" ">=10_rows" "SKIPPED" "SKIP"
fi

# ── PROMPT 3: Audit API ──────────────────────────────────────
audit_stats_status=$(get_http_status "$BACKEND_URL/api/v9/audit/stats")
if [[ "$audit_stats_status" == "200" ]]; then
    report_result "audit_stats_api" "200" "$audit_stats_status" "PASS"
else
    report_result "audit_stats_api" "200" "$audit_stats_status" "FAIL"
fi

# ── PROMPT 3: Spec Compliance ────────────────────────────────
echo "  Running spec compliance..."
if "$SCRIPT_DIR/spec_compliance/run_all.sh" > /dev/null 2>&1; then
    report_result "spec_compliance" "all_pass" "pass" "PASS"
else
    report_result "spec_compliance" "all_pass" "failures" "FAIL"
fi

spec_status=$(get_http_status "$BACKEND_URL/api/v9/spec/status")
if [[ "$spec_status" == "200" ]]; then
    report_result "spec_api" "200" "$spec_status" "PASS"
else
    report_result "spec_api" "200" "$spec_status" "FAIL"
fi

# ── PROMPT 3: Backup ─────────────────────────────────────────
echo "  Testing db_backup.sh..."
if "$SCRIPT_DIR/db_backup.sh" > /dev/null 2>&1; then
    report_result "db_backup" "exits_0" "success" "PASS"
else
    report_result "db_backup" "exits_0" "failed" "FAIL"
fi

# ── PROMPT 3: Frontend + unit tests still pass ────────────────
if check_port 3000; then
    report_result "frontend_up" "port_3000" "up" "PASS"
else
    report_result "frontend_up" "port_3000" "down" "FAIL"
fi

echo "  Running pytest tests/event_bus/ ..."
test_output=$(cd "$REPO_ROOT" && python3 -m pytest tests/event_bus/ -q --tb=no 2>&1) || true
test_line=$(echo "$test_output" | grep -E "[0-9]+ passed" | tail -1)
if [[ "$test_line" == *"passed"* ]] && [[ "$test_line" != *"failed"* ]]; then
    report_result "unit_tests" "all_pass" "$test_line" "PASS"
else
    report_result "unit_tests" "all_pass" "${test_line:-no_output}" "FAIL"
fi

# ── Summary ───────────────────────────────────────────────────
write_report "$PROMPT_NUM" "$REPORT_DIR"
print_summary
