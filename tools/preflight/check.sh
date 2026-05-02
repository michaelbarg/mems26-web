#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MEMS26 — Pre-Flight Checklist V1
# Run before Phase 3.2 market sessions to verify system health.
#
# Usage:
#   bash tools/preflight/check.sh
#   bash tools/preflight/check.sh --verbose
#   bash tools/preflight/check.sh --quiet
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ── Config ────────────────────────────────────────────────────
API_URL="${MEMS26_API_URL:-https://mems26-web.onrender.com}"
REPO_DIR="${MEMS26_REPO:-/Users/michael/Downloads/mems26_web_git}"
SC_DATA="/Users/michael/SierraChart2/Data/mes_ai_data.json"
SC_HISTORY="/Users/michael/SierraChart2/Data/mes_ai_history.json"
BRIDGE_LOG="/tmp/bridge.log"

# Parse args
VERBOSE=false
QUIET=false
for arg in "$@"; do
    case "$arg" in
        --verbose|-v) VERBOSE=true ;;
        --quiet|-q)   QUIET=true ;;
    esac
done

# ── Counters ──────────────────────────────────────────────────
PASS=0
WARN=0
FAIL=0
declare -a ACTIONS=()

pass()  { PASS=$((PASS + 1)); $QUIET || echo "  ✓ $1"; }
warn()  { WARN=$((WARN + 1)); $QUIET || echo "  ⚠ $1"; ACTIONS+=("$2"); }
fail()  { FAIL=$((FAIL + 1)); $QUIET || echo "  ✗ $1"; ACTIONS+=("$2"); }
info()  { $QUIET || echo "  ℹ $1"; }

# ── Header ────────────────────────────────────────────────────
NOW_IL=$(TZ="Asia/Jerusalem" date "+%Y-%m-%d %H:%M:%S")

if ! $QUIET; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  MEMS26 — Pre-Flight Checklist"
    echo "  Date: ${NOW_IL} IL"
    echo "  API:  ${API_URL}"
    echo "═══════════════════════════════════════════════════════════════"
fi

# ═══════════════════════════════════════════════════════════════
# 1. ENVIRONMENT
# ═══════════════════════════════════════════════════════════════
$QUIET || echo -e "\nENVIRONMENT"

cd "$REPO_DIR" 2>/dev/null || { fail "Repo not found at ${REPO_DIR}" "Clone/check REPO_DIR"; }

# Branch
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [[ "$BRANCH" == "main" ]]; then
    pass "Branch: main"
else
    warn "Branch: ${BRANCH} (expected main)" "Switch to main before market open: git checkout main"
fi

# Working tree
if git diff --quiet HEAD 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
    pass "Working tree: clean"
else
    DIRTY=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
    warn "Working tree: ${DIRTY} modified files" "Commit or stash changes before market open"
fi

# Latest commit
COMMIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
COMMIT_MSG=$(git log -1 --pretty=format:"%s" 2>/dev/null || echo "unknown")
info "Latest commit: ${COMMIT_HASH} \"${COMMIT_MSG}\""

# ═══════════════════════════════════════════════════════════════
# 2. BRIDGE STATUS
# ═══════════════════════════════════════════════════════════════
$QUIET || echo -e "\nBRIDGE STATUS"

BRIDGE_PID=$(pgrep -f "json_bridge.py" 2>/dev/null || true)
if [[ -n "$BRIDGE_PID" ]]; then
    pass "Bridge process: running (pid ${BRIDGE_PID})"
else
    warn "Bridge process: NOT running" "Start Bridge before market open: cd bridge && python3 json_bridge.py"
fi

if [[ -f "$BRIDGE_LOG" ]]; then
    LOG_MOD=$(stat -f %m "$BRIDGE_LOG" 2>/dev/null || stat -c %Y "$BRIDGE_LOG" 2>/dev/null || echo 0)
    NOW_TS=$(date +%s)
    LOG_AGE=$(( NOW_TS - LOG_MOD ))
    if (( LOG_AGE < 300 )); then
        pass "Bridge log: ${LOG_AGE}s old"
    elif (( LOG_AGE < 3600 )); then
        warn "Bridge log: ${LOG_AGE}s old (stale)" "Restart Bridge — log hasn't updated in $((LOG_AGE / 60)) min"
    else
        warn "Bridge log: ${LOG_AGE}s old (very stale)" "Bridge likely stopped — restart before market open"
    fi
