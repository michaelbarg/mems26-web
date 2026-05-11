#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 Spec Compliance Engine — runs all check_*.sh scripts
#
# Usage: ./scripts/spec_compliance/run_all.sh
# Exit:  0 = all pass, 1 = any check failed
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

printf "${CYAN}═══════════════════════════════════════════════════════════════${RESET}\n"
printf "${CYAN}  MEMS26 Spec Compliance Engine${RESET}\n"
printf "${CYAN}  $(date '+%Y-%m-%d %H:%M:%S')${RESET}\n"
printf "${CYAN}═══════════════════════════════════════════════════════════════${RESET}\n"
echo ""

PASS=0
FAIL=0
SKIP=0
FAILURES=""
START=$(date +%s)

for check in "$SCRIPT_DIR"/check_*.sh; do
    [[ -f "$check" ]] || continue
    name=$(basename "$check" .sh)

    output=$(bash "$check" 2>&1) || true
    status=$?
    first_line=$(echo "$output" | head -1)

    if echo "$first_line" | grep -q "^PASS"; then
        printf "${GREEN}  [PASS]${RESET} %s\n" "$name"
        (( PASS++ )) || true
    elif echo "$first_line" | grep -q "^SKIP"; then
        printf "${YELLOW}  [SKIP]${RESET} %s — %s\n" "$name" "$first_line"
        (( SKIP++ )) || true
    else
        printf "${RED}  [FAIL]${RESET} %s\n" "$name"
        echo "$output" | sed 's/^/         /'
        FAILURES="${FAILURES}  - ${name}\n"
        (( FAIL++ )) || true
    fi
done

ELAPSED=$(( $(date +%s) - START ))
TOTAL=$(( PASS + FAIL + SKIP ))

echo ""
printf "${CYAN}═══════════════════════════════════════════════════════════════${RESET}\n"
if (( FAIL == 0 )); then
    printf "${GREEN}  COMPLIANCE: ALL PASS${RESET}  (%d/%d pass, %d skip, %ds)\n" "$PASS" "$TOTAL" "$SKIP" "$ELAPSED"
else
    printf "${RED}  COMPLIANCE: %d FAILED${RESET}  (%d/%d pass, %d skip, %ds)\n" "$FAIL" "$PASS" "$TOTAL" "$SKIP" "$ELAPSED"
    echo -e "  Failed checks:\n$FAILURES"
fi
printf "${CYAN}═══════════════════════════════════════════════════════════════${RESET}\n"

# Write report
REPORT="$REPO_ROOT/docs/SPEC_COMPLIANCE_REPORT.md"
{
    echo "# Spec Compliance Report"
    echo ""
    echo "**Date:** $(date '+%Y-%m-%d %H:%M:%S')"
    echo "**Result:** ${PASS}/${TOTAL} PASS, ${FAIL} FAIL, ${SKIP} SKIP"
    echo "**Duration:** ${ELAPSED}s"
    echo ""
    echo "| Check | Status |"
    echo "|-------|--------|"
} > "$REPORT"

for check in "$SCRIPT_DIR"/check_*.sh; do
    [[ -f "$check" ]] || continue
    name=$(basename "$check" .sh)
    output=$(bash "$check" 2>&1) || true
    first_line=$(echo "$output" | head -1)
    if echo "$first_line" | grep -q "^PASS"; then
        echo "| $name | PASS |" >> "$REPORT"
    elif echo "$first_line" | grep -q "^SKIP"; then
        echo "| $name | SKIP |" >> "$REPORT"
    else
        echo "| $name | FAIL |" >> "$REPORT"
    fi
done

(( FAIL == 0 ))
