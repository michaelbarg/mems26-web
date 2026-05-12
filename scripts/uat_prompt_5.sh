#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/uat_lib.sh"

PROMPT_NUM=5
REPORT_DIR="$REPO_ROOT/docs/UAT_REPORTS"
BACKEND_URL="http://localhost:8000"

printf "\n${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n"
printf "${_CYAN}  MEMS26 UAT — Prompt $PROMPT_NUM: System 2 (5-min)${_RESET}\n"
printf "${_CYAN}  $(date '+%Y-%m-%d %H:%M:%S')${_RESET}\n"
printf "${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n\n"

# Inherited: health
backend_status=$(get_http_status "$BACKEND_URL/api/v9/health")
if [[ "$backend_status" == "200" ]]; then
    report_result "backend_health" "200" "$backend_status" "PASS"
else
    report_result "backend_health" "200" "$backend_status" "FAIL"
fi

# Schema file
if [[ -f "$REPO_ROOT/backend/v9/event_bus/schemas/systems/five_min_setup_package.yaml" ]]; then
    report_result "schema_file" "exists" "exists" "PASS"
else
    report_result "schema_file" "exists" "missing" "FAIL"
fi

# DB table
if sqlite3 "$REPO_ROOT/data/mems26_local.db" "SELECT 1 FROM v9_five_min_state LIMIT 0" 2>/dev/null; then
    report_result "db_five_min_state" "exists" "exists" "PASS"
else
    report_result "db_five_min_state" "exists" "missing" "FAIL"
fi

# API endpoints
for ep in current setups stats; do
    status=$(get_http_status "$BACKEND_URL/api/v9/five_min/$ep")
    if [[ "$status" == "200" ]]; then
        report_result "api_five_min_$ep" "200" "$status" "PASS"
    else
        report_result "api_five_min_$ep" "200" "$status" "FAIL"
    fi
done

# Frontend components
for comp in FiveMinPill.tsx FiveMinLensContent.tsx; do
    if [[ -f "$REPO_ROOT/frontend/v9/src/v9/components/systems/$comp" ]]; then
        report_result "fe_${comp%.tsx}" "exists" "exists" "PASS"
    else
        report_result "fe_${comp%.tsx}" "exists" "missing" "FAIL"
    fi
done

# Hardcoded colors check (AP-DESIGN01)
if grep -rE "bg-\[#|text-\[#|border-\[#" "$REPO_ROOT/frontend/v9/src/v9/components/systems/FiveMin"*.tsx 2>/dev/null; then
    report_result "no_hardcoded_colors" "empty" "FOUND" "FAIL"
else
    report_result "no_hardcoded_colors" "empty" "clean" "PASS"
fi

# Hydration check
hydrate_ok=$(python3 -c "
import os; os.environ.setdefault('DATABASE_URL','sqlite:///./data/mems26_local.db'); os.environ.setdefault('BRIDGE_TOKEN','test')
from dotenv import load_dotenv; load_dotenv()
from backend.v9.systems.five_min.five_min_system import FiveMinSystem
fm = FiveMinSystem(); r = fm.hydrate()
print('OK' if r.success else 'FAIL')
" 2>/dev/null)
if [[ "$hydrate_ok" == "OK" ]]; then
    report_result "five_min_hydration" "success" "OK" "PASS"
else
    report_result "five_min_hydration" "success" "$hydrate_ok" "FAIL"
fi

# Build
echo "  Running next build..."
build_out=$(cd "$REPO_ROOT/frontend/v9" && npx next build 2>&1) || true
if echo "$build_out" | grep -q "Compiled successfully"; then
    report_result "frontend_build" "compiles" "success" "PASS"
else
    report_result "frontend_build" "compiles" "failed" "FAIL"
fi

# Spec compliance
if "$SCRIPT_DIR/spec_compliance/run_all.sh" > /dev/null 2>&1; then
    report_result "spec_compliance" "all_pass" "pass" "PASS"
else
    report_result "spec_compliance" "all_pass" "failures" "FAIL"
fi

# Unit tests
echo "  Running tests..."
test_output=$(cd "$REPO_ROOT" && python3 -m pytest tests/test_five_min_system.py tests/test_hydration.py tests/systems/ tests/event_bus/ -q --tb=no 2>&1) || true
test_line=$(echo "$test_output" | grep -E "[0-9]+ passed" | tail -1)
if [[ "$test_line" == *"passed"* ]] && [[ "$test_line" != *"failed"* ]]; then
    report_result "unit_tests" "all_pass" "$test_line" "PASS"
else
    report_result "unit_tests" "all_pass" "${test_line:-no_output}" "FAIL"
fi

write_report "$PROMPT_NUM" "$REPORT_DIR"
print_summary