else
    info "Bridge log: not found at ${BRIDGE_LOG} (normal if never started)"
fi

# ═══════════════════════════════════════════════════════════════
# 3. SIERRA CHART
# ═══════════════════════════════════════════════════════════════
$QUIET || echo -e "\nSIERRA CHART"

if [[ -f "$SC_DATA" ]]; then
    SC_MOD=$(stat -f %m "$SC_DATA" 2>/dev/null || stat -c %Y "$SC_DATA" 2>/dev/null || echo 0)
    SC_AGE=$(( $(date +%s) - SC_MOD ))
    if (( SC_AGE < 60 )); then
        pass "mes_ai_data.json: fresh (${SC_AGE}s old)"
    elif (( SC_AGE < 600 )); then
        info "mes_ai_data.json: ${SC_AGE}s old (OK if market closed)"
    else
        warn "mes_ai_data.json: ${SC_AGE}s old" "Sierra Chart not exporting — start before market open"
    fi
else
    warn "mes_ai_data.json: NOT FOUND" "Start Sierra Chart before market open"
fi

if [[ -f "$SC_HISTORY" ]]; then
    pass "mes_ai_history.json: exists"
else
    warn "mes_ai_history.json: NOT FOUND" "Sierra may need history export — check after SC starts"
fi

# ═══════════════════════════════════════════════════════════════
# 4. BACKEND HEALTH
# ═══════════════════════════════════════════════════════════════
$QUIET || echo -e "\nBACKEND HEALTH"

HEALTH_JSON=$(curl -s --connect-timeout 10 --max-time 15 "${API_URL}/health" 2>/dev/null || echo "")

if [[ -z "$HEALTH_JSON" ]]; then
    fail "Backend unreachable at ${API_URL}" "Check Render deployment — backend may be sleeping or down"
else
    # Parse with python3 (available on macOS)
    parse_health() {
        python3 -c "
import json, sys
h = json.loads(sys.argv[1])
key = sys.argv[2]
val = h.get(key, '__MISSING__')
print(val)
" "$HEALTH_JSON" "$1" 2>/dev/null || echo "__ERROR__"
    }

    STATUS=$(parse_health "status")
    MODE=$(parse_health "mode")
    ENTRY_MODE=$(parse_health "entry_mode")
    KZ_REQ=$(parse_health "killzone_required")
    BRIDGE_HB=$(parse_health "bridge_heartbeat_age_sec")
    REDIS_OK=$(parse_health "redis_ok")
    NEWS_OK=$(parse_health "news_guard_healthy")
    GATE_RELVOL=$(parse_health "gate_relvol_min")
    GATE_FVG=$(parse_health "gate_fvg_max")
    GATE_SWEEP=$(parse_health "gate_sweep_min")
    PRE_CLOSE=$(parse_health "pre_close_freeze_active")

    # Status
    if [[ "$STATUS" == "ok" ]]; then
        pass "Backend status: ok"
    else
        fail "Backend status: ${STATUS}" "Backend not healthy — check Render logs"
    fi

    # Mode
    if [[ "$MODE" == "SIM" ]]; then
        pass "Mode: SIM"
    elif [[ "$MODE" == "LIVE" ]]; then
        fail "Mode: LIVE (should be SIM for Phase 3.2)" "Set MEMS26_MODE=SIM in Render env vars"
    else
        warn "Mode: ${MODE}" "Verify MEMS26_MODE env var"
    fi

    # Entry mode
    if [[ "$ENTRY_MODE" == "DEMO" ]]; then
        pass "Entry mode: DEMO"
    elif [[ "$ENTRY_MODE" == "STRICT" || "$ENTRY_MODE" == "LIVE" ]]; then
        warn "Entry mode: ${ENTRY_MODE} (expected DEMO)" "Bridge config entry_mode should be DEMO for Phase 3.2"
    else
        info "Entry mode: ${ENTRY_MODE}"
    fi

    # Killzone required
    if [[ "$KZ_REQ" == "False" || "$KZ_REQ" == "false" ]]; then
        pass "Killzone required: false"
    else
        warn "Killzone required: ${KZ_REQ}" "May block off-hours setups — verify this is intended"
    fi

    # Gates (DEMO defaults: 1.0 / 5.0 / 1.0)
    GATES="${GATE_RELVOL}/${GATE_FVG}/${GATE_SWEEP}"
    if [[ "$GATE_RELVOL" == "1.0" && "$GATE_FVG" == "5.0" && "$GATE_SWEEP" == "1.0" ]]; then
        pass "Gates: ${GATES} (DEMO relaxed)"
    else
        info "Gates: ${GATES} (non-default — verify intended)"
    fi

    # Bridge heartbeat
    if [[ "$BRIDGE_HB" =~ ^-?[0-9]+$ ]]; then
        if (( BRIDGE_HB >= 0 && BRIDGE_HB < 60 )); then
            pass "Bridge heartbeat: ${BRIDGE_HB}s"
        elif (( BRIDGE_HB < 300 )); then
            warn "Bridge heartbeat: ${BRIDGE_HB}s (stale)" "Bridge data is ${BRIDGE_HB}s old — may need restart"
        else
            if (( BRIDGE_HB < 0 )); then
                info "Bridge heartbeat: no data yet (${BRIDGE_HB})"
            else
                fail "Bridge heartbeat: ${BRIDGE_HB}s (very stale)" "Bridge not sending data — restart before market open"
            fi
        fi
    else
        info "Bridge heartbeat: ${BRIDGE_HB}"
    fi

    # Redis
    if [[ "$REDIS_OK" == "True" || "$REDIS_OK" == "true" ]]; then
        pass "Redis: OK"
    else
        fail "Redis: NOT OK" "Check Upstash Redis connection — backend can't function without it"
    fi

    # News guard
    if [[ "$NEWS_OK" == "True" || "$NEWS_OK" == "true" ]]; then
        pass "News guard: healthy"
    else
        warn "News guard: not available" "News guard down — trades won't be blocked around news events"
    fi

    # Show raw JSON in verbose mode
    if $VERBOSE; then
        info "Raw /health response:"
        echo "$HEALTH_JSON" | python3 -m json.tool 2>/dev/null | sed 's/^/    /'
    fi
