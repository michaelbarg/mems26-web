#!/usr/bin/env bash
# Stage: prompt_26_replay_clock_smoke — verify replay clock consumers
set -euo pipefail
cd /Users/michael/Downloads/mems26_web_git
echo "=== Replay Clock Smoke Test ==="
python3 -m pytest tests/atomic/test_replay_clock_consumers.py -q --tb=short 2>&1
echo ""
echo "=== Market Clock Module ==="
python3 -c "
from backend.v9.services.market_clock import get_clock, now_et, ClockMode
c = get_clock()
print(f'Mode: {c.mode}')
snap = c.current()
print(f'Status: {snap.status}')
print(f'now_et: {snap.now_et}')
"
echo ""
echo "✅ Replay clock smoke passed"
