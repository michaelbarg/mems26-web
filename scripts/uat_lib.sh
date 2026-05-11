#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 UAT Library — shared helpers for all uat_prompt_N.sh
# Source this file, don't execute it directly.
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

# ── Load .env if present ──────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$REPO_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.env"
    set +a
fi

# ── State ─────────────────────────────────────────────────────
_UAT_PASS=0
_UAT_FAIL=0
_UAT_SKIP=0
_UAT_RESULTS=()
_UAT_START=$(date +%s)

# ── Colors ────────────────────────────────────────────────────
_GREEN='\033[0;32m'
_RED='\033[0;31m'
_YELLOW='\033[0;33m'
_CYAN='\033[0;36m'
_RESET='\033[0m'

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

# check_process PATTERN
#   Returns 0 if any process matching PATTERN is running.
check_process() {
    local pattern="$1"
    pgrep -f "$pattern" >/dev/null 2>&1
}

# check_file_fresh PATH MAX_AGE_SEC
#   Returns 0 if file exists and mtime < MAX_AGE_SEC ago.
check_file_fresh() {
    local path="$1"
    local max_age="$2"
    [[ -f "$path" ]] || return 1
    local now mtime age
    now=$(date +%s)
    # macOS stat vs Linux stat
    if stat -f %m "$path" >/dev/null 2>&1; then
        mtime=$(stat -f %m "$path")
    else
        mtime=$(stat -c %Y "$path")
    fi
    age=$(( now - mtime ))
    (( age <= max_age ))
}

# check_redis_xlen STREAM_NAME MIN_VALUE
#   Returns 0 if XLEN of stream >= MIN_VALUE.
#   Uses Upstash REST API (reads UPSTASH_REDIS_REST_URL/TOKEN from env).
check_redis_xlen() {
    local stream="$1"
    local min_val="$2"

    if [[ -z "${UPSTASH_REDIS_REST_URL:-}" || -z "${UPSTASH_REDIS_REST_TOKEN:-}" ]]; then
        return 1
    fi

    local resp
    resp=$(curl -s -X POST "$UPSTASH_REDIS_REST_URL" \
        -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
        -H "Content-Type: application/json" \
        -d "[\"XLEN\",\"$stream\"]" 2>/dev/null) || return 1

    # Parse {"result":NNN}
    local xlen
    xlen=$(echo "$resp" | sed -n 's/.*"result":\([0-9]*\).*/\1/p')
    [[ -n "$xlen" ]] && (( xlen >= min_val ))
}

# get_redis_xlen STREAM_NAME
#   Prints the XLEN value (for reporting).
get_redis_xlen() {
    local stream="$1"
    if [[ -z "${UPSTASH_REDIS_REST_URL:-}" || -z "${UPSTASH_REDIS_REST_TOKEN:-}" ]]; then
        echo "N/A"
        return
    fi
    local resp
    resp=$(curl -s -X POST "$UPSTASH_REDIS_REST_URL" \
        -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
        -H "Content-Type: application/json" \
        -d "[\"XLEN\",\"$stream\"]" 2>/dev/null) || { echo "ERR"; return; }
    echo "$resp" | sed -n 's/.*"result":\([0-9]*\).*/\1/p'
}

# check_http URL [EXPECTED_STATUS]
#   Returns 0 if HTTP status matches expected (default 200).
check_http() {
    local url="$1"
    local expected="${2:-200}"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "$url" 2>/dev/null) || return 1
    [[ "$status" == "$expected" ]]
}

# get_http_status URL
#   Prints the HTTP status code.
get_http_status() {
    local url="$1"
    curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "$url" 2>/dev/null || echo "000"
}

# check_log_pattern FILE REGEX [MAX_AGE_LINES]
#   Returns 0 if REGEX matches in last MAX_AGE_LINES (default 200) of FILE.
check_log_pattern() {
    local file="$1"
    local regex="$2"
    local max_lines="${3:-200}"
    [[ -f "$file" ]] || return 1
    tail -n "$max_lines" "$file" | grep -qE "$regex"
}

# check_port PORT
#   Returns 0 if something is listening on PORT.
check_port() {
    local port="$1"
    lsof -iTCP:"$port" -sTCP:LISTEN -P -n >/dev/null 2>&1
}

