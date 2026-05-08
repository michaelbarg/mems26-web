#!/usr/bin/env bash
# MEMS26 Weekend Status → Slack Reporter
#
# Runs status_report.py and posts the output to #cc-master channel.
#
# Usage:
#   ./report_to_slack.sh              # Post to Slack
#   ./report_to_slack.sh --dry-run    # Print what would be posted (no Slack call)
#
# Requires:
#   SLACK_BOT_TOKEN environment variable (xoxb-...)
#   Channel: #cc-master must exist

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHANNEL="cc-master"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

# Generate report in Slack format
REPORT=$(python3 "$SCRIPT_DIR/status_report.py" --slack)

if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would post to #${CHANNEL}:"
    echo ""
    echo "$REPORT"
    exit 0
fi

# Check for Slack token
if [[ -z "${SLACK_BOT_TOKEN:-}" ]]; then
    echo "ERROR: SLACK_BOT_TOKEN not set."
    echo "Export it before running: export SLACK_BOT_TOKEN=xoxb-..."
    echo ""
    echo "For now, here's the report:"
    echo "$REPORT"
    exit 1
fi

# Post to Slack
RESPONSE=$(curl -s -X POST "https://slack.com/api/chat.postMessage" \
    -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c "
import json, sys
msg = sys.stdin.read()
print(json.dumps({'channel': '${CHANNEL}', 'text': msg, 'mrkdwn': True}))
" <<< "$REPORT")")

# Check response
OK=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('ok', False))" 2>/dev/null || echo "False")

if [[ "$OK" == "True" ]]; then
    echo "Posted to #${CHANNEL}"
else
    echo "Failed to post to Slack:"
    echo "$RESPONSE"
    exit 1
fi
