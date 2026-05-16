#!/usr/bin/env bash
# MEMS26 generic Slack notifier.
#
# Usage:
#   scripts/slack_notify.sh "Title" "Body" "good|warn|fail|info"
#
# Secret handling:
#   Reads webhook only from environment. Do not commit webhook values.

set -euo pipefail

TITLE="${1:-MEMS26 update}"
BODY="${2:-}"
LEVEL="${3:-info}"
WEBHOOK="${SLACK_UAT_WEBHOOK:-${SLACK_WEBHOOK_URL:-}}"

if [[ -z "$WEBHOOK" ]]; then
  echo "[slack_notify] SLACK_UAT_WEBHOOK/SLACK_WEBHOOK_URL not set; skipping"
  exit 0
fi

case "$LEVEL" in
  good) ICON=":white_check_mark:" ;;
  warn) ICON=":warning:" ;;
  fail) ICON=":x:" ;;
  *) ICON=":information_source:" ;;
esac

payload="$(
python3 - "$ICON" "$TITLE" "$BODY" <<'PY'
import json
import sys

icon, title, body = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps({"text": f"{icon} *{title}*\n{body}"}, ensure_ascii=False))
PY
)"

curl -s -X POST "$WEBHOOK" \
  -H "Content-Type: application/json" \
  -d "$payload" >/dev/null 2>&1 || true

