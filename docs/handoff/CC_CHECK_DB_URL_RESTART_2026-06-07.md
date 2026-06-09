# CC — check DATABASE_URL in the running backend; restart if missing

Context: the backend log shows `sqlite3.DatabaseError: database disk image is
malformed` on `v9_bars_5min` — the stack must be on local Postgres ONLY
(CLAUDE.md §DB). `DATABASE_URL` lived only in `start_all.sh`, not `.env`, so a
restart that bypassed start_all.sh may have come up on SQLite. `.env` has now
been fixed (Cowork added `DATABASE_URL=postgresql://localhost/mems26`).

Run exactly this (writes the result for Cowork):

```bash
cd /Users/michael/Downloads/mems26_web_git
DBURL=$(ps eww $(pgrep -f "uvicorn backend.main") | tr ' ' '\n' | grep '^DATABASE_URL=')
echo "running backend: ${DBURL:-DATABASE_URL MISSING}"

if [ "$DBURL" != "DATABASE_URL=postgresql://localhost/mems26" ]; then
  echo "-> wrong/missing DB URL: restarting backend (env-loader will pick .env up)"
  pkill -f "uvicorn backend.main:app"; sleep 3
  screen -dmS mems26_backend bash -c 'ulimit -n 10240 2>/dev/null; cd /Users/michael/Downloads/mems26_web_git && [ -f .env ] && set -a && source .env && set +a; python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 2>&1 | tee /tmp/backend.log'
  sleep 6
fi

{
  echo "=== DATABASE_URL in running process ==="
  ps eww $(pgrep -f "uvicorn backend.main") | tr ' ' '\n' | grep '^DATABASE_URL=' || echo "MISSING"
  echo
  echo "=== flags still ON? ==="
  ps eww $(pgrep -f "uvicorn backend.main") | tr ' ' '\n' \
    | grep -E "S2_ATR_RELATIVE|S3_RELATIVE|S1_CVD_OPENING|S1_IB_WIDTH_ATR|S1_DAYTYPE_STAGING|S2_VSA_VOLUME|S3_MUTE" | sort
  echo
  echo "=== health ==="
  curl -s localhost:8000/health
  echo
  echo "=== any sqlite errors after restart? (should be none on the PG engine) ==="
  tail -30 /tmp/backend.log | grep -iE "sqlite|malformed|Traceback" || echo "clean"
} > docs/reports/DB_URL_CHECK_2026-06-07.txt 2>&1
echo "written to docs/reports/DB_URL_CHECK_2026-06-07.txt"
```

Note: even with correct PG, one known residual exists — the legacy SQLite
*hydration fallback* in main.py (CLAUDE.md §DB residual, slated for removal).
If the only sqlite hits are the startup hydration of old history, say so
explicitly; if live reads/writes hit sqlite, that's the critical case.
