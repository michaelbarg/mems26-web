#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 UAT — Prompt 4: System 1 Day Type
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/uat_lib.sh"

PROMPT_NUM=4
REPORT_DIR="$REPO_ROOT/docs/UAT_REPORTS"
BACKEND_URL="http://localhost:8000"

printf "\n${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n"
printf "${_CYAN}  MEMS26 UAT — Prompt $PROMPT_NUM: System 1 Day Type${_RESET}\n"
printf "${_CYAN}  $(date '+%Y-%m-%d %H:%M:%S')${_RESET}\n"
printf "${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n\n"

# ── INHERITED: Health ─────────────────────────────────────────
backend_status=$(get_http_status "$BACKEND_URL/api/v9/health")
if [[ "$backend_status" == "200" ]]; then
    report_result "backend_health" "200" "$backend_status" "PASS"
else
    report_result "backend_health" "200" "$backend_status" "FAIL"
fi

# ── Day Type API ──────────────────────────────────────────────
dt_current=$(get_http_status "$BACKEND_URL/api/v9/day_type/current")
if [[ "$dt_current" == "200" ]]; then
    report_result "day_type_current_api" "200" "$dt_current" "PASS"
else
    report_result "day_type_current_api" "200" "$dt_current" "FAIL"
fi

dt_state=$(get_http_status "$BACKEND_URL/api/v9/day_type/state")
if [[ "$dt_state" == "200" ]]; then
    report_result "day_type_state_api" "200" "$dt_state" "PASS"
else
    report_result "day_type_state_api" "200" "$dt_state" "FAIL"
fi

dt_stats=$(get_http_status "$BACKEND_URL/api/v9/day_type/stats")
if [[ "$dt_stats" == "200" ]]; then
    report_result "day_type_stats_api" "200" "$dt_stats" "PASS"
else
    report_result "day_type_stats_api" "200" "$dt_stats" "FAIL"
fi

# ── Status shows day_type layer ───────────────────────────────
status_resp=$(curl -s --max-time 10 "$BACKEND_URL/api/v9/status" 2>/dev/null || echo "{}")
if echo "$status_resp" | grep -q "day_type"; then
    report_result "status_day_type_layer" "present" "found" "PASS"
else
    report_result "status_day_type_layer" "present" "missing" "FAIL"
fi

# ── Frontend components exist ─────────────────────────────────
for comp in DayTypePill.tsx DayTypeLensContent.tsx; do
    if [[ -f "$REPO_ROOT/frontend/v9/src/v9/components/systems/$comp" ]]; then
        report_result "fe_${comp%.tsx}" "exists" "exists" "PASS"
    else
        report_result "fe_${comp%.tsx}" "exists" "missing" "FAIL"
    fi
done

for comp in Switcher.tsx SidePanel.tsx Layer0Strip.tsx; do
    if [[ -f "$REPO_ROOT/frontend/v9/src/v9/components/layout/$comp" ]]; then
        report_result "fe_${comp%.tsx}" "exists" "exists" "PASS"
    else
        report_result "fe_${comp%.tsx}" "exists" "missing" "FAIL"
    fi
done

# ── Frontend build ────────────────────────────────────────────
echo "  Running next build..."
build_out=$(cd "$REPO_ROOT/frontend/v9" && npx next build 2>&1) || true
if echo "$build_out" | grep -q "Compiled successfully"; then
    report_result "frontend_build" "compiles" "success" "PASS"
else
    report_result "frontend_build" "compiles" "failed" "FAIL"
fi

# ── Spec compliance ───────────────────────────────────────────
if "$SCRIPT_DIR/spec_compliance/run_all.sh" > /dev/null 2>&1; then
    report_result "spec_compliance" "all_pass" "pass" "PASS"
else
    report_result "spec_compliance" "all_pass" "failures" "FAIL"
fi

# ── Unit tests ────────────────────────────────────────────────
echo "  Running day type + event bus tests..."
test_output=$(cd "$REPO_ROOT" && python3 -m pytest tests/systems/day_type/ tests/event_bus/ -q --tb=no 2>&1) || true
test_line=$(echo "$test_output" | grep -E "[0-9]+ passed" | tail -1)
if [[ "$test_line" == *"passed"* ]] && [[ "$test_line" != *"failed"* ]]; then
    report_result "unit_tests" "all_pass" "$test_line" "PASS"
else
    report_result "unit_tests" "all_pass" "${test_line:-no_output}" "FAIL"
fi

# ── Summary ───────────────────────────────────────────────────
write_report "$PROMPT_NUM" "$REPORT_DIR"
print_summary
