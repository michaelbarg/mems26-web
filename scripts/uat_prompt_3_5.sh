#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 UAT — Prompt 3.5: Schema Lock + Design System Foundation
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/uat_lib.sh"

PROMPT_NUM="3_5"
REPORT_DIR="$REPO_ROOT/docs/UAT_REPORTS"
BACKEND_URL="http://localhost:8000"
DB_FILE="$REPO_ROOT/data/mems26_local.db"

printf "\n${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n"
printf "${_CYAN}  MEMS26 UAT — Prompt 3.5: Schema Lock + Design System${_RESET}\n"
printf "${_CYAN}  $(date '+%Y-%m-%d %H:%M:%S')${_RESET}\n"
printf "${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n\n"

# ── INHERITED: Health checks ──────────────────────────────────
backend_status=$(get_http_status "$BACKEND_URL/api/v9/health")
if [[ "$backend_status" == "200" ]]; then
    report_result "backend_health" "200" "$backend_status" "PASS"
else
    report_result "backend_health" "200" "$backend_status" "FAIL"
fi

# ── GROUP A: 6 event schemas exist ────────────────────────────
schema_count=$(ls "$REPO_ROOT/backend/v9/event_bus/schemas/systems/"*.yaml 2>/dev/null | wc -l | tr -d ' ')
if (( schema_count == 6 )); then
    report_result "event_schemas" "6_files" "$schema_count" "PASS"
else
    report_result "event_schemas" "6_files" "$schema_count" "FAIL"
fi

# ── GROUP B: Base classes importable ──────────────────────────
if python3 -c "from backend.v9.systems.base import BaseV9TradingSystem, ContextProviderSystem, DecisionMakerSystem" 2>/dev/null; then
    report_result "base_classes_import" "importable" "OK" "PASS"
else
    report_result "base_classes_import" "importable" "failed" "FAIL"
fi

# ── GROUP C: 6 DB tables exist ────────────────────────────────
"$SCRIPT_DIR/db_init.sh" > /dev/null 2>&1 || true
new_tables=(v9_day_type_history v9_five_min_setups v9_footprint_markers v9_woodies_patterns v9_tpo_history v9_killzone_log)
tables_found=0
for table in "${new_tables[@]}"; do
    if sqlite3 "$DB_FILE" "SELECT 1 FROM $table LIMIT 0" 2>/dev/null; then
        (( tables_found++ )) || true
    fi
done
if (( tables_found == 6 )); then
    report_result "system_db_tables" "6_tables" "$tables_found" "PASS"
else
    report_result "system_db_tables" "6_tables" "$tables_found" "FAIL"
fi

total_v9=$(sqlite3 "$DB_FILE" ".tables" 2>/dev/null | tr ' ' '\n' | grep -c v9_ || echo 0)
if (( total_v9 >= 19 )); then
    report_result "total_v9_tables" ">=19" "$total_v9" "PASS"
else
    report_result "total_v9_tables" ">=19" "$total_v9" "FAIL"
fi

# ── GROUP D: Design tokens importable ─────────────────────────
for file in tokens.ts system_colors.ts; do
    if [[ -f "$REPO_ROOT/frontend/v9/src/v9/design/$file" ]]; then
        report_result "design_${file%.ts}" "exists" "exists" "PASS"
    else
        report_result "design_${file%.ts}" "exists" "missing" "FAIL"
    fi
done

# Atoms + Molecules exist
for comp in Pill.tsx StatusDot.tsx; do
    if [[ -f "$REPO_ROOT/frontend/v9/src/v9/components/atoms/$comp" ]]; then
        report_result "atom_${comp%.tsx}" "exists" "exists" "PASS"
    else
        report_result "atom_${comp%.tsx}" "exists" "missing" "FAIL"
    fi
done

for comp in SwitcherSlot.tsx Lens.tsx; do
    if [[ -f "$REPO_ROOT/frontend/v9/src/v9/components/molecules/$comp" ]]; then
        report_result "molecule_${comp%.tsx}" "exists" "exists" "PASS"
    else
        report_result "molecule_${comp%.tsx}" "exists" "missing" "FAIL"
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
echo "  Running tests..."
test_output=$(cd "$REPO_ROOT" && python3 -m pytest tests/systems/base/ tests/db/test_system_models.py tests/event_bus/ -q --tb=no 2>&1) || true
test_line=$(echo "$test_output" | grep -E "[0-9]+ passed" | tail -1)
if [[ "$test_line" == *"passed"* ]] && [[ "$test_line" != *"failed"* ]]; then
    report_result "unit_tests" "all_pass" "$test_line" "PASS"
else
    report_result "unit_tests" "all_pass" "${test_line:-no_output}" "FAIL"
fi

# ── Summary ───────────────────────────────────────────────────
write_report "$PROMPT_NUM" "$REPORT_DIR"
print_summary