# check_json_field URL FIELD EXPECTED
#   Fetches URL, checks if JSON field equals expected value.
check_json_field() {
    local url="$1"
    local field="$2"
    local expected="$3"
    local resp
    resp=$(curl -s --connect-timeout 3 --max-time 5 "$url" 2>/dev/null) || return 1
    local actual
    # Simple JSON field extraction (no jq dependency)
    actual=$(echo "$resp" | sed -n "s/.*\"$field\"[[:space:]]*:[[:space:]]*\"\{0,1\}\([^,\"}\{]*\)\"\{0,1\}.*/\1/p" | head -1)
    [[ "$actual" == "$expected" ]]
}

# ═══════════════════════════════════════════════════════════════
# Reporting
# ═══════════════════════════════════════════════════════════════

# report_result NAME EXPECTED ACTUAL STATUS
#   STATUS: PASS | FAIL | SKIP
report_result() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    local status="$4"

    case "$status" in
        PASS) (( _UAT_PASS++ )) || true; local color="$_GREEN" ;;
        FAIL) (( _UAT_FAIL++ )) || true; local color="$_RED" ;;
        SKIP) (( _UAT_SKIP++ )) || true; local color="$_YELLOW" ;;
        *)    local color="$_RESET" ;;
    esac

    _UAT_RESULTS+=("$(printf "%-40s %-20s %-20s %s" "$name" "$expected" "$actual" "$status")")
    printf "${color}  [%s]${_RESET} %-40s expected=%-15s actual=%s\n" "$status" "$name" "$expected" "$actual"
}

# print_summary
#   Prints the summary table and returns exit code (0 if all pass).
print_summary() {
    local elapsed=$(( $(date +%s) - _UAT_START ))
    local total=$(( _UAT_PASS + _UAT_FAIL + _UAT_SKIP ))

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    if (( _UAT_FAIL == 0 )); then
        printf "${_GREEN}  UAT RESULT: ALL PASS${_RESET}  (%d/%d pass, %d skip, %ds)\n" "$_UAT_PASS" "$total" "$_UAT_SKIP" "$elapsed"
    else
        printf "${_RED}  UAT RESULT: %d FAILED${_RESET}  (%d/%d pass, %d skip, %ds)\n" "$_UAT_FAIL" "$_UAT_PASS" "$total" "$_UAT_SKIP" "$elapsed"
    fi
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # Return 0 only if zero failures
    (( _UAT_FAIL == 0 ))
}

# write_report PROMPT_NUM OUTPUT_DIR
#   Writes a markdown report to OUTPUT_DIR/PROMPT_N_<timestamp>.md
write_report() {
    local prompt_num="$1"
    local output_dir="$2"
    local ts
    ts=$(date +%Y%m%d_%H%M%S)
    local elapsed=$(( $(date +%s) - _UAT_START ))
    local total=$(( _UAT_PASS + _UAT_FAIL + _UAT_SKIP ))
    local file="$output_dir/PROMPT_${prompt_num}_${ts}.md"

    mkdir -p "$output_dir"

    {
        echo "# UAT Report — Prompt $prompt_num"
        echo ""
        echo "**Date:** $(date '+%Y-%m-%d %H:%M:%S')"
        echo "**Duration:** ${elapsed}s"
        echo "**Result:** ${_UAT_PASS}/${total} PASS, ${_UAT_FAIL} FAIL, ${_UAT_SKIP} SKIP"
        echo ""
        echo "| Check | Expected | Actual | Status |"
        echo "|-------|----------|--------|--------|"
        for row in "${_UAT_RESULTS[@]}"; do
            # Parse the printf-formatted row back into fields
            local name expected actual status
            name=$(echo "$row" | awk '{print $1, $2, $3}' | sed 's/ *$//')
            # Re-extract from stored data — simpler to store structured
            echo "| $row |" | sed 's/  */ | /g; s/^| /| /; s/ |$/|/'
        done
        echo ""
        if (( _UAT_FAIL == 0 )); then
            echo "**VERDICT: PASS**"
        else
            echo "**VERDICT: FAIL**"
        fi
    } > "$file"

    echo "Report written to: $file"
}
