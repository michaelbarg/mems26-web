#!/usr/bin/env bash
# AP-A02: All Redis keys must use mems26: prefix (not bare v9:)
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Search for bare v9: prefix in Redis key definitions (not channel names for WS)
# Allowed patterns: "v9:" in WS channel names and pub/sub channels (not Stream keys)
ALLOWED_FILES="ws_manager.py|websocket.ts|events.ts|alerts.py|events.py"

hits=$(grep -rn '"v9:' "$REPO_ROOT/backend/" "$REPO_ROOT/bridge/" 2>/dev/null \
    | grep -v '__pycache__' \
    | grep -v '.pyc' \
    | grep -vE "$ALLOWED_FILES" \
    | grep -v 'mems26:v9:' \
    | grep -v '# ' \
    || true)

if [[ -n "$hits" ]]; then
    echo "FAIL: Bare v9: prefix found (should be mems26:v9:) — AP-A02:"
    echo "$hits"
    exit 1
fi
echo "PASS: All Redis keys use mems26: prefix"
