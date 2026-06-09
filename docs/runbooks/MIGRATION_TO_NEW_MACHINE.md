# MEMS26 — מדריך מעבר למחשב חדש (סביבת-הפיתוח)

> **מטרה:** להעביר את כל מחסנית-MEMS26 (repo · DB · Sierra+DLL · bridge · backend · frontend · agents) למחשב חדש שיהיה **סביבת-הפיתוח**.
> **כלל-זהב:** המערכת מלאה ב**נתיבים-אבסולוטיים** (`/Users/michael/...`). אם שם-המשתמש או נתיב-ה-repo שונים במחשב החדש — חובה grep-and-replace (סעיף 7). אם זהים — מינימום שינויים.
> נכתב 2026-06-06 · מקור: `docs/ENVIRONMENT.md` + `CLAUDE.md` + `scripts/`. **אני (Cowork) לא יכול לבצע את ההעברה — היא על המכונות שלך; זה צ'קליסט לך/ל-CC.**

## 0 · מה צריך לעבור (מפה)
| רכיב | מיקום נוכחי | אופן-העברה |
|------|-------------|-----------|
| **Repo** | `/Users/michael/Downloads/mems26_web_git` | `git clone` (מקור-אמת) — לא להעתיק עבודה-לא-committed! |
| **DB** | local Postgres `mems26` | `db_backup.sh` → `db_restore.sh`, **או** התחל-נקי (`db_init.sh`) — דאטת-עבר disposable per CLAUDE.md |
| **Sierra Chart** | דרך CrossOver (Wine) | התקנה-ידנית + חשבון Sierra + תצורת chart#5 (סעיף 3) |
| **DLL source** | `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` (מחוץ ל-repo) | מ-`sc_study/` ב-repo → `build_monolithic_cpp.sh --deploy` → Remote Build |
| **Export dir** | `~/SierraChart_Data/v9_export/` | צור ספרייה; הגדר Study Input 4 |
| **Bridge LaunchAgent** | `~/Library/LaunchAgents/com.mems26.bridge.plist` | recreate (סעיף 4) |
| **Secrets** | `.env` + `frontend/v9/.env.local` | **העבר ידנית-מאובטח** (לא ב-git) |
| **Agents מתוזמנים** | `~/Documents/Claude/Scheduled/*/SKILL.md` | העתק תיקייה / recreate (סעיף 6) |

## 1 · דרישות-קדם במחשב החדש (macOS)
- macOS (Apple-Silicon/Intel) · **Python 3.9.7** · **Node 23.x / npm 10.x** · Homebrew.
- `brew install postgresql@16 screen` (וגם `git`, `node`, `python@3.9` אם חסר). `brew services start postgresql@16`.
- CrossOver (ל-Sierra Chart).

## 2 · Repo + תלויות
```bash
git clone <remote> /Users/<user>/Downloads/mems26_web_git   # שמור נתיב זהה אם אפשר
cd /Users/<user>/Downloads/mems26_web_git
pip3 install -r requirements.txt --break-system-packages      # fastapi/uvicorn/sqlalchemy/psycopg2-binary/redis/pydantic/httpx/websockets
cd frontend/v9 && npm install && cd ../..
./scripts/check_env.sh        # מאמת deps+נתיבים — חובה שיחזיר OK לפני המשך
```
⚠️ **אל תעביר `node_modules`/`__pycache__`/`*.pyc`** — התקן מחדש (CLAUDE.md §Generated Files).

## 3 · Database (local Postgres — localhost בלבד, לעולם לא cloud)
```bash
createdb mems26                                  # DB ריק
export DATABASE_URL="postgresql://localhost/mems26"
# אופציה A (נקי, מומלץ לפיתוח): ./scripts/db_init.sh  → הרץ migrations שב-backend/v9/db/migrations/
# אופציה B (העברת-דאטה): במכונה-הישנה ./scripts/db_backup.sh → העבר את ה-dump → ./scripts/db_restore.sh
```
**כלל-קשיח (CLAUDE.md §DB):** `localhost`/`127.0.0.1` בלבד. לעולם לא Render/Upstash-prod-PG. אימות "GO" = soak-מקבילי 0-errors/0-deadlocks ≥10דק'.

## 4 · Bridge LaunchAgent (`~/Library/LaunchAgents/com.mems26.bridge.plist`)
recreate עם הכללים מ-CLAUDE.md (אל תשנה!):
- `CLOUD_URL=http://localhost:8000` (הגשר **מסרב לעלות** אם לא localhost/127.0.0.1).
- `export V9_DISABLE_WATCHDOG="${V9_DISABLE_WATCHDOG:-1}"`.
- **KeepAlive מותנה** (לא `true`):
```xml
<key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
```
- עדכן בתוך ה-plist את נתיב-ה-repo + `V9_EXPORT_DIR` למכונה החדשה.
`launchctl unload/load ~/Library/LaunchAgents/com.mems26.bridge.plist` לאחר עריכה.

