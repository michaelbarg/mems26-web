#!/usr/bin/env bash
# Interactive Anthropic API key setup for MEMS26
# Usage: ./setup_anthropic_key.sh

set -euo pipefail

ENV_FILE="$(dirname "$0")/.env"

# 1. Check if .env already has key
if [[ -f "$ENV_FILE" ]] && grep -q "^ANTHROPIC_API_KEY=sk-ant-" "$ENV_FILE" 2>/dev/null; then
    echo "⚠️  .env already has an Anthropic key."
    read -rp "Overwrite? [y/N]: " confirm
    [[ "$confirm" != "y" ]] && { echo "Aborted."; exit 0; }
fi

# 2. Prompt (silent input)
echo ""
echo "Paste your Anthropic API key (starts with sk-ant-api03-)."
echo "Key will NOT be displayed. Press Enter when done."
read -rsp "Key: " KEY
echo ""

# 3. Validate format
if [[ ! "$KEY" =~ ^sk-ant-api[0-9]{2}-[A-Za-z0-9_-]+$ ]]; then
    echo "❌ Invalid format. Expected: sk-ant-api03-..."
    exit 1
fi

# 4. Validate against API (cheap call: 1 token, smallest model)
echo "Validating key against Anthropic API..."
RESPONSE=$(curl -s -w "\n%{http_code}" https://api.anthropic.com/v1/messages \
    -H "x-api-key: $KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d '{
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}]
    }')

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" != "200" ]]; then
    ERROR_TYPE=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('error',{}).get('type','unknown'))" 2>/dev/null || echo "parse_error")
    echo "❌ API rejected key (HTTP $HTTP_CODE, error: $ERROR_TYPE)"
    case "$ERROR_TYPE" in
        authentication_error)
            echo "   → Key is invalid or revoked. Re-create at console.anthropic.com → API Keys"
            ;;
        permission_error)
            echo "   → Key valid but lacks permissions. Check workspace assignment."
            ;;
        rate_limit_error)
            echo "   → Rate limited. Wait 30s and retry."
            ;;
        *)
            echo "   → Unknown error. Body: $BODY"
            ;;
    esac
    exit 1
fi

echo "✅ Key valid."
echo "   Validated via Haiku 4.5 (1-token call, ~\$0.000005)"

# 5. Write .env
cat > "$ENV_FILE" <<EOF
# MEMS26 Anthropic API credentials
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# DO NOT COMMIT THIS FILE
# Monthly cap: \$150 (configured in Anthropic Console)
ANTHROPIC_API_KEY=$KEY
ANTHROPIC_KEY_NAME=MEMS26-AGENTS
EOF

chmod 600 "$ENV_FILE"

# 6. Verify gitignored
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [[ -n "$GIT_ROOT" ]]; then
    if ! git check-ignore -q "$ENV_FILE" 2>/dev/null; then
        echo "tools/anthropic-setup/.env" >> "$GIT_ROOT/.gitignore"
        echo "Added to .gitignore"
    fi
fi

echo ""
echo "✅ Key saved to: $ENV_FILE (chmod 600)"
echo "   Validate later with: python3 validate_key.py"
