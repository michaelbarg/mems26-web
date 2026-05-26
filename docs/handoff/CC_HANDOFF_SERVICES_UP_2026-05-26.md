# CC HANDOFF · Services Bring-Up · 2026-05-26 AM

**Authority:** Michael approved Cursor autonomous plan 2026-05-26 06:54 IL
**Phase:** Post-Memorial-Day · pre-RTH UAT preparation
**Owner (you):** Claude Code
**Reports to:** Cursor (G3 review on completion)
**Expected duration:** 5–10 minutes total
**Block:** L4-1 Stream B reject UAT is BLOCKED until you complete this.

---

## 1 · Goal

Bring up MEMS26 stack (Bridge · Backend · Frontend) so Cursor can run the
L4-1 pre-RTH UAT on Stream B reject path and continue with the
build-status endpoint work.

After this you do nothing else — Cursor takes over for L4-1 curl + 4-axis
verification.

---

## 2 · Mandatory pre-checks (do these FIRST · do not skip)

These are stability guardrails from `.cursor/rules/mems26-stability.mdc`
and `CLAUDE.md`. If any of them fail → STOP and report to Cursor instead
of starting services.

### 2.1 LaunchAgent integrity

```bash
plutil -lint ~/Library/LaunchAgents/com.mems26.bridge.plist
```

Must show `OK`.

Then inspect the plist:

```bash
grep -A 3 "KeepAlive" ~/Library/LaunchAgents/com.mems26.bridge.plist | head -10
grep "CLOUD_URL" ~/Library/LaunchAgents/com.mems26.bridge.plist
grep "V9_DISABLE_WATCHDOG" ~/Library/LaunchAgents/com.mems26.bridge.plist
```

**Expected:**

- `KeepAlive` is a `<dict>` with `<key>SuccessfulExit</key><false/>` (conditional · NOT `<true/>` as a bare bool)
- `CLOUD_URL=http://localhost:8000` (must NOT contain `mems26-web.onrender.com` or `https://`)
- `V9_DISABLE_WATCHDOG=1`

If any value drifts → STOP, paste the diff to Cursor, do not "fix" it.

### 2.2 No stale listeners

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN 2>/dev/null
lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null
```

If a listener already exists on either port → STOP, do NOT `kill -9`.
Report the PID + command to Cursor and ask before any destructive action.

### 2.3 `base_stream.py` localhost guard intact

```bash
grep -n "CLOUD_URL" bridge/v9_streams/base_stream.py | head -10
```

Must show the localhost-only refuse-to-start guard. If the file was
modified to allow remote URLs → STOP, alert Cursor (this is a stability
rule violation per `CLAUDE.md` "Bridge Local-Only Rule").

---

## 3 · Bring-up (run only after §2 all pass)

Use `scripts/start_all.sh` — it is the canonical bring-up path and
already hard-exports `CLOUD_URL=http://localhost:8000`,
`V9_DISABLE_WATCHDOG=1`, and `BRIDGE_TOKEN`. Do NOT bypass it with
manual `python3 -m uvicorn ...` calls.

```bash
cd /Users/michael/Downloads/mems26_web_git
bash scripts/start_all.sh
```

Wait for the script's own readiness loop to complete (it prints
`✅ Bridge started`, `✅ Backend started`, `✅ Frontend ready` in turn ·
takes 10–30 s).

---

## 4 · Verification (mandatory · all 4 axes)

### 4.1 PIDs alive

```bash
pgrep -fl 'json_bridge.py'
pgrep -fl 'uvicorn backend'
pgrep -fl 'next dev'
```

Each must return exactly one PID. Capture the PIDs.

### 4.2 Backend reachable

```bash
curl -fsS -m 5 http://localhost:8000/api/v9/status -o /tmp/status_response.json
cat /tmp/status_response.json | python3 -m json.tool | head -40
```

Must return HTTP 200 and valid JSON. Latency should be < 1 s.

### 4.3 Bridge not pushing to a remote URL

