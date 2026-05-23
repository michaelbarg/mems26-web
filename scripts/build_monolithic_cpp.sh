#!/bin/bash
# build_monolithic_cpp.sh — Generate monolith DLL for Sierra Chart remote build
# Lesson #17/#18: SCDLLName + sierrachart.h MUST be in first 10 lines
#
# Usage: ./scripts/build_monolithic_cpp.sh [--deploy]
#   --deploy: copy monolith to every known Sierra ACS_Source install

set -euo pipefail

SRCDIR="$(cd "$(dirname "$0")/../sc_study" && pwd)"
OUTFILE="$SRCDIR/MES_AI_DataExport_merged.cpp"
DEPLOY_TARGETS=(
  "$HOME/SierraChart/ACS_Source/MES_AI_DataExport.cpp"
  "$HOME/SierraChart2/ACS_Source/MES_AI_DataExport.cpp"
)

echo "=== Monolith Generator v9.2.0 ==="
echo "Source: $SRCDIR"

# Verify source files exist
for f in v9_types.h v9_exports.h v9_woodies_export.h MES_AI_DataExport.cpp; do
    if [ ! -f "$SRCDIR/$f" ]; then
        echo "ERROR: $SRCDIR/$f not found" >&2
        exit 1
    fi
done

# Extract version from modular cpp
VERSION=$(grep -o 'v9\.[0-9]\+\.[0-9]\+' "$SRCDIR/MES_AI_DataExport.cpp" | head -1)
[ -z "$VERSION" ] && VERSION="v9.2.0"

# Generate monolith
{
    echo "// MES_AI_DataExport_merged.cpp — $VERSION monolith for Sierra Chart remote build"
    echo "// Generated $(date '+%Y-%m-%d %H:%M:%S') by build_monolithic_cpp.sh"
    echo "// CRITICAL: sierrachart.h + SCDLLName MUST be in first 10 lines"
    echo ""
    echo '#include "sierrachart.h"'
    echo ""
    echo 'SCDLLName("MES_AI_DataExport")'
    echo ""
    echo "// ====== v9_types.h (inlined) ======"
    grep -v -E '#pragma once|#include "sierrachart.h"' "$SRCDIR/v9_types.h"
    echo ""
    echo "// ====== v9_exports.h (inlined) ======"
    grep -v -E '#pragma once|#include "sierrachart.h"|#include "v9_types.h"' "$SRCDIR/v9_exports.h"
    echo ""
    echo "// ====== v9_woodies_export.h (inlined) ======"
    grep -v -E '#pragma once|#include "sierrachart.h"|#include "v9_types.h"|#include <cmath>' "$SRCDIR/v9_woodies_export.h"
    echo ""
    echo "// ====== ImbLevel struct (file scope — Bug #16 fix) ======"
    echo "struct ImbLevel { float price; float buy_vol; float sell_vol; float ratio; };"
    echo ""
    echo "// ====== MES_AI_DataExport.cpp main function ======"
    grep -v -E '#include "sierrachart.h"|#include "v9_types.h"|#include "v9_exports.h"|#include "v9_woodies_export.h"|^SCDLLName' "$SRCDIR/MES_AI_DataExport.cpp" | \
    sed 's/struct ImbLevel {[^}]*};//'
} > "$OUTFILE"

# ── Verification ──────────────────────────────────────────────
LINES=$(wc -l < "$OUTFILE")
SCDLL_COUNT=$(grep -c '^SCDLLName(' "$OUTFILE")
SIERRA_COUNT=$(grep -c '#include "sierrachart.h"' "$OUTFILE")
SCDLL_LINE=$(grep -n '^SCDLLName(' "$OUTFILE" | head -1 | cut -d: -f1)
V920_COUNT=$(grep -c "v9.2" "$OUTFILE" || true)
MAINTAIN_VAP=$(grep -c "MaintainVolumeAtPriceData" "$OUTFILE")
ISNOTEMPTY=$(grep -c "IsNotEmpty" "$OUTFILE" || true)

FAIL=0
[ "$LINES" -lt 1400 ]     && echo "FAIL: only $LINES lines (need >=1400)" && FAIL=1
[ "$SCDLL_COUNT" -ne 1 ]   && echo "FAIL: SCDLLName appears $SCDLL_COUNT times (need 1)" && FAIL=1
[ "$SIERRA_COUNT" -ne 1 ]  && echo "FAIL: sierrachart.h appears $SIERRA_COUNT times (need 1)" && FAIL=1
[ "$SCDLL_LINE" -gt 10 ]   && echo "FAIL: SCDLLName at line $SCDLL_LINE (must be <=10)" && FAIL=1
[ "$MAINTAIN_VAP" -lt 1 ]  && echo "FAIL: MaintainVolumeAtPriceData missing" && FAIL=1
[ "$ISNOTEMPTY" -gt 0 ]    && echo "FAIL: IsNotEmpty still present (not valid ACSIL)" && FAIL=1

if [ "$FAIL" -ne 0 ]; then
    echo "VERIFICATION FAILED — monolith NOT safe to deploy" >&2
    exit 1
fi

echo "OK: $LINES lines, SCDLLName@line$SCDLL_LINE, 1x sierrachart.h, ${V920_COUNT}x v9.2"

# Deploy if requested
if [ "${1:-}" = "--deploy" ]; then
    deployed=0
    for DEPLOY_TARGET in "${DEPLOY_TARGETS[@]}"; do
        if [ -d "$(dirname "$DEPLOY_TARGET")" ]; then
            cp "$OUTFILE" "$DEPLOY_TARGET"
            echo "DEPLOYED to $DEPLOY_TARGET"
            deployed=1
            # Stale copy confuses Remote Build (duplicate SCDLLName, old p30.8 body).
            STALE_MERGED="$(dirname "$DEPLOY_TARGET")/MES_AI_DataExport_merged.cpp"
            if [ -f "$STALE_MERGED" ]; then
                mv "$STALE_MERGED" "${STALE_MERGED}.disabled-$(date +%Y%m%d%H%M%S)"
                echo "MOVED stale $STALE_MERGED aside (use MES_AI_DataExport.cpp only)"
            fi
        else
            echo "SKIP: $(dirname "$DEPLOY_TARGET") not found"
        fi
    done
    if [ "$deployed" -eq 0 ]; then
        echo "WARN: no ACS_Source targets found" >&2
    fi
fi

echo "=== Done ==="
