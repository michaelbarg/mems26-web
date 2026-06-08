# CC — מעבר-מחשב: דחיפה (מחשב ישן) + הקמה מלאה (מחשב חדש) · 2026-06-08

Michael אישר push. הרקע: הענף המקומי **222 commits לפני origin** — כל עבודת
היום (T3, דגלים, SPEC) + הרבה מלפני. בלי push, clone יביא גרסה ישנה.
Cowork לא יכול לדחוף (sandbox חסום-רשת). שני חלקים — A על המחשב **הישן**, B על **החדש**.

═══════════════════════════════════════════════════
## חלק A — על המחשב הישן (דחיפה) · הדבק פלט גולמי
═══════════════════════════════════════════════════
```bash
cd /Users/michael/Downloads/mems26_web_git
git status -sb | head -1            # אישור: ahead 222
git log --oneline -3                # אישור: 75bc08d בראש
git push origin stabilize/mems26-local-truth-2026-05-16
git status -sb | head -1            # אחרי: צריך "ahead 0" (או up-to-date)
```
אם ה-push נכשל על אימות — ודא ש-`~/.ssh/config` מכיל את ה-host `github-mems26`
ושה-key טעון (`ssh-add -l`). אל תשנה את ה-remote ל-URL אחר.

**גיבוי-`.env` מאובטח (לא ב-git!):** העתק למקום-מאובטח להעברה ידנית —
`/Users/michael/Downloads/mems26_web_git/.env` + `frontend/v9/.env.local`.
ה-`.env` חייב להכיל (אומת היום): `DATABASE_URL=postgresql://localhost/mems26`,
`MEMS26_MODE=shadow`, ו-7 הדגלים `S2_ATR_RELATIVE/S3_RELATIVE/S1_CVD_OPENING/`
`S1_IB_WIDTH_ATR/S1_DAYTYPE_STAGING/S2_VSA_VOLUME/S3_MUTE`.

═══════════════════════════════════════════════════
## חלק B — על המחשב החדש (הקמה) · לפי MIGRATION_TO_NEW_MACHINE.md
═══════════════════════════════════════════════════
**B0 · דרישות-קדם:** macOS · Python 3.9.7 · Node 23.x/npm 10.x · Homebrew ·
`brew install postgresql@16 screen git node python@3.9` · `brew services start postgresql@16` · CrossOver.

**B1 · Repo:**
```bash
git clone github-mems26:michaelbarg/mems26-web.git /Users/<user>/Downloads/mems26_web_git
cd /Users/<user>/Downloads/mems26_web_git
git checkout stabilize/mems26-local-truth-2026-05-16
git log --oneline -1     # חייב להראות 75bc08d (אם לא — ה-push בחלק A לא הושלם)
pip3 install -r requirements.txt --break-system-packages
cd frontend/v9 && npm install && cd ../..
```
⚠️ אל תעתיק `node_modules`/`__pycache__`/`*.pyc` מהמחשב הישן — התקן מחדש.

**B2 · Secrets (ידני — לא ב-git):** הנח את `.env` (מחלק A) ב-repo-root + את
`frontend/v9/.env.local`. `config/*.yaml` כבר מגיע ב-clone ✅.

**B3 · אם שם-המשתמש/נתיב שונה:** grep-and-replace (רונבוק §7):
```bash
grep -rln "/Users/michael" scripts/ ~/Library/LaunchAgents/com.mems26.bridge.plist ~/Documents/Claude/Scheduled/
```
עדכן `V9_EXPORT_DIR` ב-`.env` לנתיב המשתמש החדש. אל תשנה `CLOUD_URL` (localhost בלבד).

**B4 · DB:** `createdb mems26` → `./scripts/db_init.sh` (נקי, מומלץ) או backup→restore. localhost בלבד.

**B5 · Sierra+DLL (ידני):** התקן Sierra ב-CrossOver · שחזר chart 5 + studies ·
צור `~/SierraChart_Data/v9_export/` · **Study Input 4 = הספרייה הזו** · בנה DLL:
`./scripts/build_monolithic_cpp.sh --deploy` → Remote Build → reload.

**B6 · LaunchAgent + Agents:** recreate `com.mems26.bridge.plist` (KeepAlive מותנה,
`CLOUD_URL=localhost`, `V9_DISABLE_WATCHDOG=1` — אל תשנה!). העתק
`~/Documents/Claude/Scheduled/` (8 סוכנים) + ודא TZ-מקומי (לקח I-9).

**B7 · הפעלה + אימות (כתוב ל-`docs/reports/NEW_MACHINE_VERIFY.txt`):**
```bash
./scripts/check_env.sh                # חייב OK
bash scripts/start_all.sh; sleep 10
ps eww $(pgrep -f "uvicorn backend.main"|head -1) | tr ' ' '\n' | grep -E '^DATABASE_URL=|^S[123]_|^S2_'  # PG + 7 דגלים
curl -s localhost:8000/health; echo
tail -20 /tmp/backend.log | grep -iE "sqlite|malformed" || echo "clean"
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000
```

**צ'קליסט-GO חדש:** check_env OK · DATABASE_URL=PG בתהליך · 7 דגלים ON · 0 שגיאות
sqlite · גשר דוחף ל-localhost (errors≈0) · קבצי-Sierra טריים ב-v9_export · `pytest` ירוק
· UI :3000 מציג מחירים. דווח PASS/FAIL לכל אחד.
