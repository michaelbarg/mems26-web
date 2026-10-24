#!/bin/bash
# read-only: where is each flag read in the code (backend + scripts/fwd_harness.py), excluding tests
cd /Users/michael/Downloads/mems26_web_git
for f in "$@"; do
  b=$(grep -rln --include='*.py' "$f" backend 2>/dev/null | grep -v '/tests/' | grep -v __pycache__ | tr '\n' ' ')
  h=$(grep -c "$f" scripts/fwd_harness.py 2>/dev/null)
  t=$(grep -rln --include='*.py' "$f" tests backend/v9/tests 2>/dev/null | wc -l | tr -d ' ')
  echo "$f | backend: ${b:-<none>} | fwd_harness refs: $h | test files: $t"
done
