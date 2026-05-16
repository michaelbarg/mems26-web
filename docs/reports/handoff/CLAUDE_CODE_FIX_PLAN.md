# Claude Code — MEMS26 OS Fix Plan (Phase 1: pre-reboot)

**Status:** ready to paste into Claude Code (`claude`) from a real Terminal.app on the user's Mac.
**Mode:** EXECUTE (mutating). Will require `sudo` for the LaunchDaemon plist. Will NOT start any service. Will NOT reboot — user does that manually at the end.
**Inputs:** the prior `DIAGNOSTIC_REPORT_2026-05-16-2245.md` in the same folder.
**Author:** Cursor agent (multitask session)
**Last updated:** 2026-05-16

## How to use

1. Terminal.app (not Cursor). `cd /Users/michael/Downloads/mems26_web_git`. `claude`.
2. Paste everything between `PASTE FROM HERE` and `PASTE TO HERE` as ONE message.
3. Claude Code runs the steps with safety gates between each. If any gate fails, it STOPS and reports.
4. At the end Claude Code will tell you to reboot manually. **Do not start any service before the reboot.**
5. After reboot, run the Phase-2 prompt (separate file — `CLAUDE_CODE_BRINGUP.md`, will be added).

---

## PASTE FROM HERE

You are Claude Code in a real Terminal.app shell on macOS, in the user's MEMS26 trading-system repo at `/Users/michael/Downloads/mems26_web_git`. You ran the diagnostic report earlier today; it is at `docs/reports/handoff/DIAGNOSTIC_REPORT_2026-05-16-2245.md`.

Your job NOW is to **execute** the fix plan from §7 of that report, up to but NOT including the reboot or any service start. You will:

