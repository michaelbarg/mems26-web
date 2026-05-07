#!/usr/bin/env bash
# Interactive Slack Bot Token setup for MEMS26-OPS
# Usage: ./setup_token.sh

set -euo pipefail

ENV_FILE="$(dirname "$0")/.env"

# 1. Check if .env already exists with token
if [[ -f "$ENV_FILE" ]] && grep -q "^SLACK_BOT_TOKEN=xoxb-" "$ENV_FILE" 2>/dev/null; then
    echo "⚠️  .env already exists with a token."
    read -rp "Overwrite? [y/N]: " confirm
    [[ "$confirm" != "y" ]] && { echo "Aborted."; exit 0; }
fi

# 2. Prompt for token (no echo — like password)
echo ""
echo "Paste your Slack Bot User OAuth Token (starts with xoxb-)."
echo "Token will NOT be displayed as you type/paste. Press Enter when done."
read -rsp "Token: " TOKEN
echo ""

# 3. Validate format
if [[ ! "$TOKEN" =~ ^xoxb-[A-Za-z0-9-]+$ ]]; then
    echo "❌ Invalid format. Token must start with 'xoxb-' and contain only alphanumerics + dashes."
    exit 1
fi

# 4. Validate against Slack API (auth.test)
echo "Validating token against Slack API..."
RESPONSE=$(curl -s -X POST https://slack.com/api/auth.test \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/x-www-form-urlencoded")

OK=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('ok', False))")

if [[ "$OK" != "True" ]]; then
    ERROR=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error', 'unknown'))")
    echo "❌ Slack API rejected token: $ERROR"
    echo "   Re-check OAuth & Permissions page → re-install app if needed."
    exit 1
fi

TEAM=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('team', 'unknown'))")
BOT_USER=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('user', 'unknown'))")

echo "✅ Token valid."
echo "   Workspace: $TEAM"
echo "   Bot user:  $BOT_USER"

# 5. Warn if workspace name mismatch
if [[ "$TEAM" != "MEMS26-OPS" ]]; then
    echo ""
    echo "⚠️  WARNING: Workspace is '$TEAM', expected 'MEMS26-OPS'."
    read -rp "Continue anyway? [y/N]: " confirm
    [[ "$confirm" != "y" ]] && { echo "Aborted."; exit 0; }
fi

# 6. Write .env with strict permissions
cat > "$ENV_FILE" <<EOF
# MEMS26-OPS Slack credentials
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# DO NOT COMMIT THIS FILE
SLACK_BOT_TOKEN=$TOKEN
SLACK_WORKSPACE=$TEAM
SLACK_BOT_USER=$BOT_USER
EOF

chmod 600 "$ENV_FILE"

# 7. Verify gitignore covers it
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [[ -n "$GIT_ROOT" ]]; then
    if ! git check-ignore -q "$ENV_FILE" 2>/dev/null; then
        echo ""
        echo "⚠️  .env is NOT gitignored. Adding to root .gitignore..."
        echo "tools/slack-setup/.env" >> "$GIT_ROOT/.gitignore"
        echo "tools/slack-setup/.env.local" >> "$GIT_ROOT/.gitignore"
    fi
fi

echo ""
echo "✅ Token saved to: $ENV_FILE (chmod 600)"
echo "   Next: run bootstrap_channels.py (SLACK-SETUP-V1.0 prompt)"
