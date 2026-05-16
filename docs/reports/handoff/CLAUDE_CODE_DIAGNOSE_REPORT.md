# Claude Code — MEMS26 Local Environment Diagnostic & Report Prompt

**Status:** ready to paste into Claude Code (`claude`) running from a real Terminal.app on the user's Mac.
**Mode:** READ-ONLY / DIAGNOSTIC. **Do not start, kill, or restart any service.** Do not modify any source file, do not run `git add`/`commit`/`reset`/`stash`/`restore`. Just gather evidence and produce a structured report.
**Author:** Cursor agent (multitask session)
**Last updated:** 2026-05-16

---

## How to use

1. Open Terminal.app (not Cursor's terminal). Make sure your Mac is on a fresh login.
2. `cd /Users/michael/Downloads/mems26_web_git`
3. Run `claude` to start Claude Code in this repo.
4. Paste **everything between the `PASTE FROM HERE` and `PASTE TO HERE` markers** below as one message.
5. Let it run to completion. When it finishes, copy the final report back into the Cursor chat so the work can resume safely.

> The whole point: Cursor's shell tool keeps getting reaped or sandbox-blocked when Next.js+Turbopack+Watchpack overwhelms macOS's default ulimit. Claude Code in a real terminal does not have that limitation, so we use it to **diagnose** the problem from outside the failing environment.

---

## PASTE FROM HERE

You are Claude Code running in a real Terminal.app shell on macOS, in the user's MEMS26 trading-system repo at `/Users/michael/Downloads/mems26_web_git`. Your job is **DIAGNOSTIC ONLY**. Do not start, kill, restart, or modify any service. Do not modify any source file. Do not run `git add`, `git commit`, `git reset`, `git stash`, `git restore`, `git checkout`. Read, inspect, run safe shell queries, and produce a structured report at the end.

### Project context (one paragraph)

MEMS26 is a local autonomous MES futures trading system. Data flows **Sierra Chart (ACSIL DLL) → Python Bridge (`bridge/json_bridge.py`) → FastAPI Backend (`backend/main:app`, port 8000) → Next.js Frontend (`frontend/v9`, port 3000)**. There are 6 systems (S1 Day Type, S2 Five-Min T1, S3 Footprint T3, S4 Woodies T2, S5 TPO, S6 Killzone). Trading modes are SHADOW → DEMO → LIVE. Constitution V3 + Master Index V2 are the spec; D-074 says Woodies runs on 5-minute timeframe. No SHADOW activation until everything is wired and reliable.

### The failure mode I need you to diagnose

Every time the user tries to bring up the stack via `scripts/start_all.sh` (or `MEMS26 Restart.command` on the Desktop, which calls `scripts/restart_all.sh` → `scripts/start_all.sh`), the machine becomes unusable within ~30–120 seconds. Symptoms:

- Next.js dev server reaches `Ready in …ms`, then `Watchpack Error (watcher): Error: EMFILE: too many open files, watch` repeats indefinitely.
- Process count climbs.
- New shells stop spawning with `forkpty: Resource temporarily unavailable` (EAGAIN).
- Cursor's shell tool returns empty 0 ms output (its child processes can't fork either).
- Only a logout or reboot recovers.

The root cause we currently believe is **macOS default `ulimit -n` is 256**, and Next.js 16 + Turbopack runs Watchpack alongside, which opens hundreds of file watchers and saturates the FD table. Several fixes were applied in previous sessions but kept getting wiped because they were never committed to git. Latest fix state may be partially re-applied (uncommitted) right now — verify in step 1 below.

### Hard rules for this run

