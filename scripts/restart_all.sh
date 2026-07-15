#!/bin/bash
# MEMS26 Restart All — stop + start
# Usage: bash scripts/restart_all.sh  OR  mems-restart

bash /Users/michael/Downloads/mems26_web_git/scripts/stop_all.sh
sleep 3
bash /Users/michael/Downloads/mems26_web_git/scripts/start_all.sh

# P4 (2026-07-16): liveness gate after restart — "no green, no trading".
echo "[restart_all] waiting 20s for streams to settle, then post_restart_verify…"
sleep 20
bash /Users/michael/Downloads/mems26_web_git/scripts/post_restart_verify.sh \
  || echo "[restart_all] ⚠️  post_restart_verify RED — do NOT trade until green (see above)."
