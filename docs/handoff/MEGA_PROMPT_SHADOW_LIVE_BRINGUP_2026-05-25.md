# MEGA PROMPT · SHADOW Live Bring-Up · 2026-05-25

**Owner:** Cursor agent (Michael's main thread)
**Consumer:** Claude Code (CC) — has unrestricted shell, screen, launchctl, curl
**Reviewer:** Cursor verifies CC report on completion
**Phase:** Phase A · pre-SHADOW · live bring-up smoke test
**Estimated runtime:** 8-15 minutes (depending on how fast Sierra starts pushing)

---

## Context (Michael's situation · CC must read before acting)

Michael is about to start **Sierra Chart manually** on his Mac so that the
MES_AI_DataExport.cpp study begins writing fresh JSON files into
`~/SierraChart_Data/v9_export/`. He wants the full MEMS26 stack (bridge +
backend + frontend) running first so that the moment Sierra emits, the system
ingests live data end-to-end.

**Critical: all data in the system right now is stale.** Verified at
2026-05-25 12:30 IL:

| Source | Latest data | Age |
|---|---|---|
| `~/SierraChart_Data/v9_export/*.json` mtime | **2026-05-22 21:46** | 3 days |
| `v9_bars_5min.ts` MAX | **2026-05-22 21:35** (epoch via mtime) | 3 days |
| `v9_day_type_state.ts` MAX | **2026-05-22 18:46** | 3 days |
| `v9_trades.created_at` MAX | **2026-05-24 17:51** | 1 day (last SHADOW test) |

We do NOT wipe the DB — Sierra will append fresh bars after T0 and the new
`day_type` / `setup` / `trade` rows will accumulate on top of the existing
history. CC's job is to take a T0 snapshot so we can prove the system is
ingesting new data (not just serving stale rows).

**Real DB path:** `data/mems26_local.db` (2.8 GB · SQLite WAL).
Ignore `backend/v9/v9.db` (0 bytes · leftover).

---

## Spec authority (verbatim · CLAUDE.md + pre-LIVE protocol)

### Bridge local-only rule (NEVER violate)
- Bridge MUST push only to `http://localhost:8000`. Never to
  `mems26-web.onrender.com` or any other remote host.
- If `/tmp/bridge.err.log` ever shows `API push FAILED to https://...` → STOP,
  kill bridge, report to Michael. Means config drift slipped in.
- LaunchAgent at `~/Library/LaunchAgents/com.mems26.bridge.plist` already
  has `CLOUD_URL=http://localhost:8000` hard-set. Do NOT modify.

### LaunchAgent stability
- Do NOT change `KeepAlive` back to `true`. Must stay conditional
  (`SuccessfulExit=false`).
- Do NOT remove `V9_DISABLE_WATCHDOG="${V9_DISABLE_WATCHDOG:-1}"`.

### Pre-LIVE protocol (mems26-pre-live-protocol.mdc)
1. **Diagnose first, fix second.** No code changes from memory.
2. **One thread at a time.** Finish + report before any new work.
3. **4-axes UAT** for every data endpoint: Quality / Recency / Cardinality / Latency.
4. **No silent failures.** Any swallowed exception or `logger.debug` on a
   failure path is a STOP signal.
5. **Strategic stops:** any unexpected discovery (e.g. port collision, stale
   render LaunchAgent, mismatched DB schema) → STOP and report, don't improvise.

---

## SCOPE — exactly these actions

CC executes the following phases in order. After each phase, write a line to
the report file (created in PHASE 0).

### PHASE 0 · Init report (10 seconds)

Create `docs/reports/SHADOW_LIVE_BRINGUP_2026-05-25.md` with header:

```markdown
# SHADOW Live Bring-Up · 2026-05-25

**Operator:** Claude Code
**Start time:** <TZ-aware ISO timestamp>
**Goal:** Bring up MEMS26 stack + verify Sierra→Bridge→DB→API flow on fresh data

## Phase log
<append lines below as you go>
```

### PHASE 1 · Pre-flight + T0 snapshot (60 seconds · READ ONLY)

Run all of these. Append every result to the report under `## Phase 1 · Pre-flight`.

1. **Port check** (must be EMPTY · no listeners on 3000 / 8000):
   ```bash
   lsof -nP -iTCP:8000 -sTCP:LISTEN 2>/dev/null
   lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null
   ```
   - If anything is listening → record the PID + command, STOP, ask Michael.
   - Do NOT auto-kill. Could be a real session.

2. **Existing screen sessions** (informational):
   ```bash
   screen -ls | grep -E "mems26|bridge|backend|frontend" || echo "no mems26 screens"
   ```

3. **LaunchAgent status:**
   ```bash
   launchctl list | grep mems26 || echo "no mems26 launchagent loaded"
   ```
   - Expected: either `com.mems26.bridge` loaded OR nothing (we'll start via
     `scripts/start_all.sh` instead).

4. **Sierra export directory** (proves dir exists · captures current mtimes):
   ```bash
   ls -lrt ~/SierraChart_Data/v9_export/*.json | tail -5
   ```
   - Record the latest mtime as `T0_sierra_mtime`. Expected: ~2026-05-22 21:46.

5. **DB T0 snapshot** (this is the line that tells us if Sierra/bridge is
   working later):
   ```bash
   sqlite3 data/mems26_local.db "
     SELECT 'bars_5min' tbl, COUNT(*) cnt, MAX(ts) max_ts FROM v9_bars_5min
     UNION ALL SELECT 'day_type_state', COUNT(*), MAX(ts) FROM v9_day_type_state
     UNION ALL SELECT 'woodies_signals', COUNT(*), MAX(ts) FROM v9_woodies_signals
     UNION ALL SELECT 'five_min_setups', COUNT(*), MAX(ts) FROM v9_five_min_setups
     UNION ALL SELECT 'trades', COUNT(*), MAX(created_at) FROM v9_trades;
   "
   ```
   - Record all 5 rows verbatim in the report as `T0 DB state`.

6. **CLOUD_URL sanity** (defense vs config drift):
   ```bash
   grep -E "CLOUD_URL" ~/Library/LaunchAgents/com.mems26.bridge.plist | head -2
   grep -E "CLOUD_URL" scripts/start_all.sh | head -2
   grep -E "^CLOUD_URL" bridge/v9_streams/base_stream.py 2>/dev/null | head -3
   ```
   - All three must show `localhost` or `127.0.0.1`. If anything else → STOP,
     this is the exact config drift CLAUDE.md warns about.

**STOP signal for PHASE 1:**
- Ports 3000 or 8000 already in use → STOP, report PIDs to Michael.
- Sierra export directory missing → STOP, ask Michael where it is.
- Any `CLOUD_URL` not pointing to localhost → STOP immediately.

### PHASE 2 · Start the stack (90-150 seconds)

1. Run the canonical start script (it handles bridge + backend + frontend in
   `screen` sessions and already has all the right env vars):
   ```bash
   bash scripts/start_all.sh
   ```

2. Wait 10 seconds then verify all three:
   ```bash
   sleep 10
   pgrep -fa "json_bridge.py" | head -3
   pgrep -fa "uvicorn backend" | head -3
   pgrep -fa "next dev" | head -3
   ```

3. Backend health (must respond in <500ms · status 200):
   ```bash
   curl -s -w "\nHTTP %{http_code} · time_total=%{time_total}s\n" -m 5 \
     http://localhost:8000/api/v9/status | head -50
   ```

4. Bridge log sanity (must be empty or local-only · 30 seconds tail):
   ```bash
   tail -50 /tmp/bridge.err.log 2>/dev/null
   tail -30 /tmp/bridge.log 2>/dev/null
   ```
   - GREP for forbidden patterns:
     ```bash
     grep -E "https?://(mems26-web|render|cloud)" /tmp/bridge.log /tmp/bridge.err.log 2>/dev/null \
       && echo "❌ FORBIDDEN CLOUD URL DETECTED" \
       || echo "✅ no cloud push attempts"
     ```
   - If `❌` → STOP, kill bridge with `launchctl bootout` or
     `screen -X -S mems26_bridge quit`, report to Michael.

5. Frontend reachable (informational only · Michael may not need it for this run):
   ```bash
   curl -sI -m 5 http://localhost:3000 | head -3
   ```

Record all four service states (PID, port, log status) in the report under
`## Phase 2 · Stack up`.

**STOP signal for PHASE 2:**
- Any service fails to start within `start_all.sh`'s built-in timeouts.
- Bridge log shows non-localhost push attempt.
- `/api/v9/status` returns 5xx or >2000ms (likely DB lock or import error).

### PHASE 3 · Wait for Sierra fresh data (Michael-triggered · up to 5 min)

Output to console (so Michael sees it clearly in the terminal):

```
═══════════════════════════════════════════════════════════════
  STACK IS UP. NOW START SIERRA CHART.
  Load the MES_AI_DataExport.cpp study on your MES chart.
  Confirm the study is running (status bar bottom of chart).
  CC will detect first fresh write within 5 minutes.
═══════════════════════════════════════════════════════════════
```

Then poll the export directory every 10 seconds for up to 5 minutes:

```bash
T0_MTIME=$(stat -f "%m" ~/SierraChart_Data/v9_export/5min.json)
for i in $(seq 1 30); do
  CURRENT_MTIME=$(stat -f "%m" ~/SierraChart_Data/v9_export/5min.json)
  if [ "$CURRENT_MTIME" -gt "$T0_MTIME" ]; then
    echo "✅ Sierra wrote 5min.json at $(date) (loop $i)"
    break
  fi
  sleep 10
done
```

After detection (or 5-min timeout):

1. Capture current Sierra exports (latest mtime + size):
   ```bash
   ls -lt ~/SierraChart_Data/v9_export/*.json | head -10
   ```

2. Give bridge 30 seconds to ingest, then check bridge log for stream activity:
   ```bash
   sleep 30
   tail -100 /tmp/bridge.log | grep -E "API push (OK|FAILED|to)" | tail -20
   ```
   - Expected: lines like `[5min] API push OK to http://localhost:8000`.
   - If 0 lines → bridge isn't picking up files, STOP, report.

Record Sierra-first-write timestamp and first-bridge-push timestamp in
`## Phase 3 · Sierra live`.

**STOP signal for PHASE 3:**
- After 5 minutes no file mtime has advanced → ask Michael to confirm Sierra
  + study are actually running. Don't loop forever.
- Bridge log shows `API push FAILED` (any URL) → STOP, capture last 50 lines.
- Bridge log shows push to non-localhost → STOP immediately.

### PHASE 4 · 4-axes UAT on live endpoints (90 seconds)

For each endpoint below, run the curl and check ALL FOUR axes from
pre-LIVE protocol. Record results in a table in the report.

The four axes (verbatim from `.cursor/rules/mems26-pre-live-protocol.mdc`):
1. **Quality:** the bad-data condition is gone (e.g. no NULL OHLC, no zero `vol` on a non-empty bar)
2. **Recency:** `endpoint.latest_ts > T0_DB_MAX_TS` (proves new data is in)
3. **Cardinality:** `len(rows) == requested_limit` (no silent truncation)
4. **Latency:** `time_total < 100ms` for health, `<500ms` for chart/TPO

Endpoints to verify:

```bash
# 1. Health (recency check vs T0)
curl -s -w "\ntime_total=%{time_total}s\n" -m 5 \
  http://localhost:8000/api/v9/status | python3 -m json.tool | head -40

# 2. 5min bars (the critical pipe)
curl -s -w "\ntime_total=%{time_total}s\n" -m 5 \
  "http://localhost:8000/api/v9/chart/bars5min?limit=20" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
rows = data.get('bars', data) if isinstance(data, dict) else data
print(f'rows_returned: {len(rows)}')
if rows:
    print(f'latest_ts: {rows[-1].get(\"ts\")}')
    print(f'earliest_ts: {rows[0].get(\"ts\")}')
    nulls = sum(1 for r in rows if any(r.get(k) is None for k in ['o','h','l','c']))
    print(f'null_OHLC_rows: {nulls}')
"

# 3. Day type
curl -s -w "\ntime_total=%{time_total}s\n" -m 5 \
  http://localhost:8000/api/v9/day_type/current | python3 -m json.tool | head -30

# 4. TPO current
curl -s -w "\ntime_total=%{time_total}s\n" -m 5 \
  http://localhost:8000/api/v9/tpo/current | python3 -m json.tool | head -30

# 5. Footprint (latest)
curl -s -w "\ntime_total=%{time_total}s\n" -m 5 \
  http://localhost:8000/api/v9/footprint/current 2>&1 | head -50

# 6. Woodies signals
curl -s -w "\ntime_total=%{time_total}s\n" -m 5 \
  http://localhost:8000/api/v9/woodies/signals/latest 2>&1 | head -50
```

For each endpoint output a row in this exact format:

| Endpoint | HTTP | Latency | Rows | Latest ts (vs T0) | Quality |
|---|---|---|---|---|---|
| `/status` | 200 | 45ms | n/a | ts > T0 ✅ | no errors ✅ |
| `/chart/bars5min?limit=20` | 200 | 180ms | 20 ✅ | ts > T0 ✅ | 0 null OHLC ✅ |
| ... | ... | ... | ... | ... | ... |

After UAT, re-snapshot the DB and compare to T0:

```bash
sqlite3 data/mems26_local.db "
  SELECT 'bars_5min' tbl, COUNT(*) cnt, MAX(ts) max_ts FROM v9_bars_5min
  UNION ALL SELECT 'day_type_state', COUNT(*), MAX(ts) FROM v9_day_type_state
  UNION ALL SELECT 'woodies_signals', COUNT(*), MAX(ts) FROM v9_woodies_signals
  UNION ALL SELECT 'five_min_setups', COUNT(*), MAX(ts) FROM v9_five_min_setups
  UNION ALL SELECT 'trades', COUNT(*), MAX(created_at) FROM v9_trades;
"
```

Compare row-by-row to `T0 DB state`. For each table, classify as:
- **ADVANCING** — count grew OR max_ts is newer (Sierra → bridge → DB working)
- **STATIC** — count same + max_ts same (no fresh data reached this table yet)
- **ANOMALY** — count dropped or max_ts went backwards (BUG · STOP)

Record under `## Phase 4 · UAT live`.

**STOP signal for PHASE 4:**
- Any endpoint returns 5xx persistently.
- `/chart/bars5min` returns `len(rows) < requested_limit` (recurrence of P27.5a bug).
- `/status.latency_ms` > 100ms (backend choke).
- Any table in DB snapshot 2 is an ANOMALY (count dropped or ts regressed).

### PHASE 5 · Final report (60 seconds)

Append `## Summary` to `docs/reports/SHADOW_LIVE_BRINGUP_2026-05-25.md` with:

1. **Stack status:** bridge / backend / frontend — RUNNING or DOWN (with PIDs).
2. **Sierra live:** YES / NO / TIMEOUT — with first-write timestamp.
3. **Fresh data flowing:** which tables ADVANCED beyond T0 (table list).
4. **UAT axes:** Quality / Recency / Cardinality / Latency — PASS or FAIL per axis (rolled up across all endpoints).
5. **Issues found:** any STOP signals encountered + their resolution status.
6. **Recommendation to Michael:** one of:
   - `READY for SHADOW soak` — all four axes PASS, fresh data flowing on all critical tables.
   - `PARTIAL` — stack up but some tables not advancing yet (could be normal · 5-min bar boundary, day-type recompute delay) — what to watch.
   - `BLOCKED` — concrete issue + which file/log to look at.

Output to console at the end:

```
═══════════════════════════════════════════════════════════════
  PHASE 5 COMPLETE. Report at:
  docs/reports/SHADOW_LIVE_BRINGUP_2026-05-25.md
  Recommendation: <READY|PARTIAL|BLOCKED>
═══════════════════════════════════════════════════════════════
```

---

## Constraints (must not violate)

1. **No code changes.** This is service bring-up, not a fix. If you find a
   bug → STOP and report, don't patch.
2. **No `kill -9` on real services** without explicit Michael approval. If a
   port is stuck, report PID + command first.
3. **No new dependencies, no pip install, no npm install.** If something
   doesn't import → STOP, the env is broken, report.
4. **No silent excepts.** Every command's failure must be logged to the
   report (`stderr` redirected with `2>&1` is OK · `2>/dev/null` is NOT, except
   for the `lsof` and `pgrep` "no match" cases noted above).
5. **No `logger.debug` on failure paths** — but we're not editing code anyway.
6. **No render/cloud URLs anywhere.** Even in a one-off curl. The instant
   `https://mems26-web.onrender.com` appears in any log → STOP.
7. **No background polling after PHASE 4.** The screen sessions started by
   `start_all.sh` keep running (that's the goal) — but don't add new watch loops.

## Allowed tools

- `bash`, `screen`, `launchctl`, `lsof`, `pgrep`, `curl`, `sqlite3`, `python3`, `tail`, `grep`, `stat`, `ls`, `date`, `sleep`.
- `scripts/start_all.sh` (canonical service starter · already audited).
- Writing to `docs/reports/SHADOW_LIVE_BRINGUP_2026-05-25.md` (the only file you create).

## Forbidden

- Editing any `.py`, `.ts`, `.tsx`, `.json` config, plist, or shell script.
- Touching `~/Library/LaunchAgents/com.mems26.bridge.plist`.
- Running `pip install` / `npm install` / `npm run build`.
- Running `pytest` (this is bring-up, not test).
- `git add` / `git commit` / `git push` — Michael owns commits.
- Running `scripts/stop_all.sh` or `scripts/restart_all.sh` unless you hit a
  STOP signal AND Michael approves the restart in a follow-up message.

---

## Deliverable format

After PHASE 5, output to chat (in addition to the report file):

1. **One-line status:** `STATUS: <READY|PARTIAL|BLOCKED> · stack=<up|partial|down> · sierra=<live|stale> · fresh_data_tables=N/5`
2. **Report path:** `docs/reports/SHADOW_LIVE_BRINGUP_2026-05-25.md`
3. **Key counters T0 → T1:** the diff line for `v9_bars_5min` (e.g.
   `bars_5min: 2115 → 2117 (+2 bars · max_ts 1779475500 → 1779475800)`).
4. **Any STOP signals hit:** list them with timestamp.
5. **Next action for Michael:** what to check / decide.

## Stop signal — overall

IF any of these conditions are met, STOP immediately and report to Michael
with the exact log/error/PID seen:

- Port 3000 or 8000 already in use by an unknown process.
- `CLOUD_URL` anywhere doesn't point to `localhost` or `127.0.0.1`.
- Bridge log shows `https://` (any cloud/render URL).
- 5xx on `/api/v9/status` or `/api/v9/chart/bars5min` for >30 seconds.
- Sierra doesn't write within 5 minutes after Michael says it's started.
- Any DB table shows `count` dropped between T0 and T1 (data loss).
- Any `except` you'd be tempted to add to mask a failure — DON'T, STOP instead.

DO NOT guess. DO NOT improvise. DO NOT add a "TODO: check this later" line.
Output:

```
STOP — <one-line reason>
Last command: <command>
Last output: <output tail>
Need Michael decision on: <specific question>
```

---

## Authority references

- `CLAUDE.md` — bridge local-only · LaunchAgent stability · service bring-up rules
- `.cursor/rules/mems26-pre-live-protocol.mdc` — 4-axes UAT · stop signals · diagnose-first
- `.cursor/rules/mems26-stability.mdc` — port pre-check · no auto-restart
- `scripts/start_all.sh` — canonical service starter (already env-correct)
- `docs/handoff/NEXT_CHAT_CONTINUATION_2026-05-25_AM.md` — current Phase A state

*End of mega-prompt · v1 · 2026-05-25 12:35 IL*
