#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────
# MEMS26 V9 — R3 Spec Compliance Audit
# Per: MEMS26_SPEC_COMPLIANCE_AND_CROSS_SYSTEM_SNAPSHOT_LOCKED_V1.1
#
# Runs all compliance tests, parses manifests, computes drift %.
# Exit 0 if drift < 15% (SHADOW OK), exit 1 if drift >= 15%.
# ────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SYSTEMS=(day_type chart_5min tick_reversal woodies tpo killzone)
PHASE="${1:-SHADOW}"

echo "═══════════════════════════════════════════════════════════════"
echo " MEMS26 V9 — R3 Spec Compliance Audit"
echo " Phase: ${PHASE}"
echo " Date:  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Phase thresholds ──
case "$PHASE" in
    LIVE)   MAX_DRIFT=5  ;;
    SIM)    MAX_DRIFT=10 ;;
    SHADOW) MAX_DRIFT=15 ;;
    *)      MAX_DRIFT=15 ;;
esac

TOTAL_REQ=0
TOTAL_IMPL=0
TOTAL_PARTIAL=0
TOTAL_MISSING=0
AUDIT_PASS=true

echo "┌──────────────────┬───────┬──────┬─────────┬─────────┬────────┐"
echo "│ System           │ Total │ Impl │ Partial │ Missing │ Drift% │"
echo "├──────────────────┼───────┼──────┼─────────┼─────────┼────────┤"

for sys in "${SYSTEMS[@]}"; do
    MANIFEST="$ROOT_DIR/backend/v9/systems/$sys/compliance_manifest.yaml"

    if [ ! -f "$MANIFEST" ]; then
        echo "│ $sys             │  N/A  │  N/A │   N/A   │   N/A   │  N/A   │"
        continue
    fi

    # Parse manifest summary section
    total=$(grep "total_requirements:" "$MANIFEST" | head -1 | awk '{print $2}')
    impl=$(grep "implemented:" "$MANIFEST" | head -1 | awk '{print $2}')
    partial=$(grep "partial:" "$MANIFEST" | head -1 | awk '{print $2}')
    missing=$(grep "missing:" "$MANIFEST" | head -1 | awk '{print $2}')

    if [ -z "$total" ] || [ "$total" = "0" ]; then
        drift="0.0"
    else
        drift=$(python3 -c "print(round(($missing + $partial) / $total * 100, 1))")
    fi

    # Pad system name
    printf "│ %-16s │ %5s │ %4s │ %7s │ %7s │ %5s%% │\n" \
        "$sys" "$total" "$impl" "$partial" "$missing" "$drift"

    TOTAL_REQ=$((TOTAL_REQ + total))
    TOTAL_IMPL=$((TOTAL_IMPL + impl))
    TOTAL_PARTIAL=$((TOTAL_PARTIAL + partial))
    TOTAL_MISSING=$((TOTAL_MISSING + missing))
done

echo "├──────────────────┼───────┼──────┼─────────┼─────────┼────────┤"

if [ "$TOTAL_REQ" -gt 0 ]; then
    OVERALL_DRIFT=$(python3 -c "print(round(($TOTAL_MISSING + $TOTAL_PARTIAL) / $TOTAL_REQ * 100, 1))")
else
    OVERALL_DRIFT="0.0"
fi

printf "│ %-16s │ %5s │ %4s │ %7s │ %7s │ %5s%% │\n" \
    "TOTAL" "$TOTAL_REQ" "$TOTAL_IMPL" "$TOTAL_PARTIAL" "$TOTAL_MISSING" "$OVERALL_DRIFT"
echo "└──────────────────┴───────┴──────┴─────────┴─────────┴────────┘"
echo ""

# ── Run compliance tests ──
echo "Running compliance tests..."
echo ""

TEST_DIR="$ROOT_DIR/tests/v9/compliance"
if [ -d "$TEST_DIR" ]; then
    cd "$ROOT_DIR"
    if python3 -m pytest "$TEST_DIR" -v --tb=short 2>&1; then
        echo ""
        echo "All compliance tests PASSED."
    else
        echo ""
        echo "Some compliance tests FAILED."
        AUDIT_PASS=false
    fi
else
    echo "No compliance test directory found at $TEST_DIR"
    AUDIT_PASS=false
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " VERDICT"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo " Phase:          ${PHASE}"
echo " Max drift:      ${MAX_DRIFT}%"
echo " Actual drift:   ${OVERALL_DRIFT}%"
echo " Total tests:    ${TOTAL_REQ} requirements across 6 systems"
echo " Implemented:    ${TOTAL_IMPL}"
echo " Partial:        ${TOTAL_PARTIAL}"
echo " Missing:        ${TOTAL_MISSING}"
echo ""

# Compare drift to threshold
DRIFT_OK=$(python3 -c "print('YES' if $OVERALL_DRIFT < $MAX_DRIFT else 'NO')")

if [ "$DRIFT_OK" = "YES" ] && [ "$AUDIT_PASS" = "true" ]; then
    echo " RESULT: PASS — drift ${OVERALL_DRIFT}% < ${MAX_DRIFT}% threshold"
    echo " ${PHASE} gate: OPEN"
    exit 0
else
    echo " RESULT: FAIL — drift ${OVERALL_DRIFT}% >= ${MAX_DRIFT}% threshold"
    echo " ${PHASE} gate: BLOCKED"
    exit 1
fi
