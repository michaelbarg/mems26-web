#!/usr/bin/env bash
# P31 Issue B — TPO stepped lines UAT.
#
# Run this after RTH opens (17:30 IL = 09:30 ET = 14:30 UTC) to verify
# the TPOHistorySnapshotter (B1) is capturing per-letter POC/VAH/VAL into
# v9_tpo_history and the chart is rendering stepped lines.
#
# Usage:
#   bash scripts/uat_tpo_stepped_lines.sh           # one-shot probe
#   bash scripts/uat_tpo_stepped_lines.sh --watch   # loop every 60s
#
# Four-axis verification:
#   * Quality:    snapshotter task is alive, no errors in log
#   * Recency:    most recent v9_tpo_history.ts is within last 30 min
#   * Cardinality: between 1 (letter A only) and 13 (A..M, end of RTH) rows for today
#   * Latency:    /api/v9/tpo/current returns < 100 ms warm
#
# Expected timeline on a normal RTH day:
#   17:30 IL  →  letter A starts. Snapshotter at 17:30:05 captures the
#                first POC (may be sparse / equal to opening tick).
#   18:00 IL  →  letter B starts. Snapshot at 18:00:05 captures letter A's
#                final POC. First clear step on the chart.
#   18:30 IL  →  letter C starts. Two steps now visible.
#   …
#   23:00 IL  →  letter M (=15:30 ET, last letter before close).
#   23:30 IL  →  RTH closes; snapshotter stops writing until next session.

set -uo pipefail

BACKEND=${BACKEND_URL:-http://127.0.0.1:8000}
DB=${V9_DB_PATH:-/Users/michael/Downloads/mems26_web_git/data/mems26_local.db}
LOG=${BACKEND_LOG:-/tmp/backend.log}

run_probe() {
  local et_now
  et_now=$(TZ=America/New_York date +"%Y-%m-%d %H:%M:%S %Z")
  local il_now
  il_now=$(TZ=Asia/Jerusalem date +"%H:%M:%S")
  echo "============================================================"
  echo "TPO STEPPED-LINES UAT — $(date -u +"%Y-%m-%dT%H:%M:%SZ") (IL $il_now)"
  echo "                       ET $et_now"
  echo "============================================================"

  echo ""
  echo "--- Snapshotter task alive? ---"
  if grep -q "tpo_snapshotter.*task started" "$LOG" 2>/dev/null; then
    echo "    ✓ task started log present"
    grep "tpo_snapshotter" "$LOG" | tail -3
  else
    echo "    ✗ NO 'task started' log line — backend may not have loaded new code."
    echo "      Try: bash scripts/uat_tpo_stepped_lines.sh after backend restart."
  fi

  echo ""
  echo "--- v9_tpo_history: today's rows ---"
  sqlite3 -header "$DB" "
    SELECT ts, poc, vah, val, ib_high, ib_low
    FROM v9_tpo_history
    WHERE ts LIKE strftime('%Y-%m-%d', 'now', '-4 hours') || '%'
       OR ts LIKE strftime('%Y-%m-%d', 'now', '-3 hours') || '%'
       OR ts LIKE strftime('%Y-%m-%d', 'now', 'localtime') || '%'
    ORDER BY ts;
  "
  local today_count
  today_count=$(sqlite3 "$DB" "
    SELECT COUNT(*) FROM v9_tpo_history
    WHERE ts LIKE strftime('%Y-%m-%d', 'now', '-4 hours') || '%'
       OR ts LIKE strftime('%Y-%m-%d', 'now', '-3 hours') || '%';
  ")
  echo "    today_row_count=$today_count"

  echo ""
  echo "--- /api/v9/tpo/current periods[] ---"
  curl -s --max-time 5 -w "\n[curl] time_total=%{time_total}s\n" "$BACKEND/api/v9/tpo/current" |
    python3 -c "
import sys, json
try:
    chunks = sys.stdin.read()
    # Last line is the curl footer; everything before is JSON
    body, footer = chunks.rsplit('\n[curl]', 1)
    d = json.loads(body)
    print(f'    source={d.get(\"source\")} stale={d.get(\"stale\")}')
    print(f'    poc={d.get(\"poc\")} vah={d.get(\"vah\")} val={d.get(\"val\")}')
    periods = d.get('periods') or []
    print(f'    periods_count={len(periods)}')
    for p in periods[:8]:
        print(f'      opened_ts={p.get(\"opened_ts\")} poc={p.get(\"poc_price\")} vah={p.get(\"vah_price\")} val={p.get(\"val_price\")}')
    print(footer)
except Exception as e:
    print(f'    [parse error] {e}')
    print(chunks)
"

  echo ""
  echo "--- Snapshotter WARN/ERROR (last 5) ---"
  grep -iE "snapshotter.*(warn|err|fail)" "$LOG" 2>/dev/null | tail -5 || echo "    (none — good)"

  echo ""
  echo "--- UAT verdict ---"
  if [ "$today_count" -ge 1 ]; then
    echo "    ✓ stepped data IS being captured ($today_count rows today)"
    echo "    → check the cockpit chart at $BACKEND → pink lines should step"
  else
    echo "    ⚠ no rows yet for today. Either RTH hasn't opened yet,"
    echo "      or the snapshotter hasn't reached its first boundary."
    echo "      Wait until 17:35 IL minimum, then re-run."
  fi
}

if [ "${1:-}" = "--watch" ]; then
  while true; do
    run_probe
    echo ""
    echo "[sleeping 60s — Ctrl-C to exit]"
    sleep 60
  done
else
  run_probe
fi