## 5 · Sierra Chart + DLL (החלק הידני-ביותר)
1. התקן CrossOver + Sierra Chart; היכנס לחשבון Sierra; שחזר את **chart #5** (MES) + ה-studies.
2. צור `~/SierraChart_Data/v9_export/` והגדר **Study Input 4 = `/Users/<user>/SierraChart_Data/v9_export/`** (נשמר per-chart).
3. בנה ופרוס את ה-DLL: `sc_study/` → `./scripts/build_monolithic_cpp.sh --deploy` → `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` → **Analysis → Build Advanced Custom Study DLL** (Remote Build) → reload study.
4. אמת: `./scripts/verify_sierra_dll_deploy.sh` + בדוק שקבצי-יצוא טריים מופיעים ב-`v9_export/`.
- כללי-DLL (ENVIRONMENT.md): אין `std::max/min` (→`v9_max/v9_min`), אין Windows-paths, אין `GetPersistentString` (→`GetPersistentSCString`). אופס מלא: `docs/runbooks/SIERRA_DLL_OPS.md`.

## 6 · Secrets + Agents
- **`.env`** (repo-root, לא ב-git): `DATABASE_URL` · `V9_EXPORT_DIR` · `CLOUD_URL=http://localhost:8000` · `BRIDGE_TOKEN` · `UPSTASH_REDIS_REST_URL/TOKEN` (אם בשימוש). **`frontend/v9/.env.local`:** `NEXT_PUBLIC_API_URL` · `NEXT_PUBLIC_WS_URL` · `NEXT_PUBLIC_BRIDGE_TOKEN`. העבר ידנית-מאובטח.
- **Agents מתוזמנים:** העתק `~/Documents/Claude/Scheduled/` (8 משימות: rth-monitor, eod-fire-analysis, eod-issues-designs, missed-trades-investigator, pattern-diag-30min…). ⚠️ ה-cron ב-**TZ מקומי** — ודא TZ של המחשב החדש (ישראל) כדי שה-23:xx IL יישארו אחרי-סגירת-RTH (לקח I-9). עדכן נתיבים-אבסולוטיים בתוך כל `SKILL.md`.

## 7 · ⚠️ Grep-and-replace נתיבים (אם שם-משתמש/נתיב שונים)
```bash
grep -rln "/Users/michael" scripts/ docs/ ~/Library/LaunchAgents/com.mems26.bridge.plist ~/Documents/Claude/Scheduled/
```
מוקדי-נתיב-קשיח ידועים: `scripts/start_all.sh` (`cd /Users/michael/Downloads/mems26_web_git` ל-backend+frontend; `V9_EXPORT_DIR`), ה-plist, ו-`SKILL.md` של הסוכנים. **CLAUDE.md מתעד את הנתיבים כ-stability-controls — אל תשנה ל-cloud-URL בטעות.**

## 8 · הרצה + אימות סופי
```bash
./scripts/start_all.sh        # bridge(screen) + backend(uvicorn:8000) + frontend(next:3000). בודק listeners קיימים קודם.
./scripts/check_status.sh
# אמת: http://localhost:3000 (dashboard) · http://localhost:8000/docs (API) · /tmp/bridge.err.log אין "push FAILED to https://"
```
**צ'קליסט-GO למחשב החדש:** check_env OK · DB עולה (day_type מסווג) · גשר דוחף ל-localhost (errors≈0) · S2 armed · קבצי-Sierra טריים ב-`v9_export/` · `pytest` ירוק · UI מציג עסקאות/מחירים.

## 9 · אחרי-המעבר — uncommitted + config-לא-ב-git
- **תיקון-T3: כבר committed** (2026-06-07: `4d79a2d` backend · `0be56ab` frontend · `56a6a9c` טסט). מגיע אוטומטית ב-`git clone`. (ההערה הישנה "uncommitted" התיישנה.)
- **דגלי-SHADOW ב-`.env` (לא ב-git — חובה להעביר ידנית, §6):** מאז `bcdf43e` ה-backend טוען `.env` בקוד (`backend/env_loader.py`) בכל דרך-אתחול, אז במכונה החדשה **חובה שה-`.env` יכיל את כל דגלי-הכיול** (`S2_ATR_RELATIVE`/`S3_RELATIVE`/`S1_CVD_OPENING`/`S1_IB_WIDTH_ATR`/`S1_DAYTYPE_STAGING`/`S2_VSA_VOLUME`/`S3_MUTE`) + `MEMS26_MODE=shadow`, אחרת הדגלים יורדים ל-OFF (תקרית 06/06).
- **לאמת:** האם קיים LaunchAgent **backend** (`com.mems26.backend`) בנוסף ל-bridge? §4 מכסה רק את ה-bridge; §8 מריץ backend דרך `start_all.sh` (screen). אם קיים — recreate גם אותו (כעת יטען `.env` לבד בזכות `bcdf43e`).
