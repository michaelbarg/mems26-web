# CC — הקמת MEMS26 על המחשב החדש (self-contained)

הרקע: ה-repo נדחף ל-GitHub (origin מעודכן, HEAD=`75bc08d`, ענף
`stabilize/mems26-local-truth-2026-05-16`). זו סביבת-הפיתוח החדשה. בצע לפי הסדר,
הדבק פלט גולמי לכל שלב, ובסוף כתוב צ'קליסט-GO ל-`docs/reports/NEW_MACHINE_VERIFY.txt`.
**כלל-זהב:** localhost בלבד — אל תשנה שום `CLOUD_URL` ל-URL ענן.

## 0 · דרישות-קדם (macOS)
```bash
# Homebrew מותקן; ואז:
brew install postgresql@16 screen git node python@3.9
brew services start postgresql@16
# Python 3.9.7 · Node 23.x/npm 10.x · CrossOver (ל-Sierra) — ידני
```

## 1 · Clone + תלויות
```bash
git clone github-mems26:michaelbarg/mems26-web.git /Users/<user>/Downloads/mems26_web_git
cd /Users/<user>/Downloads/mems26_web_git
git checkout stabilize/mems26-local-truth-2026-05-16
git log --oneline -1          # ❗ חייב להראות 75bc08d — אם לא, ה-push לא הושלם, עצור
pip3 install -r requirements.txt --break-system-packages
cd frontend/v9 && npm install && cd ../..
```
⚠️ אל תעתיק `node_modules`/`__pycache__`/`*.pyc` מהמחשב הישן — מותקנים מחדש כאן.

## 2 · Secrets ידניים (לא ב-git — להעביר מהמחשב הישן באופן מאובטח)
- הנח `.env` ב-repo-root. **חובה שיכיל (אומת 2026-06-08):**
  `DATABASE_URL=postgresql://localhost/mems26` · `MEMS26_MODE=shadow` · `CLOUD_URL=http://localhost:8000` ·
  ו-7 הדגלים: `S2_ATR_RELATIVE` `S3_RELATIVE` `S1_CVD_OPENING` `S1_IB_WIDTH_ATR` `S1_DAYTYPE_STAGING` `S2_VSA_VOLUME` `S3_MUTE` (+ `BRIDGE_TOKEN`, `UPSTASH_*` אם בשימוש).
- הנח `frontend/v9/.env.local` (כתובות `NEXT_PUBLIC_API_URL`/`WS_URL`/`BRIDGE_TOKEN`).
- `config/*.yaml` (auth_matrix/targets/stop_params/s2_firing) — **כבר הגיע ב-clone**, לא להעתיק.

## 3 · אם שם-המשתמש/נתיב שונה מ-`/Users/michael/...`
```bash
grep -rln "/Users/michael" scripts/ ~/Library/LaunchAgents/com.mems26.bridge.plist ~/Documents/Claude/Scheduled/ 2>/dev/null
```
עדכן את `V9_EXPORT_DIR` ב-`.env` ואת הנתיבים ב-`start_all.sh`/plist/SKILL.md. אל תיגע ב-`CLOUD_URL`.

## 4 · Database (Postgres מקומי בלבד)
```bash
createdb mems26
export DATABASE_URL="postgresql://localhost/mems26"
./scripts/db_init.sh          # נקי (מומלץ) — או backup→restore מהישן
```

## 5 · Sierra Chart + DLL (ידני, החלק הארוך)
1. CrossOver + Sierra Chart + חשבון Sierra; שחזר **chart 5** (MES) + studies.
2. צור `~/SierraChart_Data/v9_export/` · הגדר **Study Input 4 = הספרייה הזו** (נשמר per-chart).
3. `./scripts/build_monolithic_cpp.sh --deploy` → Analysis → Build Advanced Custom Study DLL (Remote Build) → reload study.
4. `./scripts/verify_sierra_dll_deploy.sh` + ודא קבצי-יצוא טריים ב-`v9_export/`.

## 6 · LaunchAgent + סוכנים מתוזמנים
- recreate `~/Library/LaunchAgents/com.mems26.bridge.plist` עם הכללים (אל תשנה!):
  `CLOUD_URL=http://localhost:8000` · `export V9_DISABLE_WATCHDOG=1` · KeepAlive מותנה
  (`<dict><key>SuccessfulExit</key><false/></dict>`). עדכן בו נתיב-repo + `V9_EXPORT_DIR`.
  `launchctl load ~/Library/LaunchAgents/com.mems26.bridge.plist`.
- העתק `~/Documents/Claude/Scheduled/` (8 סוכנים) · ודא TZ של המחשב = ישראל (לקח I-9) · עדכן נתיבים ב-SKILL.md.

## 7 · הפעלה + אימות → כתוב ל-docs/reports/NEW_MACHINE_VERIFY.txt
```bash
./scripts/check_env.sh        # חייב OK לפני המשך
bash scripts/start_all.sh; sleep 10
{
echo "== health =="; curl -s localhost:8000/health; echo
echo "== DATABASE_URL + 7 דגלים בתהליך הרץ =="
ps eww $(pgrep -f "uvicorn backend.main"|head -1) | tr ' ' '\n' | grep -E '^DATABASE_URL=|^S1_|^S2_|^S3_' | sort
echo "== sqlite errors? =="; tail -30 /tmp/backend.log | grep -iE "sqlite|malformed" || echo clean
echo "== bridge (אין push FAILED to https) =="; tail -15 /tmp/bridge.err.log 2>/dev/null
echo "== frontend =="; curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000
} > docs/reports/NEW_MACHINE_VERIFY.txt 2>&1
cat docs/reports/NEW_MACHINE_VERIFY.txt
```

## צ'קליסט-GO (דווח PASS/FAIL לכל אחד)
1. `git log` HEAD = 75bc08d · 2. check_env OK · 3. DATABASE_URL=postgresql://localhost/mems26 בתהליך ·
4. 7 דגלים ON · 5. 0 שגיאות sqlite · 6. גשר דוחף ל-localhost (אין https) · 7. קבצי-Sierra טריים ב-v9_export ·
8. `pytest` ירוק · 9. UI :3000 נטען.
חסר 3/4/5 → עצור ודווח (אלה התקלות שתיקנו ב-06-08).
