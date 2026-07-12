# התקנת MEMS26 על מק שני — ראנבוק ל-Claude Code (2026-07-11)

**מטרה:** עותק מלא ומתעדכן של המערכת. ברירת-מחדל: מכונת פיתוח/גיבוי (בלי סיירה).
מסחר נשאר על המכונה הראשית אלא אם מייקל אומר אחרת.

## 0. עקרונות (לפני הכל)
- קרא את `CLAUDE.md` בשורש — כל כללי-הזהב (דגלים פסוקים, ‏bridge-localhost-only,
  ‏snapshot לפני out-of-git) חלים גם כאן.
- אל תדליק שום דגל פסוק-OFF; אל תשנה `.env` בלי snapshot; אל תפנה לשום cloud.
- המכונה הזו לא סוחרת עד פסיקת מייקל — אל תפעיל bridge מול סיירה ואל תפרוס DLL.

## 1. תלויות
```bash
xcode-select --install                       # git וכלי-בסיס
# Postgres.app מ-https://postgresapp.com (גרסה 18) — להפעיל פעם אחת
# Node/npm: https://nodejs.org LTS (או brew install node אם יש brew)
python3 --version                            # 3.9+ נדרש
```

## 2. שכפול הריפו
הרימוט פרטי: `https://github.com/michaelbarg/mems26-web.git`
```bash
gh auth login        # או SSH key שמייקל יאשר ב-GitHub
git clone https://github.com/michaelbarg/mems26-web.git ~/Downloads/mems26_web_git
cd ~/Downloads/mems26_web_git
git checkout stabilize/mems26-local-truth-2026-05-16   # הענף החי
```

## 3. קובץ הסודות `.env` — לא בגיט!
מייקל מעביר אותו ידנית (AirDrop/Drive) מהמכונה הראשית:
`~/Downloads/mems26_web_git/.env` (או מה-snapshot האחרון ב-`~/mems26_snapshots/`).
להניח בשורש הריפו. בלעדיו שום דבר לא עולה (BRIDGE_TOKEN, 47 דגלים פסוקים).

## 4. בסיס-נתונים
```bash
/Applications/Postgres.app/Contents/Versions/latest/bin/createdb mems26
```
מתחילים ריק (העבר הוא disposable per CLAUDE.md §DB). אם מייקל רוצה היסטוריה:
במכונה הראשית `pg_dump mems26 > mems26.sql` → כאן `psql mems26 < mems26.sql`.

## 5. התקנה
```bash
bash scripts/install_mems26.sh      # אידמפוטנטי: תלויות-פייתון, LaunchAgents מתובנתים
cd frontend/v9 && npm install && cd ../..
```
**הערה:** ה-LaunchAgent של הפרונט נכשל על TCC/launchd במכונה הראשית (npm/PATH +
הרשאות Downloads) — אם קורה גם כאן, השתמש ב-screen כמו `scripts/start_all.sh`.

## 6. אימות (חובה, Rule 5 — צטט פלטים)
```bash
python3 scripts/flag_guard.py        # PASS — all 47 ruled flags match
python3 scripts/fire_drill.py        # 🟢 (יתלונן על feed — אין סיירה כאן; זה צפוי)
bash scripts/mems26_verify.sh        # יסמן חוסר-DLL/feed — מקובל במכונת-פיתוח
curl -s localhost:8000/api/v9/health # אחרי הרמת backend
```
מה שקשור לסיירה (feed, DLL, exports, bridge) **צפוי אדום** במכונה בלי סיירה — לא באג.

## 7. שגרת עדכון
```bash
bash scripts/mems26_update.sh        # או: git pull origin stabilize/mems26-local-truth-2026-05-16
```
אחרי כל pull: `python3 scripts/flag_guard.py` + אם השתנו דגלים — לקרוא את ה-diff
של `config/RULED_FLAGS.yaml` לפני שממשיכים.

## 8. חלוקת-עבודה מול המכונה הראשית
- הראשית = מסחר + אמת-סיירה. השנייה = פיתוח/טסטים/בקטסטים כבדים.
- עבודה כאן נדחפת ל-origin; המכונה הראשית מושכת. **אין עריכה מקבילה של אותו קובץ
  בשתי המכונות** — לתאם דרך מייקל/Cowork, ולהריץ איחוד-טסטים אחרי merge.
- דוחות: `docs/reports/` עם suffix `_MAC2` כדי שלא להתנגש.
