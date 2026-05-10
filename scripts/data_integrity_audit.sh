#!/bin/bash
# scripts/data_integrity_audit.sh
# MEMS26 Data Integrity Audit — runs at every phase transition
# Per: MEMS26_DATA_INTEGRITY_PRINCIPLE_LOCKED (Drive 1EXCgoE7XxcDzhtXxa3_QwEP7qLncWSLT9GsiY7q-KWQ)

set -e
VIOLATIONS=0
WARNINGS=0

echo "═══════════════════════════════════════════════════════════════"
echo "   MEMS26 DATA INTEGRITY AUDIT — $(date +'%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════════"
echo ""

cd /Users/michael/Downloads/mems26_web_git || { echo "🔴 Cannot cd to working dir"; exit 1; }

echo "TEST 1 — Forbidden markers (fallback/approximat/proportional/TBD)"
HITS=$(grep -rn "fallback\|approximat\|proportional.*distribut\|TBD.*data" \
       backend/v9/ bridge/ sc_study/ 2>/dev/null \
       | grep -v "test_\|/tests/\|# OK:\|/\* OK:\|//\s*OK:" \
       | wc -l | tr -d ' ')
if [ "$HITS" -gt 0 ]; then
    echo "  🔴 FAIL: $HITS hit(s)"
    grep -rn "fallback\|approximat\|proportional.*distribut\|TBD.*data" \
        backend/v9/ bridge/ sc_study/ 2>/dev/null \
        | grep -v "test_\|/tests/\|# OK:\|/\* OK:\|//\s*OK:" | head -5 | sed 's/^/      /'
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "  ✅ PASS"
fi
echo ""

echo "TEST 2 — MaintainVolumeAtPriceData (must be 1 OR have Python compensator)"
MAINTAIN_STATUS=$(grep -E "MaintainVolumeAtPriceData\s*=\s*[01]" \
                  sc_study/MES_AI_DataExport.cpp 2>/dev/null | head -1 | tr -s ' ')
PYTHON_VAP=$(ls bridge/v9_streams/vap_recompute.py 2>/dev/null | wc -l | tr -d ' ')

if echo "$MAINTAIN_STATUS" | grep -q "= 1"; then
    echo "  ✅ PASS: VAP enabled in DLL"
elif [ "$PYTHON_VAP" -eq 1 ]; then
    echo "  ✅ PASS: VAP compensated via bridge/v9_streams/vap_recompute.py"
else
    echo "  🔴 FAIL: VAP disabled in DLL and no Python compensator"
    echo "     DLL: $MAINTAIN_STATUS"
    VIOLATIONS=$((VIOLATIONS + 1))
fi
echo ""

echo "TEST 3 — Per-system data quality"
for sys in day_type chart_5min tick_reversal woodies tpo killzone; do
    if [ ! -d "backend/v9/systems/$sys" ]; then
        printf "  ⚪ %-15s not yet implemented\n" "$sys"
        continue
    fi
    HITS=$(grep -l "fallback\|approximat\|degraded\|TBD" \
           backend/v9/systems/$sys/*.py 2>/dev/null | wc -l | tr -d ' ')
    if [ "$HITS" -gt 0 ]; then
        printf "  🔴 %-15s %s file(s) with degradation markers\n" "$sys" "$HITS"
        VIOLATIONS=$((VIOLATIONS + 1))
    else
        printf "  ✅ %-15s clean\n" "$sys"
    fi
done
echo ""

echo "TEST 4 — Unbounded collections in bridge"
UNBOUNDED=$(grep -rn "\.append\|\.extend" bridge/ 2>/dev/null \
            | grep -v "deque\|maxlen\|test_\|/tests/" \
            | grep -v "# bounded:\|# OK:" \
            | wc -l | tr -d ' ')
if [ "$UNBOUNDED" -gt 50 ]; then
    echo "  🟡 WARN: $UNBOUNDED unbounded operations (review)"
    WARNINGS=$((WARNINGS + 1))
else
    echo "  ✅ PASS: $UNBOUNDED operations (within tolerance)"
fi
echo ""

echo "TEST 5 — Active violations declared in §17 of SKILL"
SKILL=".claude/MASTER_DEV_SKILL.md"
if [ -f "$SKILL" ]; then
    ACTIVE=$(grep -E "🔴 (ACTIVE )?VIOLATION" "$SKILL" | wc -l | tr -d ' ')
    if [ "$ACTIVE" -gt 0 ]; then
        echo "  🔴 BLOCK: $ACTIVE active violation(s) tracked in §17"
        grep -E "🔴" "$SKILL" | head -3 | sed 's/^/      /'
        VIOLATIONS=$((VIOLATIONS + 1))
    else
        echo "  ✅ PASS: no active 🔴 violations in §17"
    fi
else
    echo "  🟡 WARN: SKILL.md not at $SKILL"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

echo "TEST 6 — DLL version sanity"
DLL_PATH="$HOME/SierraChart/Data/MES_AI_DataExport.dll"
if [ -f "$DLL_PATH" ]; then
    VER=$(strings "$DLL_PATH" 2>/dev/null | grep -oE "v9\.[0-9]+\.[0-9]+" | head -1)
    [ -n "$VER" ] && echo "  ✅ DLL version: $VER" || echo "  🟡 DLL exists but version not detected"
else
    echo "  ⚪ DLL not deployed"
fi
echo ""

echo "TEST 7 — Latency Budget Check (bridge heartbeat + SC data age)"
LATENCY_REPORT=$(curl -s -m 3 https://mems26-web.onrender.com/health 2>/dev/null | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    hb = d.get("bridge_heartbeat_age_sec", 999)
    sc = d.get("sc_data_age_sec", 999)
    print(f"hb={hb} sc={sc}")
except:
    print("hb=999 sc=999")
' 2>/dev/null || echo "hb=999 sc=999")
HB_VAL=$(echo "$LATENCY_REPORT" | grep -oE "hb=[0-9.]+" | cut -d= -f2 | cut -d. -f1)
SC_VAL=$(echo "$LATENCY_REPORT" | grep -oE "sc=[0-9.]+" | cut -d= -f2 | cut -d. -f1)
HB_VAL=${HB_VAL:-999}
SC_VAL=${SC_VAL:-999}
if [ "$HB_VAL" -gt 30 ] || [ "$SC_VAL" -gt 30 ]; then
    echo "  🔴 FAIL: bridge_heartbeat_age=${HB_VAL}s sc_data_age=${SC_VAL}s (threshold: 30s)"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "  ✅ PASS: bridge_heartbeat_age=${HB_VAL}s sc_data_age=${SC_VAL}s"
fi
echo ""

echo "═══════════════════════════════════════════════════════════════"
if [ "$VIOLATIONS" -eq 0 ]; then
    echo "   ✅ DATA INTEGRITY: PASS"
    [ "$WARNINGS" -gt 0 ] && echo "   ($WARNINGS warning(s) — non-blocking)"
    echo "   Phase transition AUTHORIZED."
    echo "═══════════════════════════════════════════════════════════════"
    exit 0
else
    echo "   🔴 DATA INTEGRITY: $VIOLATIONS VIOLATION(S)"
    echo "   PHASE TRANSITION BLOCKED."
    echo ""
    echo "   Per LOCKED principle:"
    echo "   'No degraded data → no decisions → no trades.'"
    echo "═══════════════════════════════════════════════════════════════"
    exit 1
fi
