# MEMS26 Disaster Recovery Runbook

## 1. System Overview

MEMS26 has 4 critical components:

| Component | Host | Recovery Priority |
|-----------|------|-------------------|
| Sierra Chart | Local Mac (CrossOver) | P1 — no data without it |
| Bridge | Local Mac | P1 — data doesn't reach Redis |
| Backend API | Render (cloud) | P2 — auto-deploys from git |
| Frontend | Netlify (cloud) | P3 — auto-deploys from git |

**Recovery time targets:**
- Bridge down → back in 10 min (restart script)
- Sierra config lost → back in 30 min (restore from backup)
- Full local wipe → back in 2 hours (git clone + restore backup + Sierra reinstall)
- Cloud services down → wait for Render/Netlify (nothing local to do)

## 2. Scenario: Bridge Stops Sending Data

**Symptoms:** Frontend shows stale data, Redis `mems26:latest` timestamp > 30s old.

**Steps:**
1. Check if bridge process is running:
   ```bash
   ps aux | grep json_bridge
   ```
2. Check bridge logs for errors
3. Restart bridge:
   ```bash
   cd ~/Documents/GitHub/mems26-web/bridge
   python3 json_bridge.py
   ```
4. Verify data flowing:
   - Frontend shows fresh timestamp
   - Or check Redis directly via Upstash console

**Root causes to investigate:**
- Sierra Chart crashed or frozen (check CrossOver)
- `mes_ai_data.json` not being written (Sierra study issue)
- Redis connection timeout (Upstash rate limit)
- Python crash (check terminal output)

## 3. Scenario: Sierra Chart Data Export Fails

**Symptoms:** `mes_ai_data.json` not updating, bridge running but no new data.

**Steps:**
1. Open Sierra Chart in CrossOver
2. Check study `MES_AI_DataExport` is attached to chart
3. Verify study output path: `/users/michael/SierraChart2/mes_ai_data.json`
4. Check Sierra Chart message log for errors
5. If study gone: re-add from `sc_study/MES_AI_DataExport.cpp`, compile, attach

**Restore config from backup:**
```bash
cd tools/ops-infra
./restore_from_backup.sh <timestamp> --component sierra
```

## 4. Scenario: Local Machine Failure (Full Recovery)

**Steps:**
1. **Git clone** — gets all code:
   ```bash
   git clone https://github.com/michaelbarg/mems26-web.git
   ```
2. **Restore bridge + Sierra from backup:**
   ```bash
   cd mems26-web/tools/ops-infra
   ./restore_from_backup.sh <latest_timestamp>
   ```
3. **Install CrossOver** — download from codeweavers.com
4. **Install Sierra Chart** in CrossOver
5. **Restore Sierra config + studies** (step 2 already did this)
6. **Install Python deps for bridge:**
   ```bash
   cd bridge
   pip3 install aiohttp redis
   ```
7. **Configure `.env` files** — these are NOT in backups. Recreate from password manager:
   - Redis URL (Upstash)
   - Anthropic API key
8. **Start bridge:**
   ```bash
   python3 json_bridge.py
   ```
9. **Verify:** Frontend at mems26.netlify.app shows live data

## 5. Scenario: Backend (Render) Issues

**Symptoms:** Frontend shows "API Error", 500s in console.

**Steps:**
1. Check Render dashboard for deploy status
2. Check Render logs for Python errors
3. Common fixes:
   - Redeploy: push any commit to `main`
   - Environment vars missing: check Render settings
   - Redis timeout: check Upstash status page

**Backend is stateless** — it reads from Redis. No local data to lose.

## 6. Scenario: Frontend (Netlify) Issues

**Symptoms:** Site unreachable or shows old build.

**Steps:**
1. Check Netlify dashboard for deploy status
2. Trigger redeploy from Netlify UI or push to `main`
3. Check build logs for errors

**Frontend is static** — rebuild and deploy fixes most issues.

## 7. Scenario: Redis (Upstash) Data Loss

**Symptoms:** Frontend shows no candles, empty charts.

**Steps:**
1. Check Upstash console for database status
2. Redis data is ephemeral (live market data). Loss means:
   - Current candles gone (rebuilds automatically when bridge runs)
   - Trade journal entries gone (if stored in Redis)
3. Restart bridge — it seeds from Sierra's 200-bar footprint on startup
4. Historical data rebuilds within one trading session

**Prevention:** Trade journal should eventually move to persistent DB.

## 8. Backup Verification Checklist

Run weekly (Friday after market close):

- [ ] `ls ~/mems26-backups/` shows recent backup
- [ ] Backup size is reasonable (not 0 bytes)
- [ ] `./backup_local.sh --dry-run` completes without errors
- [ ] Git repo has no uncommitted changes: `git status`
- [ ] Sierra Chart study compiles without errors
- [ ] Bridge starts cleanly: `python3 json_bridge.py` (Ctrl+C after seeing first data)
- [ ] Frontend loads at mems26.netlify.app
- [ ] Backend responds: `curl https://<render-url>/market/latest`
