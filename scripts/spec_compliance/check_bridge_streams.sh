#!/usr/bin/env bash
# AP-A01: All bridge streams must extend BaseV9Stream or use mems26: prefix
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STREAMS_DIR="$REPO_ROOT/bridge/v9_streams"

failures=""
for f in "$STREAMS_DIR"/*_stream.py; do
    [[ -f "$f" ]] || continue
    basename=$(basename "$f")
    [[ "$basename" == "base_stream.py" ]] && continue

    # Must either extend BaseV9Stream or use mems26: prefix
    has_base=$(grep -c 'BaseV9Stream\|base_stream' "$f" || true)
    has_prefix=$(grep -c 'mems26:' "$f" || true)

    if (( has_base == 0 && has_prefix == 0 )); then
        failures="${failures}  $basename: no BaseV9Stream inheritance and no mems26: prefix\n"
    fi
done

if [[ -n "$failures" ]]; then
    echo "FAIL: Bridge stream architecture violations (AP-A01):"
    echo -e "$failures"
    exit 1
fi
echo "PASS: All bridge streams follow architecture pattern"