fi

# ═══════════════════════════════════════════════════════════════
# 5. RECENT ACTIVITY
# ═══════════════════════════════════════════════════════════════
$QUIET || echo -e "\nRECENT ACTIVITY"

DQ_JSON=$(curl -s --connect-timeout 10 --max-time 15 "${API_URL}/analytics/data_quality_check" 2>/dev/null || echo "")

if [[ -n "$DQ_JSON" ]]; then
    parse_dq() {
        python3 -c "
import json, sys
d = json.loads(sys.argv[1])
checks = d.get('checks', {})
key = sys.argv[2]
# Handle nested keys with dot notation
parts = key.split('.')
val = checks
for p in parts:
    if isinstance(val, dict):
        val = val.get(p, '__MISSING__')
    else:
        val = '__MISSING__'
        break
print(val)
" "$DQ_JSON" "$1" 2>/dev/null || echo "__ERROR__"
    }

    ATTEMPTS_24H=$(parse_dq "total_attempts_24h")
    DIR_RATIO=$(parse_dq "direction_balance.ratio")
    WITH_OUTCOMES=$(parse_dq "with_outcome")

    # Setup count
    if [[ "$ATTEMPTS_24H" =~ ^[0-9]+$ ]]; then
        if (( ATTEMPTS_24H > 2000 )); then
            pass "Setups in 24h: ${ATTEMPTS_24H}"
        elif (( ATTEMPTS_24H > 0 )); then
            warn "Setups in 24h: ${ATTEMPTS_24H} (low)" "Low setup count — expected if market closed/weekend"
        else
            warn "Setups in 24h: 0" "No setups detected — verify Bridge is running during market hours"
        fi
    else
        info "Setups in 24h: ${ATTEMPTS_24H}"
    fi

    # Direction balance
    if [[ "$DIR_RATIO" =~ ^[0-9.]+$ ]]; then
        DIR_RATIO_INT=$(python3 -c "print(int(float('$DIR_RATIO')))" 2>/dev/null || echo 0)
        if (( DIR_RATIO_INT < 5 )); then
            pass "Direction balance: ${DIR_RATIO}x ratio"
        else
            warn "Direction balance: ${DIR_RATIO}x ratio (extreme)" "Heavy directional bias — may indicate data issue"
        fi
    else
        info "Direction balance: ${DIR_RATIO}"
    fi

    # Outcomes
    if [[ "$WITH_OUTCOMES" =~ ^[0-9]+$ ]] && (( WITH_OUTCOMES > 0 )); then
        pass "Setups with outcomes: ${WITH_OUTCOMES}"
    else
        info "Setups with outcomes: ${WITH_OUTCOMES} (normal if sequential sim hasn't run)"
    fi
