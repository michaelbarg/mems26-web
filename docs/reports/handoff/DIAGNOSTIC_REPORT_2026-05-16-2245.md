# MEMS26 Local Diagnostic Report — 2026-05-16 22:45 IST

## 1. Current file state

| Item | Status | Evidence |
|------|--------|----------|
| start_all.sh ulimit fix | **present** | Line 20: `ulimit -n 10240 2>/dev/null \|\| true` |
| start_all.sh WATCHPACK_POLLING | **present** | Line 71: `WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000` |
| start_all.sh backend host | **127.0.0.1** | Line 56: `--host 127.0.0.1 --port 8000` |
| start_all.sh V9_DISABLE_WATCHDOG | **present** | Line 36 (inside bridge block): `export V9_DISABLE_WATCHDOG="${V9_DISABLE_WATCHDOG:-1}"` |
| next.config.ts turbopack.root | **present** | Line 4-5: `turbopack: { root: process.cwd() }` |
| package.json dev script | `"next dev -H 127.0.0.1"` | Line 6 |
| ChartV5b client guards (attributionLogo, looksOk, age_ms, withZ) | **absent** | grep returned nothing — guards removed or never in this version |
| V9Dashboard single-pane | **yes** | No imports of VolumePanel, SystemPanelsBar, react-resizable-panels in V9Dashboard.tsx (note: react-resizable-panels remains in package.json deps but is unused) |
| bar_integrity.py | **exists** | 1725 bytes |
| test_bar_integrity.py | **exists** | 3874 bytes |
| MEGA_PROMPT_P27_5A.md | **exists** | 19359 bytes |

## 2. Git state

- **Branch:** `stabilize/mems26-local-truth-2026-05-16` (no remote tracking shown)
- **HEAD:** `04ade4b fix(infra): harden start_all + Next dev to prevent EMFILE/Watchpack crashes`
- **Uncommitted tracked files (modified):**
  - `bridge/v9_streams/__pycache__/__init__.cpython-39.pyc`
  - `bridge/v9_streams/__pycache__/base_stream.cpython-39.pyc`
- **Untracked files:**
  - `backend/v9/services/bar_integrity.py`
  - `docs/architecture/`
  - `docs/reports/handoff/CLAUDE_CODE_DIAGNOSE_REPORT.md`
  - `docs/reports/handoff/GANTT_TO_LIVE.md`
  - `docs/reports/handoff/NEXT_CHAT_PROMPT.md`
  - `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md`
  - `docs/reports/handoff/SESSION_LOG_2026-05-16.md`
  - `docs/reports/stage_runs/` (3 log files)
  - `tests/v9/services/test_bar_integrity.py`
- **Last 5 commits touching hardening files:**
  1. `04ade4b` fix(infra): harden start_all + Next dev to prevent EMFILE/Watchpack crashes
  2. `419f4cc` fix: stabilize bridge startup diagnostics
  3. `dd47362` fix(bridge): align export dir default to SierraChart_Data
  4. `5c90044` feat(ops): mems-start/stop/restart commands for full stack management