1. **READ-ONLY.** No source edits, no git mutations, no `kill`, no `screen -X`, no `launchctl unload`.
2. **Do not run** `scripts/start_all.sh`, `scripts/restart_all.sh`, `npm run dev`, `python3 bridge/json_bridge.py`, `uvicorn ...`, or anything else that starts a long-running service.
3. **Safe queries only:** `cat`, `grep`, `ls`, `git status`/`log`/`diff`/`show` (without mutation flags), `lsof`, `ps`, `pgrep`, `sysctl`, `launchctl limit`, `ulimit -a`, `node --version`, `npm config get`, `python3 --version`, `curl -m 5` to localhost (only to *probe* whether something is already running — don't start anything).
4. **Be exhaustive.** This is the third round we hit this. The user wants every variable surfaced, even if obvious.
5. **Do not** `sudo` anything in this run. List `sudo` commands as recommendations only.
6. If any check requires elevated privileges, list it in the "recommended next commands" section instead of running it.

### Investigation steps — run them in order, capture output

#### 1. Current file state — confirm which fixes are in place vs missing

Run and quote relevant lines from:

- `scripts/start_all.sh` — look for `ulimit -n 10240`, `V9_DISABLE_WATCHDOG=1`, `WATCHPACK_POLLING=true`, `CHOKIDAR_USEPOLLING=true`, and confirm whether backend launches with `--host 127.0.0.1` or `--host 0.0.0.0`, and whether frontend launches with `WATCHPACK_POLLING` env or as a bare `npm run dev`.
- `scripts/restart_all.sh` — does it just call stop_all + start_all?
- `scripts/check_status.sh` — what does it grep for? (Heads-up: it greps for `screen` sessions named `mems26_*`; nohup-launched processes will register as false-negative.)
- `~/Desktop/MEMS26 Restart.command` (note the space — quote the path) — does it `ulimit -n 10240` before calling restart_all.sh?
- `frontend/v9/next.config.ts` — is `turbopack.root: process.cwd()` set?
- `frontend/v9/package.json` — is the `dev` script `next dev -H 127.0.0.1` or just `next dev`?
- `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` — search for `attributionLogo`, `looksOk`, `age_ms`, and the regex `withZ` in `tsToUnix`. Report which (if any) are present. These are client-side guards from a prior session; backend P27.5a should replace them, but they are tracked so we know what state we're in.
- `frontend/v9/src/v9/components/layout/V9Dashboard.tsx` — confirm `ChartV5b` is the only chart import and that `VolumePanel`, `SystemPanelsBar`, `react-resizable-panels` are NOT imported anymore (single-pane).
- `backend/v9/services/bar_integrity.py` and `tests/v9/services/test_bar_integrity.py` — verify they exist (P27.5a in progress) and report file sizes.
- `docs/reports/handoff/MEGA_PROMPT_P27_5A.md` — verify it exists.

#### 2. Git state — see what's tracked, untracked, and recently committed

```
cd /Users/michael/Downloads/mems26_web_git
git status -sb
git log --oneline -25
git log --oneline -10 -- scripts/start_all.sh
git log --oneline -10 -- frontend/v9/next.config.ts frontend/v9/package.json
git log --oneline -10 -- frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx
git show --stat HEAD
git stash list
```

Identify **why** previous hardening got wiped. Suspect: an earlier `git stash`/`git restore` from a parallel session reverted uncommitted hardening edits. Verify or refute.

#### 3. OS-level resource limits — the smoking gun

```
ulimit -a                       # current shell
launchctl limit                 # system-wide hard/soft (sysadmin level)
sysctl kern.maxproc             # max processes total
sysctl kern.maxprocperuid       # per-user
sysctl kern.maxfiles            # max open files total
sysctl kern.maxfilesperproc     # max open files per process
ps -A | wc -l                   # processes right now
echo "user procs: $(ps -u $USER | wc -l)"
```

Compare against required:
- `ulimit -n` should be **≥ 4096** for Next.js dev. macOS default is **256** (huge red flag).
- `kern.maxfilesperproc` should be **≥ 10240**.
- `kern.maxproc` should be **≥ 2048**.

#### 4. Process/service current state — confirm everything is down (or up)

```
pgrep -fl "json_bridge|uvicorn backend|next dev|turbopack" || echo "no MEMS26 processes"
lsof -nP -iTCP:3000 -sTCP:LISTEN 2>&1 | head
lsof -nP -iTCP:8000 -sTCP:LISTEN 2>&1 | head
lsof -nP -iTCP:8765 -sTCP:LISTEN 2>&1 | head
screen -ls 2>&1 | head
launchctl list | grep -iE "mems26|bridge" || echo "no launchd MEMS26 entry"
ls -la ~/Library/LaunchAgents/ 2>/dev/null | grep -iE "mems26|bridge" || echo "no MEMS26 LaunchAgent"
```

Also check if `sysmond` is up (it has been observed down after some reboots, which breaks `pgrep`):
```
launchctl list | grep sysmond || echo "sysmond not running — pgrep will fail"
```

#### 5. Node/Next environment

```
node --version
npm --version
ls -la frontend/v9/node_modules/.bin/next 2>/dev/null && echo "next CLI present"
ls -la frontend/v9/.next 2>/dev/null | head    # stale cache from prior crash?
cat frontend/v9/.next/BUILD_ID 2>/dev/null || echo "no BUILD_ID — clean"
du -sh frontend/v9/.next 2>/dev/null
du -sh frontend/v9/node_modules
du -sh frontend/v9/node_modules/next 2>/dev/null
```

If `.next/` exists and is stale, that's a known cause of the RSC manifest 500 errors after EMFILE crashes. Note its size but don't delete it.

#### 6. Bridge / Sierra prerequisites

```
ls -la /Users/michael/SierraChart_Data/v9_export 2>/dev/null | head
stat -f "%Sm" /Users/michael/SierraChart_Data/v9_export 2>/dev/null
ls -la /tmp/bridge.log /tmp/backend.log /tmp/frontend.log /tmp/start_bridge.sh 2>/dev/null
tail -n 20 /tmp/bridge.log 2>/dev/null
echo "--- .env ---"
test -f /Users/michael/Downloads/mems26_web_git/.env && grep -E "^(V9_|BRIDGE_|CLOUD_)" /Users/michael/Downloads/mems26_web_git/.env | sed 's/=.*/=***/' || echo "no .env"
```

#### 7. Repo's existing handoff & roadmap docs — read but do not modify

```
ls -la docs/reports/handoff/
wc -l docs/reports/handoff/*.md
head -30 docs/reports/handoff/NEXT_CHAT_PROMPT.md
head -30 docs/reports/handoff/MEGA_PROMPT_P27_5A.md
head -30 docs/reports/SYSTEM_COMPLETION_CONTROL_BOARD.md 2>/dev/null
```

#### 8. What changed in the last ~24 h that could have introduced the regression

```
git log --since="2026-05-15 00:00" --pretty=format:"%h %ad %s" --date=short -- scripts/ frontend/v9/next.config.ts frontend/v9/package.json frontend/v9/src/v9/components/
```

#### 9. Independent EMFILE root-cause probe (READ-ONLY)

Without starting Next.js, find out **how many file watchers** would be opened. Heuristic counts:

```
echo "files under frontend/v9/src (count):"
find frontend/v9/src -type f 2>/dev/null | wc -l
echo "files under frontend/v9/node_modules (count, will be huge):"
find frontend/v9/node_modules -type f 2>/dev/null | wc -l
echo "total tracked files in repo:"
git ls-files | wc -l
```

If the project file count (excluding `node_modules`) is in the low thousands, then **256 ulimit is the bottleneck**, not project size. Confirm.

### Final report — produce this exactly

After the queries above, write a Markdown report to stdout (and save a copy to `docs/reports/handoff/DIAGNOSTIC_REPORT_<YYYY-MM-DD-HHMM>.md`). It must have the following sections, populated from real data you collected:

```
# MEMS26 Local Diagnostic Report — <timestamp>

## 1. Current file state
- start_all.sh ulimit fix:         [present | absent]   evidence: <line numbers>
- start_all.sh WATCHPACK_POLLING:  [present | absent]   evidence: ...
- start_all.sh backend host:       [127.0.0.1 | 0.0.0.0]
- next.config.ts turbopack.root:   [present | absent]
- package.json dev script:         [exact value]
- ChartV5b client guards:          [present | absent | partial]   evidence: ...
- V9Dashboard single-pane:         [yes | no]
- bar_integrity.py:                [exists | missing]   size: N bytes
- MEGA_PROMPT_P27_5A.md:           [exists | missing]

## 2. Git state
- branch: ...
- uncommitted tracked files:  [list]
- untracked files:            [list]
- last 5 commits touching hardening files: ...
- stashes: [n stashes / none]
- diagnosis of likely cause of the previous wipe: [free text]

## 3. OS resource limits — RED/GREEN audit
| limit | current | needed | status |
| ulimit -n (open files) | ... | ≥ 4096 | RED/GREEN |
| kern.maxfilesperproc   | ... | ≥ 10240 | ... |
| kern.maxfiles          | ... | ≥ 49152 | ... |
| kern.maxproc           | ... | ≥ 2048 | ... |
| processes now          | ... | < ~500 idle | ... |
| sysmond                | [up/down] | up | ... |

## 4. Service state right now
- Bridge:   [running PID … / not running]
- Backend:  [running PID … / not running]    health: [200 / unreachable]
- Frontend: [running PID … / not running]
- screen sessions: [list or none]
- launchd entries: [list or none]

## 5. Next.js environment
- node: ...
- npm: ...
- .next cache: [absent | N MB] [clean | stale]
- node_modules: N MB
- frontend src file count: ...

## 6. Sierra / bridge prerequisites
- v9_export dir: [exists | missing]   last modified: ...
- .env keys present: [V9_*, BRIDGE_*, CLOUD_*]

## 7. Recommended FIX PLAN — ordered, with risk assessment
For each item, give: exact command(s), risk (low/med/high), persistence (transient/session/permanent), whether sudo is required.

1. **Permanent OS-level file-descriptor limit** — most important.
   - Option A: per-user, via `ulimit -n 10240` in `~/.zshrc` / `~/.zprofile`. Transient per-shell unless every shell sources it. Risk: low. No sudo.
   - Option B: system-wide LaunchDaemon at `/Library/LaunchDaemons/limit.maxfiles.plist`. Permanent, survives reboot. Risk: medium (requires sudo, reboot to take effect). Provide the exact plist contents and `sudo launchctl load -w …` command.
2. **Commit the hardening edits** — `scripts/start_all.sh`, `frontend/v9/next.config.ts`, `frontend/v9/package.json` — so they survive the next `git stash`/`git restore`. Risk: low. Provide the exact `git diff --stat` and a suggested commit message. **Do not run** the commit yourself — just propose it.
3. **Replace `screen` orchestration with `nohup` + PID files** in start_all.sh — `screen` sessions are reaped under sandbox conditions and `check_status.sh` produces false negatives. Document the change but do not apply it.
4. **Add a pre-flight `ulimit -n` guard** at the top of start_all.sh that aborts with a clear error if `ulimit -n < 4096`, telling the user to apply step 1 first.
5. **Sanity-check `sysmond`** — if down, `sudo launchctl kickstart -k system/com.apple.sysmond`. Provide the diagnostic to confirm before doing it.

## 8. Concrete next step
One paragraph saying exactly what should be done next, in plain language, given the diagnostic. (Do not do it. Just say it.)

## 9. Raw command outputs
Append all command outputs collected in steps 1–9 above, in fenced code blocks, for evidence trail.
```

Be precise about numbers. Quote file lines with line numbers. Do not summarize away evidence.

When done, **stop**. Do not start anything. Do not commit anything. Reply with the report. The user will copy it back into Cursor.

## PASTE TO HERE

---

## Notes (read after Claude Code returns)

- The likely smoking gun is **section 3 (`ulimit -n`)**. If it's 256, that confirms the root cause and the fix is permanent OS-level configuration, not just script edits.
- **Do not commit anything in Cursor or Claude Code** based on this report alone. Bring the report back here first so we can plan and align with Constitution / D-### decisions.
- The four handoff docs under `docs/reports/handoff/` already contain the broader roadmap. This diagnostic report complements them.
