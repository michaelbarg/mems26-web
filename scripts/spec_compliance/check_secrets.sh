#!/usr/bin/env bash
# Security: No secrets in committed files
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Check tracked files only (not .env*)
tracked=$(git -C "$REPO_ROOT" ls-files 2>/dev/null || find "$REPO_ROOT" -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js')

hits=""
for pattern in 'sk-ant-' 'sk-[a-zA-Z0-9]\{20,\}' 'xoxb-' 'ghp_' 'AKIA[A-Z0-9]\{16\}'; do
    match=$(echo "$tracked" | xargs grep -ln "$pattern" 2>/dev/null \
        | grep -v '.env' \
        | grep -v 'node_modules' \
        | grep -v 'check_secrets.sh' \
        | grep -v 'pre-commit' \
        || true)
    if [[ -n "$match" ]]; then
        hits="${hits}${match}\n"
    fi
done

if [[ -n "$hits" ]]; then
    echo "FAIL: Possible secrets in committed files:"
    echo -e "$hits"
    exit 1
fi
echo "PASS: No secrets detected in committed files"
