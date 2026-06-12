# Migration Runbook: Mac → Trading Machine (2026-06-13)

**Goal:** Move the full MEMS26 stack from Michael's MacBook to the dedicated trading machine.
MacBook becomes dev-only afterward. Standing Decisions stay default-OFF in code.

---

## 1. Repository + Git State

```bash
# On MacBook — get current state
cd /Users/michael/Downloads/mems26_web_git
git log --oneline -5          # verify HEAD = latest commit
git tag -l "*anchor*"         # should show pre-anchor-trial-2026-06-12 + anchor-trial-2026-06-12
git stash list                # any uncommitted work?
git status --short            # clean?

# On trading machine:
git clone <repo-url> /path/to/mems26_web_git
cd /path/to/mems26_web_git
git checkout main             # or whatever branch
git log --oneline -5          # verify matches MacBook
```

## 2. Environment Variables (.env)

**Critical:** Copy the full `.env` — all 20+ flags must match.

```bash
# On MacBook — list active flags:
grep -v '^#\|^$' .env | wc -l    # count: should be ~25 lines
grep '=1$\|=true$\|=yes$' .env   # active flags (expect ~20)

# Copy to trading machine:
scp .env trading-machine:/path/to/mems26_web_git/.env
```

**Active flags as of 2026-06-12 evening (verify with `grep`):**
```
S2_ATR_RELATIVE=true         S3_RELATIVE=true
S1_CVD_OPENING=true          S1_IB_WIDTH_ATR=true
S1_DAYTYPE_STAGING=true      S2_VSA_VOLUME=1
S3_MUTE=1                    S1_DYNAMIC_RECLASS=true
S1_LIVE_RECLASS=true         STOP_ANCHORS_V2=1
S4_EXTREME_TREND_RELABEL=true  S1_PROVISIONAL_DAYTYPE=1
FOOTPRINT_DISABLED=1         PATTERN_RISK_CAPS=1
S2_DETECTION_LOG=1           RUNNER_TARGETS_V1=1
S2_CHART_ALL_DAYTYPES=1      S2_VOL_ADAPTIVE=1
GIANT_BAR_STOP_V1=1          PATTERN_LOSS_BREAKER=1
```

Also copy non-flag env vars: `DATABASE_URL`, `BRIDGE_TOKEN`, `CORS_ORIGINS`, etc.

## 3. LaunchAgents (2 services — PATHS ARE ABSOLUTE)

### 3a. Backend (`com.mems26.backend`)

```bash
# On MacBook — find the plist:
ls ~/Library/LaunchAgents/com.mems26.backend.plist

# Copy to trading machine:
scp ~/Library/LaunchAgents/com.mems26.backend.plist trading-machine:~/Library/LaunchAgents/

# ⚠️ EDIT PATHS in the plist on the trading machine:
# - WorkingDirectory → /path/to/mems26_web_git (on trading machine)
# - ProgramArguments → correct Python path
# - EnvironmentVariables → if any hardcoded paths
# - StandardOutPath / StandardErrorPath → /tmp/backend.log, /tmp/backend.err.log

# Load:
launchctl load ~/Library/LaunchAgents/com.mems26.backend.plist

# Verify:
curl -s http://localhost:8000/api/v9/status | head -5
# Should return 200

# Key behavior: kill PID → launchd respawns automatically with .env loaded
```

### 3b. Bridge

```bash
# On MacBook — find the bridge LaunchAgent:
ls ~/Library/LaunchAgents/com.mems26.bridge*.plist

# Copy + edit paths (same process as backend)
# Verify after load:
tail -3 /tmp/bridge.err.log    # should show push activity
```

## 4. PostgreSQL Database

```bash
# On MacBook — dump:
/Applications/Postgres.app/Contents/Versions/18/bin/pg_dump -Fc mems26 > mems26_backup.dump

# Copy to trading machine:
scp mems26_backup.dump trading-machine:~/

# On trading machine — restore:
createdb mems26
pg_restore -d mems26 mems26_backup.dump

# Verify:
psql -d mems26 -c "SELECT count(*) FROM v9_trades;"
psql -d mems26 -c "SELECT count(*) FROM v9_bars_5min WHERE ts::date = CURRENT_DATE;"
```

## 5. Sierra Chart + DLL Study

```bash
# Sierra export directory (source of truth):
# MacBook: ~/SierraChart_Data/v9_export/
# Trading machine: set Input-4 export path in Sierra Study settings

# Copy DLL ops reference:
scp docs/SIERRA_DLL_OPS.md trading-machine:/path/to/mems26_web_git/docs/

# Sierra files to verify on trading machine:
# - 5min.json, 5min_continuous.json, woodies_5min.json, tpo.json
# - cumulative_delta.json, tick_reversal_12.json, tick_reversal_15.json
# - footprint.json, volume_profile.json, imbalance_flags.json
# - stacked_imbalances.json, woodies_30min.json, woodies_diag.json, live_price.json

# ⚠️ The bridge reads from ~/SierraChart_Data/v9_export/ — update path if different
# on trading machine. Check bridge config / stream files.
```

## 6. Frontend

```bash
# On trading machine:
cd /path/to/mems26_web_git/frontend/v9
npm install
npx next build
npx next dev    # or start with LaunchAgent

# Verify: open http://localhost:3000/trades in browser
# The browser must be on the SAME machine (localhost)
```

## 7. PRE_TRADE_PROTOCOL Acceptance Test

Run `docs/runbooks/PRE_TRADE_PROTOCOL.md` checklist on the trading machine:

```bash
# 1. Backend health
curl -s http://localhost:8000/api/v9/status | python3 -m json.tool | head -5

# 2. Bridge streaming
tail -5 /tmp/bridge.err.log   # should show push activity every ~3s

# 3. Bars flowing
psql -d mems26 -c "SELECT max(ts), count(*) FROM v9_bars_5min WHERE ts::date = CURRENT_DATE;"

# 4. Flags loaded (check from backend log at startup)
grep "PATTERN_RISK_CAPS\|RUNNER_TARGETS_V1\|S2_DETECTION_LOG" /tmp/backend.err.log | tail -3

# 5. Frontend accessible
curl -s http://localhost:3000/trades | head -5

# 6. Trades page renders (open in browser, verify trade cards load)
```

## 8. Rollback Plan

If anything goes wrong on trading machine:

```bash
# Option A: Flag rollback (immediate, no code change)
# Comment out problematic flags in .env, kill backend (launchd respawns)

# Option B: Git rollback to pre-anchor-trial
git checkout pre-anchor-trial-2026-06-12
# Then restart backend

# Option C: Full rollback — MacBook takes over again
# Just start the LaunchAgents on MacBook (they're still installed)
```

## 9. Standing Decisions Reminder

**All gates are default-OFF in code.** The flags in `.env` ENABLE features.
If `.env` is missing or empty, the system behaves like pre-trial (safe default).

Do NOT enable:
- `S2_CHOPPINESS_GATE` — Standing Decision OFF
- `LAYER0_CHOP_GATE` — Standing Decision OFF
- `S2_REQUIRE_COT_AMT` — Standing Decision OFF

## Checklist

- [ ] Repo cloned + correct HEAD
- [ ] Tags present (pre-anchor-trial, anchor-trial)
- [ ] .env copied with all 20+ flags
- [ ] Backend LaunchAgent installed + running (health 200)
- [ ] Bridge LaunchAgent installed + running (pushes flowing)
- [ ] PostgreSQL restored + verified
- [ ] Sierra Chart export path configured
- [ ] Frontend built + accessible
- [ ] PRE_TRADE_PROTOCOL passed
- [ ] Trades page loads with data
