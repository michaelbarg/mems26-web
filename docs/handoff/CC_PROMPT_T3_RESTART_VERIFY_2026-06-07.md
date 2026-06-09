# CC Prompt — T3 fix: restart SHADOW + verify live (2026-06-07)

**Context:** The T3 root-fix is now committed (`4d79a2d` backend, `0be56ab`
frontend, `c0c7ea9` boards) on `stabilize/mems26-local-truth-2026-05-16`.
Root: `t3=0.0` was a phantom (unreachable) target on the C3 leg because
`active_trade_manager/monitor.py:104` treats `t3 is not None` as a live
target. Fix = `None` end-to-end. **The running backend still holds the old
`0.0` code — it must be restarted to load the fix.**

Follow `CC_HANDOFF_CONTRACT.md` + `CC_VERIFICATION_PROTOCOL.md`. Every claim =
command + raw output (Rule 5). Diagnose-first, read-only before any change.

---

## Step 0 — confirm the commits are checked out (read-only)
```
cd /Users/michael/Downloads/mems26_web_git
git log --oneline -3        # expect c0c7ea9, 0be56ab, 4d79a2d on top
git grep -n '"t3": None\|t3_price' backend/v9/systems/five_min/five_min_system.py | head
```
Paste raw output. If HEAD is not on those commits, STOP and report.

## Step 1 — pre-restart snapshot (read-only)
```
lsof -i :8000              # expect a SINGLE uvicorn (no duplicate)
curl -s localhost:8000/health    # note mode + alive
ps aux | grep "uvicorn backend" | grep -v grep
```

## Step 2 — restart backend ONLY (smallest change)
The fix is backend-only; the frontend is hot-reload. Restart just uvicorn,
not the bridge/Sierra (don't disturb the data path):
```
# stop the running backend (screen session is mems26_backend)
pkill -f "uvicorn backend.main:app"
sleep 3
lsof -i :8000              # expect EMPTY before restart
# start it back the same way start_all.sh does:
cd /Users/michael/Downloads/mems26_web_git
screen -dmS mems26_backend bash -c 'ulimit -n 10240 2>/dev/null; [ -f .env ] && set -a && source .env && set +a; python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 2>&1 | tee /tmp/backend.log'
sleep 5
lsof -i :8000             # expect a SINGLE uvicorn again
curl -s localhost:8000/health    # expect alive:true, mode:shadow
```
(If you prefer the blessed path, `bash scripts/restart_all.sh` restarts
everything — only if the bridge/Sierra are confirmed healthy first.)

## Step 3 — verify the fix is LIVE (Rule 5)
1. **Code loaded:** `tail -40 /tmp/backend.log` → clean startup, no import error.
2. **No regression in health latency:** `curl -s -w "%{time_total}\n" -o /dev/null localhost:8000/health` → <0.1s.
3. **T3 passthrough (the actual fix)** — this needs a fresh S2 setup on a
   **Trend** day (Trend_Normal=4R / Trend_DD=4R-cap carry a real T3; Variation
   = trail = `None`). Markets are closed on 2026-06-07, so this verifies at
   **Monday RTH**: when S2 fires on a Trend day, the new trade row must show
   `t3` = a real price (Trend) or `null` (trail) — **never `0.0`**:
   ```
   curl -s localhost:8000/api/v9/trades/recent | python3 -m json.tool | grep -E '"t3"|"t3_label"|"day_type"'
   ```
   Existing pre-restart trades keep `t3=0.0` (the frontend renders 0.0 as "—");
   only trades created **after** the restart carry the corrected value.

## NOT-DONE / open after this
- **🔴 LIVE-gate (B5):** `0.0→None` changes C3 management on Trend days
  (fixed target vs. trail). Requires a SHADOW soak on a real Trend day + an
  explicit Michael approval before LIVE. Do NOT flip LIVE on this alone.
- **OPEN decision (Michael):** in Variation, T3 stays `trail` per the spec
  (`targets_table.py`). Changing it to a fixed T3 is a spec change, not a bug.
- Paste raw output for every step above; if any step can't be verified
  (e.g. closed market for Step 3.3), say so explicitly — don't claim "works".
