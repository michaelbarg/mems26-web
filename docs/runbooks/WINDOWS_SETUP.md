# MEMS26 on the Windows (Sierra) machine — setup + sync-from-Mac
**Goal:** Mac = dev (Cowork + me). Windows = trading machine with Sierra, kept updated from the Mac via **GitHub**. Cowork + Claude Code installed on BOTH → I work on either; git syncs them.

> Sierra Chart is native Windows, so the trading machine is the natural home. The Mac stays dev. Remote = `origin` → `github-mems26:michaelbarg/mems26-web.git` (branch `stabilize/mems26-local-truth-2026-05-16`).

---

## A. One-time install on Windows
1. **Claude Desktop (Cowork)** + **Claude Code** (CLI).
2. **Git for Windows**, **Python 3.11** (3.9+ ok), **PostgreSQL 16**, **Node.js LTS**.
3. **GitHub access:** add this machine's SSH key to GitHub, OR use HTTPS + a Personal Access Token. Test: `git ls-remote <url>`.
4. **Clone:**
   ```bat
   git clone https://github.com/michaelbarg/mems26-web.git C:\mems26_web_git
   cd C:\mems26_web_git
   git checkout stabilize/mems26-local-truth-2026-05-16
   ```
5. **Python deps:** `pip install -r requirements.txt`
6. **Frontend:** `cd frontend\v9 && npm install`

## B. .env (copy from Mac, fix the paths)
Copy the Mac `.env` to `C:\mems26_web_git\.env`, then change ONLY the path/host values:
```
DATABASE_URL=postgresql://localhost/mems26          # ok as-is
CLOUD_URL=http://localhost:8000                      # ok — bridge stays localhost-only
V9_EXPORT_DIR=C:\SierraChart\Data\v9_export          # <-- Windows Sierra export path (set to YOUR Sierra path)
```
All the feature flags (DAYTYPE_PLAYBOOK, RUNNER_TARGETS_V1, anchor-trial, etc.) copy verbatim. `backend/main.py` loads `.env` in code, so they apply on Windows too.

## C. PostgreSQL
```bat
createdb mems26
:: optional — restore the Mac data (else it starts fresh, which is fine):
:: pg_restore -d mems26 mems26.dump
```

## D. Sierra Chart (native Windows) — chartbook + studies
The chart layout + ALL studies live in one **chartbook** file. On the Mac it is:
```
/Users/michael/SierraChart/Data/AAMichael_lap25.Cht   (backups in ~/SierraChart/Backups/)
```
Steps on Windows:
1. **Copy the chartbook** `AAMichael_lap25.Cht` → the Windows Sierra `Data\` folder
   (e.g. `C:\SierraChart\Data\`). It carries the whole layout + every study's settings.
2. **Compile the study DLL on Windows:** the study SOURCE is in this repo (`sc_study/`,
   e.g. `MES_AI_DataExport.cpp`) and arrives via git. In Sierra: copy it to
   `ACS_Source\`, run **Analysis ▸ Build ▸ Remote Build** to produce the Windows DLL,
   then reload the study (see `docs/runbooks/SIERRA_DLL_OPS.md`).
3. Open the chartbook in Sierra → set **every chart symbol to MESU26 (September)**, not June.
4. In the export study, set **Input-4 (export dir)** = the same folder as `V9_EXPORT_DIR` (§B).
5. Sanity: files appear/update in that folder (`mes_ai_data.json`, `woodies_5min.json`, ...).

> The chartbook (.Cht) is a binary file, not code — it transfers as a FILE (USB / cloud /
> the migration bundle), NOT via git. The study .cpp DOES come via git.

## E. Run (Windows replaces LaunchAgents with .bat + Task Scheduler)
Create these in `scripts\windows\` (templates — adjust the path/token):

**start_backend.bat**
```bat
@echo off
cd /d C:\mems26_web_git
set V9_DISABLE_WATCHDOG=1
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
**start_bridge.bat**
```bat
@echo off
cd /d C:\mems26_web_git
set CLOUD_URL=http://localhost:8000
set V9_EXPORT_DIR=C:\SierraChart\Data\v9_export
set BRIDGE_TOKEN=michael-mems26-2026
python bridge\json_bridge.py
```
**Auto-start:** Task Scheduler → "At log on" → run each .bat (or use NSSM to run them as Windows services). Frontend: `cd frontend\v9 && npx next dev` (same machine, localhost:3000).

## F. The daily UPDATE-FROM-MAC flow
On the **Mac** (me/you): `git add -A && git commit -m "..." && git push`.
On **Windows**, run **update_from_mac.bat**:
```bat
@echo off
cd /d C:\mems26_web_git
git pull --rebase
pip install -r requirements.txt
cd frontend\v9 && npm install && cd ..\..
:: restart services: stop the start_backend/start_bridge windows (or Task Scheduler), then start them again
echo Updated. Restart backend + bridge to load changes.
```

## G. Continue developing with Cowork on Windows
Open **Cowork** on Windows → connect the `C:\mems26_web_git` folder. I work there exactly like on the Mac. Whatever I commit, `git push` here → `git pull` there (and vice-versa) keeps both in sync.

## H. Verify (both machines)
`curl http://localhost:8000/health` → ok · `tail` bridge log shows pushes · `psql -d mems26 -c "SELECT max(ts) FROM v9_bars_5min_woodies;"` recent · dashboard loads at `http://localhost:3000` · run `docs/runbooks/PRE_TRADE_PROTOCOL.md`.
