#!/usr/bin/env bash
# MEMS26 Registry Health Audit
# Checks MEMS26_REGISTRY.yaml for completeness and health metrics

set -euo pipefail

REGISTRY="${1:-MEMS26_REGISTRY.yaml}"
cd "$(dirname "$0")/.."

if [ ! -f "$REGISTRY" ]; then
  echo "ERROR: $REGISTRY not found"
  exit 1
fi

echo "=== MEMS26 Registry Health Audit ==="
echo "File: $REGISTRY"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Total entries
TOTAL=$(grep -c "^  - id: REQ-" "$REGISTRY" || true)
echo "Total requirements: $TOTAL"
echo ""

# Distribution by category
echo "--- Distribution by Category ---"
for CAT in S DATA ADMIN UI EXPLAIN INFRA GOVERN; do
  COUNT=$(grep -c "^  - id: REQ-${CAT}-" "$REGISTRY" || true)
  echo "  REQ-${CAT}-*: $COUNT"
done
echo ""

# Distribution by status
echo "--- Distribution by Status ---"
for STATUS in SPECIFIED IN_PROGRESS IMPLEMENTED VERIFIED LIVE ARCHIVED; do
  COUNT=$(grep -c "status: ${STATUS}$" "$REGISTRY" || true)
  echo "  ${STATUS}: $COUNT"
done
echo ""

# Distribution by severity
echo "--- Distribution by Severity ---"
for SEV in CRITICAL HIGH MEDIUM LOW; do
  COUNT=$(grep -c "severity: ${SEV}$" "$REGISTRY" || true)
  echo "  ${SEV}: $COUNT"
done
echo ""

# SPECIFIED with no owner (grep-based: count blocks where status=SPECIFIED and owner_worker=null)
SPEC_NO_OWNER=$(awk '/^  - id: REQ-/{block=""} {block=block"\n"$0} /owner_worker: null/{if(block ~ /status: SPECIFIED/) count++} END{print count+0}' "$REGISTRY")
echo "--- Health Warnings ---"
echo "  SPECIFIED with no owner: $SPEC_NO_OWNER"

# CRITICAL items not yet IMPLEMENTED/VERIFIED/LIVE
CRIT_NOT_IMPL=$(awk '/^  - id: REQ-/{block=""} {block=block"\n"$0} /^$/{if(block ~ /severity: CRITICAL/ && block !~ /status: (IMPLEMENTED|VERIFIED|LIVE)/) count++} END{print count+0}' "$REGISTRY")
echo "  CRITICAL not yet IMPLEMENTED: $CRIT_NOT_IMPL"

# IMPLEMENTED with no test_path
IMPL_NO_TEST=$(awk '/^  - id: REQ-/{block=""} {block=block"\n"$0} /test_path: null/{if(block ~ /status: (IMPLEMENTED|VERIFIED)/) count++} END{print count+0}' "$REGISTRY")
echo "  IMPLEMENTED with no test_path: $IMPL_NO_TEST"

# Duplicate IDs
DUPES=$(grep "^  - id: REQ-" "$REGISTRY" | sort | uniq -d | wc -l | tr -d ' ')
echo "  Duplicate IDs: $DUPES"

echo ""

# SHADOW blockers summary (CRITICAL + not yet implemented)
echo "--- SHADOW Blockers (CRITICAL + SPECIFIED/IN_PROGRESS) ---"
awk '
/^  - id: REQ-/ { id=$NF; name=""; sev=""; stat="" }
/name: /         { sub(/.*name: "/, ""); sub(/"$/, ""); name=$0 }
/severity: /     { sev=$NF }
/status: /       { stat=$NF }
/notes: /        {
  if (sev == "CRITICAL" && (stat == "SPECIFIED" || stat == "IN_PROGRESS"))
    printf "  %s: %s\n", id, name
}
' "$REGISTRY"

echo ""
echo "=== Audit Complete ==="