1. Kill the duplicate bridge PID 5000 (keeping LaunchAgent-managed PID 547).
2. Install a permanent system-wide LaunchDaemon that raises `maxfiles` to `65536 / 200000` (Option B, fix #1 in the report).
3. Restart `sysmond` if it's down.
4. Commit the currently untracked P27.5a files and handoff documents (3 atomic commits).
5. Drop the now-redundant pre-P27.5a stash.
6. STOP. Print a clear summary and instruct the user to reboot.

### Hard rules

- **Do NOT** start `bash scripts/start_all.sh`, `npm run dev`, `python3 bridge/json_bridge.py`, `uvicorn ...`, or anything that opens a long-running service. The whole point of this phase is to fix the OS BEFORE touching the stack again.
- **Do NOT** unload or remove the existing `com.mems26.bridge` LaunchAgent — PID 547 keeps the bridge alive; only the duplicate (PID 5000) is removed.
- **Do NOT** modify any source file in `frontend/`, `backend/`, `bridge/`, or `scripts/`. Only create the new plist and run `git add`/`commit`/`stash drop`.
- **Do NOT** force-push, amend, rebase, or rewrite history. New commits only.
- After each step, RUN A VERIFY QUERY and abort if the precondition isn't satisfied. Do not "try harder" — stop and report.
- Output every command and its full output. The user is reviewing this in another tool.

### Step 0 — pre-flight: confirm the diagnostic is still valid

```
cd /Users/michael/Downloads/mems26_web_git
launchctl limit maxfiles                                # expect: 256 unlimited
kill -0 547 && echo "bridge LaunchAgent PID 547 alive" || echo "❌ 547 DEAD — abort"
kill -0 5000 && echo "duplicate bridge PID 5000 alive" || echo "ℹ️ 5000 already gone"
kill -0 5143 && echo "backend PID 5143 alive" || echo "ℹ️ 5143 gone (expected if killed earlier)"
lsof -nP -iTCP:3000 -sTCP:LISTEN 2>&1 | head      # expect: empty (frontend NOT running)
git log -1 --oneline                              # expect HEAD: 04ade4b
git stash list                                    # expect: stash@{0}: pre-P27.5a
git status -sb                                    # expect untracked files match diagnostic §2
```

If `launchctl limit maxfiles` already shows the target (`65536 200000`), skip Step 2. If 547 is dead, STOP and report (the LaunchAgent should be alive).

### Step 1 — kill the duplicate bridge (keep LaunchAgent's PID 547)

```
kill 5000 2>/dev/null
sleep 2
kill -0 5000 2>/dev/null && { echo "still alive, escalating"; kill -9 5000; sleep 1; }
kill -0 5000 2>/dev/null && echo "❌ FAILED to kill 5000 — STOP" || echo "✅ duplicate gone"
kill -0 547  && echo "✅ LaunchAgent bridge 547 still alive (good)" || echo "❌ 547 died — STOP"
```

If 547 died, the LaunchAgent should respawn it within ~30 s (KeepAlive+ThrottleInterval=30). Wait, verify with `pgrep -f json_bridge.py`. If still no bridge, STOP and report.

### Step 2 — install permanent LaunchDaemon for maxfiles

Write the plist to a non-privileged location first:

```
cat > /tmp/limit.maxfiles.plist << 'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>limit.maxfiles</string>
    <key>ProgramArguments</key>
    <array>
        <string>launchctl</string>
        <string>limit</string>
        <string>maxfiles</string>
        <string>65536</string>
        <string>200000</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>ServiceIPC</key>
    <false/>
</dict>
</plist>
PLIST_EOF

plutil -lint /tmp/limit.maxfiles.plist || { echo "❌ plist invalid — STOP"; exit 1; }
cat /tmp/limit.maxfiles.plist | head -20
```

Now elevate. **The user's terminal will prompt for password.** Do not retry on failure — print the error and STOP.

```
sudo install -o root -g wheel -m 644 /tmp/limit.maxfiles.plist /Library/LaunchDaemons/limit.maxfiles.plist
ls -la /Library/LaunchDaemons/limit.maxfiles.plist
sudo launchctl load -w /Library/LaunchDaemons/limit.maxfiles.plist
```

Verify immediately:

```
launchctl limit maxfiles
```

Expected output: `maxfiles    65536          200000`. If it still shows `256`, the load failed silently — STOP and report.

Also raise the *current* Terminal's ulimit so subsequent commits don't choke:

```
ulimit -n 10240 2>/dev/null
ulimit -n
```

### Step 3 — restart sysmond if down

```
launchctl list | grep -i sysmond || { echo "sysmond not running — restarting"; sudo launchctl kickstart -k system/com.apple.sysmond; }
sleep 2
launchctl list | grep -i sysmond && echo "✅ sysmond running" || echo "⚠️ sysmond still not visible — non-fatal but pgrep may misbehave"
pgrep -fl Finder >/dev/null && echo "✅ pgrep works" || echo "⚠️ pgrep still broken"
```

### Step 4 — commit the untracked work (3 atomic commits)

Verify scope before committing:

```
git status -sb
```

**Commit A — P27.5a service stubs:**

```
git add backend/v9/services/bar_integrity.py tests/v9/services/test_bar_integrity.py
git add docs/architecture/                                       # if non-empty
git add docs/reports/handoff/MEGA_PROMPT_P27_5A.md
git diff --cached --stat
git commit -m "$(cat <<'EOF'
feat(P27.5a-wip): bar integrity service skeleton + execution prompt

- backend/v9/services/bar_integrity.py: bad-bar detection service stub
- tests/v9/services/test_bar_integrity.py: TDD scaffold (P27.5a)
- docs/architecture/: supporting design artifacts
- docs/reports/handoff/MEGA_PROMPT_P27_5A.md: self-contained P27.5a prompt

Untracked since prior session — committing now per
docs/reports/handoff/DIAGNOSTIC_REPORT_2026-05-16-2245.md §7.3.
Implementation itself runs under P27.5a (next prompt).
EOF
)"
```

**Commit B — handoff & roadmap docs:**

```
git add docs/reports/handoff/NEXT_CHAT_PROMPT.md \
        docs/reports/handoff/GANTT_TO_LIVE.md \
        docs/reports/handoff/PROMPT_LIST_TO_LIVE.md \
        docs/reports/handoff/SESSION_LOG_2026-05-16.md \
        docs/reports/handoff/CLAUDE_CODE_DIAGNOSE_REPORT.md \
        docs/reports/handoff/DIAGNOSTIC_REPORT_2026-05-16-2245.md \
        docs/reports/handoff/CLAUDE_CODE_FIX_PLAN.md
git diff --cached --stat
git commit -m "$(cat <<'EOF'
docs(handoff): session 2026-05-16 — roadmap, prompts, diagnostic + fix plan

Living documents for cross-tool (Cursor / Claude Code / Claude web) handoff:
- NEXT_CHAT_PROMPT.md         — paste-ready prompt for next chat session
- GANTT_TO_LIVE.md            — 11-phase plan to LIVE money trading
- PROMPT_LIST_TO_LIVE.md      — ordered prompts P27.5a → P-L5
- SESSION_LOG_2026-05-16.md   — what was done this session
- CLAUDE_CODE_DIAGNOSE_REPORT.md — prompt for OS diagnostic
- DIAGNOSTIC_REPORT_2026-05-16-2245.md — actual diagnostic output
- CLAUDE_CODE_FIX_PLAN.md     — this fix plan (Phase 1: pre-reboot)
EOF
)"
```

**Commit C — stage run logs:**

```
git add docs/reports/stage_runs/status_check_*.log
git diff --cached --stat
git commit -m "ops: stage status_check logs from 2026-05-16 session"
```

After all three commits — confirm clean (only the harmless `__pycache__` modifications should remain):

```
git status -sb
git log --oneline -5
```

If anything other than `__pycache__/*.pyc` is uncommitted, STOP and report — do not commit `__pycache__` files; instead suggest adding them to `.gitignore` in a later prompt.

### Step 5 — drop the now-redundant stash

The pre-P27.5a stash is superseded by commit `04ade4b`. Drop it to prevent future confusion:

```
git stash show -p stash@{0} | head -20      # quick sanity glance
git stash drop stash@{0}
git stash list                              # should be empty
```

If the stash diff at this point shows something NOT in `04ade4b` (i.e. unique work not yet captured), STOP and report — do not drop, save the stash to a patch file for later review.

### Step 6 — final checks and stop

```
echo "=== FINAL STATE ==="
launchctl limit maxfiles
ulimit -n
echo "--- services ---"
pgrep -fl "json_bridge|uvicorn backend|next dev" || echo "no MEMS26 processes (frontend should be absent)"
lsof -nP -iTCP:3000 -sTCP:LISTEN 2>&1 | head
curl -s -o /dev/null -w "backend health: %{http_code}\n" -m 5 http://127.0.0.1:8000/api/v9/health
echo "--- git ---"
git log --oneline -5
git status -sb
git stash list
echo "==================="
```

### Final report — print this exactly

When all 6 steps are green, output a short markdown summary including:

- Old `launchctl limit maxfiles` (256/unlimited) → new (65536/200000)
- Duplicate bridge killed? yes/no
- sysmond restored? yes/no
- 3 commits SHAs and one-line subjects
- Stash dropped? yes/no
- Bridge PID still alive (LaunchAgent)? PID number
- Backend still 200? yes/no
- Frontend still not running? yes/no
- **NEXT STEP for the human:**
  ```
  1. Reboot the Mac now (Apple menu → Restart).
  2. After login, open Terminal.app and verify:  launchctl limit maxfiles
     → should show 65536 200000.
  3. Paste the Phase-2 bring-up prompt (CLAUDE_CODE_BRINGUP.md, to be added)
     to start the stack cleanly.
  ```

If any step failed, output the failed step number + full error + which subsequent steps were skipped. Do not paper over failures.

## PASTE TO HERE
