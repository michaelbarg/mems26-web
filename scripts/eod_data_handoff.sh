#!/bin/bash
# eod_data_handoff.sh — daily data packet from the TRADING machine to git,
# so the ANALYST machine can read everything it collected.
#
# Michael ruling 2026-08-13 (~12:00): once mac-2 is certified it becomes the
# DEFAULT trader, and mac-1 (dev) "צריך גישה לכל המידע שהוא אוסף — לנתח את
# הסוף-יום שלו ולהציע איך לשפר את המערכת". Rails: git (both machines already
# sync through it), no network coupling, packets are auditable evidence.
#
# Runs on WHICHEVER machine trades (LaunchAgent com.mems26.eod_handoff,
# 23:05 IL Sun-Fri). Output: data_handoff/<MACHINE_TAG>/<YYYY-MM-DD>/
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

TAG=$(grep -a "^MACHINE_TAG" .env 2>/dev/null | cut -d= -f2)
TAG=${TAG:-$(hostname -s)}
DAY=$(date "+%Y-%m-%d")
OUT="data_handoff/$TAG/$DAY"
mkdir -p "$OUT"

echo "[eod-handoff] $TAG $DAY → $OUT"

# 1. today's trades (live+shadow) from local Postgres
python3 - << 'PYEOF' > "$OUT/trades.json" 2>"$OUT/trades.err" || echo "[eod-handoff] trades export failed (see trades.err)"
import json, psycopg2
conn = psycopg2.connect("postgresql://localhost/mems26")
cur = conn.cursor()
cur.execute("""
SELECT id, mode, firing_system, pattern_id_at_entry, direction, state,
       entry_ts::text, entry_price, stop, t1, t2, t3,
       exit_ts::text, exit_price, exit_reason, pnl_usd, pnl_sierra,
       outcome, day_type_at_entry, session_at_entry
FROM v9_trades
WHERE (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date = current_date
ORDER BY entry_ts""")
cols = [d[0] for d in cur.description]
rows = [dict(zip(cols, (str(v) if v is not None else None for v in r))) for r in cur.fetchall()]
print(json.dumps(rows, ensure_ascii=False, indent=1))
PYEOF

# 2. today's gateway decisions (the rotated file is today-only by design, F6)
cp "$HOME/SierraChart_Data/v9_export/gateway_decisions.jsonl" "$OUT/gateway_decisions.jsonl" 2>/dev/null || echo "[]" > "$OUT/gateway_decisions.jsonl"

# 3. fills journal (full — small) + sierra_state snapshot
cp "$HOME/SierraChart_Data/v9_export/trade_fills_journal.jsonl" "$OUT/trade_fills_journal.jsonl" 2>/dev/null || true
cp "$HOME/SierraChart_Data/v9_export/sierra_state.json" "$OUT/sierra_state_eod.json" 2>/dev/null || true

# 4. health digest for the day (grep-level evidence, not full logs)
{
  echo "day=$DAY machine=$TAG generated=$(date '+%H:%M:%S %Z')"
  echo "order_failed_count=$(grep -ac 'ORDER_FAILED' /tmp/backend.err.log 2>/dev/null || echo 0)"
  echo "bypass_revoked_count=$(grep -ac 'BYPASS REVOKED' /tmp/backend.err.log 2>/dev/null || echo 0)"
  echo "boot_line=$(grep -a 'env_loader' /tmp/backend.err.log 2>/dev/null | tail -1)"
  echo "flag_guard=$(python3 scripts/flag_guard.py 2>&1 | tail -1)"
  echo "git_head=$(git rev-parse --short HEAD)"
} > "$OUT/health_digest.txt"

# 5. ops log for the day (if exists)
cp "docs/reports/OPS_LOG_$DAY.md" "$OUT/" 2>/dev/null || true

# 6. commit + push — the payload path ONLY.
# NEVER stash/pull here (T-261, cowork 2026-09-06). This repo is written concurrently by
# cc-macbook. Measured: stash -> pull --rebase -> stash pop leaves CONFLICT MARKERS inside
# live .py files (UU state) whenever the remote touched the same file, and `|| true` hides
# it. `git pull --rebase --autostash` is NOT a fix either: it produces the identical broken
# tree and still exits 0 ("Applying autostash resulted in conflicts").
# Committing an explicit pathspec leaves the working tree untouched; a rejected push is
# REPORTED, never "repaired" by mutating someone else's work.
git add "data_handoff/$TAG/$DAY"
if git diff --cached --quiet -- "data_handoff/$TAG/$DAY"; then
  echo "[eod-handoff] nothing to commit for $TAG/$DAY"
elif git commit --quiet -m "eod-handoff($TAG): $DAY packet — trades/decisions/fills/state/health" -- "data_handoff/$TAG/$DAY"; then
  if git push --quiet; then
    echo "[eod-handoff] PUSHED"
  else
    echo "[eod-handoff] PUSH REJECTED — remote moved. Commit is LOCAL and safe; NOT pulling (tree may be dirty). Integrate manually with a clean 'git pull --rebase'."
  fi
else
  echo "[eod-handoff] commit FAILED — check manually"
fi
