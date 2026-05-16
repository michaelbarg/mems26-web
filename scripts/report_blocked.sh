#!/usr/bin/env bash
# Post a concise BLOCKED summary to Slack.
#
# Usage:
#   scripts/report_blocked.sh docs/reports/BLOCKED.md

set -euo pipefail

BLOCKED_FILE="${1:-docs/reports/BLOCKED.md}"

if [[ ! -f "$BLOCKED_FILE" ]]; then
  echo "[report_blocked] missing file: $BLOCKED_FILE" >&2
  exit 1
fi

TITLE="MEMS26 BLOCKED"
BODY="$(
python3 - "$BLOCKED_FILE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(errors="replace").strip()
lines = [line for line in text.splitlines() if line.strip()]
summary = "\n".join(lines[:12])
if len(lines) > 12:
    summary += f"\n... +{len(lines)-12} more lines"
print(f"File: `{path}`\n{summary}")
PY
)"

"$(dirname "$0")/slack_notify.sh" "$TITLE" "$BODY" "warn"

