#!/usr/bin/env bash
# AP-CC01: No test mock values in production code
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# 5412. is the canonical test price. Must not appear in production paths.
hits=$(grep -rn '5412\.' \
    "$REPO_ROOT/backend/" \
    "$REPO_ROOT/bridge/" \
    "$REPO_ROOT/frontend/v9/src/" \
    2>/dev/null \
    | grep -v '__pycache__' \
    | grep -v 'node_modules' \
    | grep -v '__tests__' \
    | grep -v 'test_' \
    | grep -v '.test.' \
    || true)

if [[ -n "$hits" ]]; then
    echo "FAIL: Test mock value '5412.' in production code (AP-CC01):"
    echo "$hits"
    exit 1
fi
echo "PASS: No test mock values in production code"
