#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 UAT — Prompt N: <TITLE>
# Copy this file to uat_prompt_N.sh and fill in checks.
#
# Usage: ./scripts/uat_prompt_N.sh [--skip-sierra] [--skip-wait]
# Exit:  0 = all pass, 1 = failures
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/uat_lib.sh"

PROMPT_NUM=N   # ← CHANGE THIS
REPORT_DIR="$REPO_ROOT/docs/UAT_REPORTS"
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

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
printf "${_CYAN}  MEMS26 UAT — Prompt $PROMPT_NUM: <TITLE>${_RESET}\n"
printf "${_CYAN}  $(date '+%Y-%m-%d %H:%M:%S')${_RESET}\n"
printf "${_CYAN}═══════════════════════════════════════════════════════════════${_RESET}\n"
echo ""

# ═══════════════════════════════════════════════════════════════
# PREREQUISITE: Run Prompt 1 UAT first (inherited checks)
# ═══════════════════════════════════════════════════════════════
# Uncomment to require Prompt 1 baseline:
# bash "$SCRIPT_DIR/uat_prompt_1.sh" --skip-wait || {
#     echo "ERROR: Prompt 1 UAT failed — fix before running Prompt $PROMPT_NUM"
#     exit 1
# }

# ═══════════════════════════════════════════════════════════════
# CHECK 1: <description>
# Available helpers:
#   check_process "pattern"
#   check_file_fresh "/path/to/file" 60
#   check_redis_xlen "stream:key" 100
#   check_http "http://..." 200
#   check_log_pattern "/path/to/log" "regex"
#   check_port 8000
#   check_json_field "http://..." "field_name" "expected_value"
# ═══════════════════════════════════════════════════════════════
# Example:
# if check_http "$BACKEND_URL/api/v9/some/endpoint" 200; then
#     report_result "my_check_name" "200" "200" "PASS"
# else
#     actual=$(get_http_status "$BACKEND_URL/api/v9/some/endpoint")
#     report_result "my_check_name" "200" "$actual" "FAIL"
# fi

# ═══════════════════════════════════════════════════════════════
# CHECK 2: <description>
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# CHECK 3: <description>
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# Summary + Report
# ═══════════════════════════════════════════════════════════════
write_report "$PROMPT_NUM" "$REPORT_DIR"
print_summary
