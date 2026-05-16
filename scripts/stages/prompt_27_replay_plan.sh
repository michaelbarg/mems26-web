#!/usr/bin/env bash
# Stage: prompt_27_replay_plan — dry run: just verify plan doc exists
set -euo pipefail
cd /Users/michael/Downloads/mems26_web_git
echo "=== Replay Validation Plan Check ==="
test -f docs/reports/PROMPT27_REPLAY_VALIDATION_PLAN.md && echo "✅ Plan doc exists" || { echo "FAIL: Plan doc missing"; exit 1; }
echo ""
echo "=== Quick Integration Tests ==="
python3 -m pytest tests/atomic/test_cross_system_integration.py -q --tb=no 2>&1
echo ""
echo "✅ Replay plan stage passed"