```bash
tail -200 /tmp/bridge.err.log 2>/dev/null | grep -E "API push FAILED to https?://" | head -5
tail -200 /tmp/bridge.log 2>/dev/null | grep -E "API push FAILED to https?://" | head -5
```

**Must return zero matches.** If you see `API push FAILED to https://` →
this is the CLOUD_URL drift scenario from `mems26-stability.mdc`. STOP,
do not retry, alert Cursor.

It is OK if you see `API push FAILED to http://localhost` while uvicorn
is still warming up — only the `https://` form is a config drift
violation.

### 4.4 Frontend compiled

```bash
curl -fsS -m 5 http://localhost:3000 > /tmp/frontend_check.html
head -20 /tmp/frontend_check.html
```

Must return HTML containing `<title>` or `__next` markers. If you see
the Next.js compile-in-progress page → wait 10 s and retry once.

---

## 5 · Report back to Cursor

Reply in chat (do not commit anything · this is read-only bring-up).
Include exactly these fields:

```
Services up · 2026-05-26 HH:MM IL
- Bridge PID: <pid>
- Backend PID: <pid>
- Frontend PID: <pid>
- /api/v9/status: 200 in <Nms>
- /tmp/bridge.err.log "API push FAILED to https://" matches: 0
- Frontend on :3000: 200 (HTML returned)
- Pre-checks: LaunchAgent OK · CLOUD_URL=localhost · base_stream guard intact
```

Cursor will then run L4-1 independently.

---

## 6 · Stop signals (immediate halt)

Halt and ping Cursor — do NOT troubleshoot autonomously — if any of:

1. `plutil -lint` on the LaunchAgent reports a parse error.
2. `CLOUD_URL` in any file ≠ `http://localhost:8000`.
3. Existing listener on `:8000` or `:3000` before bring-up.
4. `pgrep -fl 'uvicorn backend'` shows >1 PID after start (duplicate workers).
5. `API push FAILED to https://...` in either log file.
6. `/api/v9/status` returns 500/timeout.
7. `base_stream.py` modified to remove the localhost guard.

If something genuinely benign fails (e.g., ulimit warning), include it
in your report but proceed.

---

## 7 · Forbidden surface (do NOT touch)

- `~/Library/LaunchAgents/com.mems26.bridge.plist` — read only · no edits
- `bridge/v9_streams/base_stream.py` — read only · the localhost guard is locked
- `.gitignore` — already correct post-`84f731f`
- `sc_study/MES_AI_DataExport_merged.cpp` — gitignored · do not commit
- `backend/v9/v9.db` — gitignored · do not commit
- Anything under `frontend/v9/src/v9/` — Cursor owns frontend in this session
- `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` — known modified ·
  Cursor logged it as "option ג open" in STATUS_BOARD · Michael to decide
  tonight · do not revert/commit

---

## 8 · Memorial Day lessons applicable here (§5 reminders)

1. **No silent failure.** If a check fails, surface it in the report —
   do not paper over it with "best effort completed".
2. **Diagnose first, fix second.** If something is unexpectedly wrong
   (e.g., 3 backend PIDs), stop and report — do not `kill -9` and
   retry hoping for a different result (mistake #3 from
   `mems26-pre-live-protocol.mdc`).
3. **Trust raw evidence over status summaries.** `pgrep` output beats
   "looks healthy". Always paste raw output to Cursor (mistake #4).
4. **Do not change CLOUD_URL** for any reason without Michael's
   explicit chat approval (stability rule).

---

## 9 · After Cursor takes over

Cursor will:
1. Run L4-1 curl (POST `/api/v9/bars/5min` with `BarStatus=BAR_OPEN`)
2. Verify the bar is rejected (Stream B reject path)
3. Verify zero rows added to `bars_5min` for that BarStatus
4. Update STATUS_BOARD with the result

You are free after §5 report unless Cursor pings you again.

---

**End of handoff.** Signal Cursor when §5 report is posted.