else
    warn "Data quality check: API unreachable" "Could not fetch /analytics/data_quality_check"
fi

# Sequential summary
SEQ_JSON=$(curl -s --connect-timeout 10 --max-time 15 "${API_URL}/analytics/setups/sequential_today_summary" 2>/dev/null || echo "")
if [[ -n "$SEQ_JSON" ]]; then
    SEQ_EXEC=$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('total_executed_in_sim',0))" "$SEQ_JSON" 2>/dev/null || echo 0)
    if [[ "$SEQ_EXEC" =~ ^[0-9]+$ ]] && (( SEQ_EXEC > 0 )); then
        pass "Sequential sim today: ${SEQ_EXEC} executed"
    else
        info "Sequential sim today: 0 executed (normal off-market)"
    fi
fi

# ═══════════════════════════════════════════════════════════════
# 6. CRITICAL CONFIGS
# ═══════════════════════════════════════════════════════════════
$QUIET || echo -e "\nCRITICAL CONFIGS"

if [[ -n "$HEALTH_JSON" ]]; then
    # Pre-close freeze (time-based, may be true/false depending on time)
    if [[ "$PRE_CLOSE" == "True" || "$PRE_CLOSE" == "true" ]]; then
        pass "Pre-close freeze: active (expected if after 15:30 ET)"
    else
        info "Pre-close freeze: inactive (normal before 15:30 ET)"
    fi

    # Summarize mode for critical check
    if [[ "$MODE" == "SIM" ]]; then
        pass "MEMS26_MODE: SIM"
    fi
fi

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════

TOTAL=$((PASS + WARN + FAIL))

if ! $QUIET; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"

    if (( FAIL > 0 )); then
        echo "  SUMMARY: ✗ NOT READY — ${FAIL} critical failure(s)"
    elif (( WARN > 0 )); then
        echo "  SUMMARY: ⚠ READY WITH WARNINGS"
    else
        echo "  SUMMARY: ✓ ALL CLEAR"
    fi

    echo ""
    echo "  Pass:      ${PASS}"
    echo "  Warnings:  ${WARN}"
    echo "  Failures:  ${FAIL}"

    if (( ${#ACTIONS[@]} > 0 )); then
        echo ""
        echo "  Action items:"
        for i in "${!ACTIONS[@]}"; do
            echo "    $((i + 1)). ${ACTIONS[$i]}"
        done
    fi

    echo ""
    if (( FAIL > 0 )); then
        echo "  GO/NO-GO: ✗ NO-GO — Fix critical failures first."
    elif (( WARN > 0 )); then
        echo "  GO/NO-GO: ⚠ CONDITIONAL GO — Address warnings before market open."
    else
        echo "  GO/NO-GO: ✓ GO"
    fi
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
fi

# Save report to file
REPORT_DIR="$(dirname "$0")/output"
mkdir -p "$REPORT_DIR"
REPORT_FILE="${REPORT_DIR}/preflight_$(date +%Y%m%d_%H%M%S).txt"

{
    echo "MEMS26 Pre-Flight Report — ${NOW_IL} IL"
    echo "Pass: ${PASS}  Warn: ${WARN}  Fail: ${FAIL}"
    echo "API: ${API_URL}"
    echo "Branch: ${BRANCH}  Commit: ${COMMIT_HASH}"
    if (( ${#ACTIONS[@]} > 0 )); then
        echo "Actions:"
        for a in "${ACTIONS[@]}"; do echo "  - $a"; done
    fi
} > "$REPORT_FILE"

$QUIET || echo "  Report saved: ${REPORT_FILE}"

# Exit code
if (( FAIL > 0 )); then
    exit 1
else
    exit 0
fi