- **Stashes:** 1 — `stash@{0}: pre-P27.5a: 2026-05-16 frontend + scripts hardening (carry-forward)`
- **Diagnosis of previous wipe:** The stash message confirms it: someone (likely Cursor's parallel session) ran `git stash` before starting P27.5a work, which stashed the uncommitted hardening edits. Later, commit `04ade4b` re-applied them as a real commit. The hardening is now **committed and safe** — it will not be wiped again by a stash/restore cycle. The stash still exists but is redundant.

## 3. OS resource limits — RED/GREEN audit

| Limit | Current | Needed | Status |
|-------|---------|--------|--------|
| ulimit -n (open files) | **1,048,575** | >= 4096 | **GREEN** (this shell; see note below) |
| launchctl limit maxfiles (soft) | **256** | >= 4096 | **RED** — LaunchAgent-spawned processes (including the bridge plist) inherit the 256 soft limit! |
| kern.maxfilesperproc | 61,440 | >= 10,240 | **GREEN** |
| kern.maxfiles | 122,880 | >= 49,152 | **GREEN** |
| kern.maxproc | 4,176 | >= 2,048 | **GREEN** |
| kern.maxprocperuid | 2,784 | — | GREEN |
| Processes now | 512 total / 318 user | < ~500 idle | **YELLOW** — elevated (318 user procs), likely due to two bridge processes + Cursor + many helpers |
| sysmond | **NOT running** | up | **RED** |

**Critical note on ulimit -n:** This Claude Code shell shows 1,048,575 because Terminal.app sources `~/.zshrc` (or the shell was launched with the higher limit). However, `launchctl limit maxfiles` reports **256 soft**. Any process launched by launchd (including `com.mems26.bridge.plist`) or by GUI apps like Cursor inherits the launchd soft limit of 256 unless it explicitly calls `ulimit -n` after fork. The `start_all.sh` script does call `ulimit -n 10240` which raises it for screen children, but if the parent shell's hard limit is 256, the raise will silently fail. This is the likely remaining vector for EMFILE when launching from Finder / .command files.

## 4. Service state right now

| Service | Status | Details |
|---------|--------|---------|
| Bridge | **RUNNING (2 PIDs: 547, 5000)** | PID 547 launched by LaunchAgent (`com.mems26.bridge`), PID 5000 likely a manual/screen launch. **Duplicate — must be resolved.** |
| Backend | **RUNNING (PID 5143)** | `uvicorn backend.main:app --host 127.0.0.1 --port 8000`. Health: **200 OK** |
| Frontend | **NOT RUNNING** | No process on port 3000, no `next dev` process |
| Screen sessions | **NONE** | `/var/folders/.../T/.screen` — "No Sockets found" |
| LaunchAgent | `com.mems26.bridge.plist` present and loaded | KeepAlive=true, RunAtLoad=true, ThrottleInterval=30 |
| launchd mems26 entry | PID 547, exit status 0 | Active |

**Key issue:** The LaunchAgent (`KeepAlive: true`) will respawn the bridge whenever it's killed. This conflicts with `start_all.sh`'s screen-based bridge launch, resulting in **duplicate bridge processes**. The second bridge (PID 5000) was probably spawned by `start_all.sh`; it competes for the same WebSocket/file resources.

## 5. Next.js environment

| Item | Value |
|------|-------|
| Node | v24.10.0 |
| npm | 11.6.1 |
| .next cache | **171 MB** (dev subfolder only, no BUILD_ID) — stale from prior dev session |
| node_modules | 516 MB (next alone: 169 MB) |
| frontend/v9/src file count | 105 files |
| frontend/v9/node_modules file count | **25,519 files** |

**Analysis:** With 25,519 files in node_modules and 105 in src, Watchpack (even with polling) would attempt inotify/kqueue watches on potentially all of them. At ulimit 256 (launchd-inherited), this immediately hits EMFILE. With ulimit 10240 (from start_all.sh), it has headroom — **but only if start_all.sh is the launch vector** (not .command via Finder, not LaunchAgent).

## 6. Sierra / bridge prerequisites

| Item | Status |
|------|--------|
| v9_export dir | **exists** — 14 entries, 12 JSON files |
| Last modified | May 16 14:09:43 2026 (~8.5 hours ago — market closed) |
| /tmp/bridge.log | **missing** (LaunchAgent's StandardOutPath should write here, but may be failing) |
| /tmp/backend.log | not found |
| /tmp/frontend.log | not found |
| /tmp/start_bridge.sh | exists (490 bytes, from start_all.sh line 28-39) |
| .env keys | V9_EXPORT_DIR, CLOUD_URL, BRIDGE_TOKEN — all present |

**Note:** The LaunchAgent plist routes stdout to `/tmp/bridge.log` and stderr to `/tmp/bridge.err.log`, yet `/tmp/bridge.log` doesn't exist. This suggests the LaunchAgent is either failing silently or the file was cleaned by a reboot (tmp is ephemeral on macOS). Check `/tmp/bridge.err.log`.

## 7. Recommended FIX PLAN — ordered, with risk assessment

### 1. Permanent OS-level file-descriptor limit (MOST IMPORTANT)

The `launchctl limit maxfiles 256 unlimited` is the **root cause**. Even though `kern.maxfilesperproc` is 61K, the launchd soft limit of 256 is what processes inherit.

- **Option A — per-session in `~/.zshrc`:**
  ```bash
  # Add to ~/.zshrc (or ~/.zprofile for login shells):
  ulimit -n 10240
  ```
  Risk: LOW. No sudo. Only affects Terminal shells — NOT Finder-launched .command files (they may not source .zshrc).

- **Option B — system-wide LaunchDaemon (RECOMMENDED):**
  Create `/Library/LaunchDaemons/limit.maxfiles.plist`:
  ```xml
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
  </dict>
  </plist>
  ```
  Then:
  ```bash
  sudo chown root:wheel /Library/LaunchDaemons/limit.maxfiles.plist
  sudo chmod 644 /Library/LaunchDaemons/limit.maxfiles.plist
  sudo launchctl load -w /Library/LaunchDaemons/limit.maxfiles.plist
  # Verify:
  launchctl limit maxfiles   # should show 65536 200000
  ```
  Risk: MEDIUM (requires sudo, takes effect immediately, survives reboot). Persistence: PERMANENT.

### 2. Resolve duplicate bridge processes

The LaunchAgent (`com.mems26.bridge.plist` with KeepAlive+RunAtLoad) conflicts with `start_all.sh`'s screen-based bridge launch. Choose ONE:

- **Option A (recommended):** Keep the LaunchAgent as the canonical bridge launcher. Remove the bridge section from `start_all.sh` (or make it detect the LaunchAgent PID and skip). Add `ulimit -n 10240` inside the plist's bash command.
- **Option B:** Remove the LaunchAgent: `launchctl unload ~/Library/LaunchAgents/com.mems26.bridge.plist` and delete the plist. Let `start_all.sh` manage everything.

Right now, kill the duplicate: `kill 5000` (keep the LaunchAgent-managed PID 547). Risk: LOW.

### 3. Commit the P27.5a work-in-progress files

Untracked files that should be committed:
```
backend/v9/services/bar_integrity.py      (1725 bytes)
tests/v9/services/test_bar_integrity.py   (3874 bytes)
docs/reports/handoff/*.md                  (5 files)
docs/architecture/                         (new dir)
docs/reports/stage_runs/*.log              (3 files)
```
Suggested commit message:
```
feat(P27.5a): bar integrity service + handoff docs + stage run logs

- backend/v9/services/bar_integrity.py: bad-bar detection/filtering
- tests: test_bar_integrity.py (P27.5a TDD scaffold)
- docs/reports/handoff/: MEGA_PROMPT, NEXT_CHAT_PROMPT, SESSION_LOG, GANTT, PROMPT_LIST
- docs/reports/stage_runs/: status check logs from 2026-05-16
```
Risk: LOW. **Do not run** — just propose.

### 4. Add pre-flight ulimit guard to start_all.sh

At the top of `start_all.sh`, after line 20, add:
```bash
if [ "$(ulimit -n)" -lt 4096 ]; then
  echo "FATAL: ulimit -n is $(ulimit -n) — must be >= 4096."
  echo "Fix: see docs/reports/handoff/DIAGNOSTIC_REPORT_2026-05-16-2245.md §7.1"
  exit 1
fi
```
Risk: LOW. Prevents the cascading EMFILE crash from even starting.

### 5. Replace screen orchestration with nohup + PID files

`screen` sessions are not found (empty socket dir), yet processes ARE running (via LaunchAgent + direct launch). The check_status.sh script checks for `screen -ls | grep mems26_*` which produces false negatives when processes run outside screen. Recommendation:
- Use `nohup ... &` with PID written to `/tmp/mems26_{service}.pid`
- check_status.sh reads PID files and verifies with `kill -0`
- Avoids screen dependency entirely

Risk: LOW. Document only — do not apply.

### 6. Sanity-check sysmond

`sysmond` is not in the launchctl list. This is Apple's system monitoring daemon. If it's down, `pgrep` may behave unexpectedly on older macOS versions. Diagnostic:
```bash
sudo launchctl kickstart -k system/com.apple.sysmond
```
Risk: LOW (Apple system service, idempotent). Requires sudo.

### 7. Clean stale .next cache

The 171 MB `.next/dev` directory is from a crashed session. Before next `npm run dev`:
```bash
rm -rf frontend/v9/.next
```
Risk: LOW (will be regenerated on next dev start, ~30s compile time).

## 8. Concrete next step

**Kill the duplicate bridge process (PID 5000), apply the permanent maxfiles LaunchDaemon (Option B in fix #1), then reboot.** After reboot, verify `launchctl limit maxfiles` shows 65536/200000. Then run `start_all.sh` from Terminal — it should raise ulimit to 10240, start backend + frontend without EMFILE, and skip bridge (already running via LaunchAgent). Once the stack is confirmed stable, commit the P27.5a files and proceed with the MEGA_PROMPT_P27_5A.md work. Do NOT attempt to start the frontend until the file descriptor limit is permanently fixed — it will crash the machine again.

## 9. Raw command outputs

### ulimit -a (this shell)
```
core file size          (blocks, -c) 0
data seg size           (kbytes, -d) unlimited
file size               (blocks, -f) unlimited
max locked memory       (kbytes, -l) unlimited
max memory size         (kbytes, -m) unlimited
open files                      (-n) 1048575
pipe size            (512 bytes, -p) 1
stack size              (kbytes, -s) 8192
cpu time               (seconds, -t) unlimited
max user processes              (-u) 2784
virtual memory          (kbytes, -v) unlimited
```

### launchctl limit
```
cpu         unlimited      unlimited      
filesize    unlimited      unlimited      
data        unlimited      unlimited      
stack       8388608        67104768       
core        0              unlimited      
rss         unlimited      unlimited      
memlock     unlimited      unlimited      
maxproc     2784           4176           
maxfiles    256            unlimited      
```

### sysctl kern.*
```
kern.maxproc: 4176
kern.maxprocperuid: 2784
kern.maxfiles: 122880
kern.maxfilesperproc: 61440
```

### Process counts
```
Total processes: 512
User processes: 318
```

### pgrep MEMS26 services
```
547 Python bridge/json_bridge.py
5000 Python bridge/json_bridge.py
5143 Python uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### lsof TCP listeners
```
Port 3000: nothing listening
Port 8000: Python PID 5143 (127.0.0.1:8000 LISTEN)
Port 8765: nothing listening
```

### screen -ls
```
No Sockets found in /var/folders/f3/0p00vq9x5y5_qrhdl996b18r0000gn/T/.screen.
```

### LaunchAgent plist (com.mems26.bridge)
```
Label: com.mems26.bridge
RunAtLoad: true
KeepAlive: true
ThrottleInterval: 30
WorkingDirectory: /Users/michael/Downloads/mems26_web_git
stdout: /tmp/bridge.log
stderr: /tmp/bridge.err.log
```

### git status -sb
```
## stabilize/mems26-local-truth-2026-05-16
 M bridge/v9_streams/__pycache__/__init__.cpython-39.pyc
 M bridge/v9_streams/__pycache__/base_stream.cpython-39.pyc
?? backend/v9/services/bar_integrity.py
?? docs/architecture/
?? docs/reports/handoff/CLAUDE_CODE_DIAGNOSE_REPORT.md
?? docs/reports/handoff/GANTT_TO_LIVE.md
?? docs/reports/handoff/NEXT_CHAT_PROMPT.md
?? docs/reports/handoff/PROMPT_LIST_TO_LIVE.md
?? docs/reports/handoff/SESSION_LOG_2026-05-16.md
?? docs/reports/stage_runs/status_check_20260516_175609.log
?? docs/reports/stage_runs/status_check_20260516_181530.log
?? docs/reports/stage_runs/status_check_20260516_200030.log
?? tests/v9/services/test_bar_integrity.py
```

### git log --oneline -25
```
04ade4b fix(infra): harden start_all + Next dev to prevent EMFILE/Watchpack crashes
63909d5 docs(handoff): mega prompt for P27.5a — backend bad-bar fix
419f4cc fix: stabilize bridge startup diagnostics
5c89729 docs: Prompt 28 — replay smoke run (11/11 pass)
d8246a9 feat: Prompt 27 — stage runner automation + replay validation plan
5c28519 docs: UAT report artifact — Prompt 5 (11/13 pass, auto-generated)
cc8cc8c docs: Woodies remaining gaps after Prompt 5 audit
fd626dd feat: Prompt 26b — TPO + TradeManager use market_clock (replay-safe)
e09ecaf feat: Prompt 26a — replay clock mode
72ab15d fix: Prompt 25b — advisory context integration proof
647af60 feat: Prompt 25 — cross-system integration proof (11 tests)
1d9aa1e docs: Prompt 24 — final System Completion Board reconciliation
f3197c8 feat(s4): Prompt 23 — prove Woodies runtime contract
b076cb6 fix(s3): route footprint fires through pre-fire gateway
22c0668 docs: PROMPT 5 quality report + LIVE readiness audit · GATE 5
9d6ea15 feat(woodies): UFL/UFH bypass verification in A4+B4 · 5 new scenarios (PROMPT 5 · 5.2)
aafb699 fix(woodies): resolve 14 test failures · ZLR spec-aligned + HFE consistency (PROMPT 5 · 5.1)
634b483 fix(s1): Prompt 21c pd context degraded proof
c9ef075 docs: PROMPT 4 quality report · GATE 4
5a37092 feat(woodies): full E2E flow · 5 scenarios · entry to terminal (PROMPT 4 · 4.3)
6deb8e4 fix(s1): Prompt 21b — pd_close from bars last close, not POC
908f7f8 feat(woodies): execution bridge · D-067 Hybrid · 4 methods (PROMPT 4 · 4.2)
a60d1b0 feat(woodies): 18 terminal states emission · DB + Redis + Slack (PROMPT 4 · 4.1)
fc6a319 feat(s1): Prompt 21 — wire pd_high/pd_low/pd_close from v9_bars_5min fallback
48fcc94 docs: PROMPT 3 quality report · GATE 3
```

### git stash list
```
stash@{0}: On stabilize/mems26-local-truth-2026-05-16: pre-P27.5a: 2026-05-16 frontend + scripts hardening (carry-forward)
```

### File counts
```
frontend/v9/src: 105 files
frontend/v9/node_modules: 25,519 files
Total tracked files in repo: 915
```

### Node/npm
```
node: v24.10.0
npm: 11.6.1
```

### Changes since 2026-05-15
```
04ade4b 2026-05-16 fix(infra): harden start_all + Next dev to prevent EMFILE/Watchpack crashes
419f4cc 2026-05-16 fix: stabilize bridge startup diagnostics
d8246a9 2026-05-16 feat: Prompt 27 — stage runner automation + replay validation plan
3370656 2026-05-16 fix(s4): check V9 health directly
856ef46 2026-05-16 ops: add Slack one-way summaries
2b33bc8 2026-05-15 feat(frontend): wire Day Type components to V9 endpoint with V1 fallback
```

---

*Report generated by Claude Code (Terminal.app) — diagnostic only, no mutations made.*
