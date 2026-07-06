# MEMS26 — מדריך לסוכן על המכונה השנייה (Claude Code / Cowork)

**מי אתה:** סוכן שרץ על **מכונת-מסחר שנייה** של Michael (מאק, סיארה כבר מותקנת). Michael הריץ את
`RUN_ME.command` מתוך חבילת-ההתקנה ונתקע. **התפקיד שלך: לסיים את ההתקנה, לאבחן מה נתקע, לאמת
שהכל מחובר, ולהפעיל — לא לפתח.** שום שינוי בלוגיקת-מסחר, שום דגל-סיכון בלי אישור מפורש של Michael.

> **הכלל הראשון — הרץ אבחון לפני הכל:**
> ```bash
> cd <repo>   # בד"כ ~/mems26/mems26_web_git
> bash scripts/mems26_doctor.sh
> ```
> הוא קורא-בלבד, ומסתיים ב-**`NEXT STEP →`** אחד — הפעולה הבאה המדויקת. עבוד לפיה, הרץ שוב, חזור.

---

## 1 · מה זו המערכת (בקצרה)
סטאק-מסחר אוטונומי מקומי: **Sierra Chart** (DLL כותב JSON) → **bridge** → **backend FastAPI** (:8000)
→ **Postgres מקומי** (`postgresql://localhost/mems26`) → gateway/מערכות → DEMO/LIVE. **frontend** (:3000)
הוא דשבורד בלבד. הכל **localhost** — הברידג' דוחף רק ל-`localhost:8000`, לעולם לא ענן.

ארבעה שירותי-רקע (LaunchAgents, עולים לבד בהתחברות): `com.mems26.backend` · `.bridge` ·
`.export_promoter` · `.startup_check` (בדיקה-עצמית שמדפיסה דוח + התראה בכל הפעלה).

## 2 · לסיים התקנה — לפי מה שהדוקטור מצא
הדוקטור בודק בסדר-תלות. טפל ב-`NEXT STEP` הראשון, ואז הרץ שוב:

| מה הדוקטור אומר | מה לעשות |
|---|---|
| `install git/node/python3` | `brew install git node python@3.11` (אם אין brew: התקן מ-https://brew.sh) |
| `Postgres not installed` | התקן **Postgres.app** (https://postgresapp.com), פתח אותו פעם אחת (מתחיל שרת), ואז המשך |
| `DB 'mems26' unreachable` | `createdb mems26` ואז `DATABASE_URL=postgresql://localhost/mems26 bash scripts/db_init.sh` |
| `no venv` / `pip deps missing` | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| `no .env` | `cp install/env.template .env` וערוך נתיבים (או הרץ שוב `install/install_mems26.sh`) |
| `DATABASE_URL not set to postgresql` | ערוך `.env`: `DATABASE_URL=postgresql://localhost/mems26` (מונע נפילה שקטה ל-SQLite) |
| `com.mems26.* not loaded` | `launchctl load -w ~/Library/LaunchAgents/com.mems26.<svc>.plist` (או הרץ שוב את המתקין) |
| `Backend :8000 not listening` | ראה §4 (לוגים) → תקן → `launchctl kickstart -k gui/$(id -u)/com.mems26.backend` |

**הדרך הבטוחה תמיד:** פשוט להריץ שוב את המתקין — הוא idempotent ולא דורס `.env`:
```bash
bash install/install_mems26.sh --repo "$PWD"
```

## 3 · לאמת שהכל מחובר
```bash
bash scripts/mems26_startup_check.sh   # דוח מלא + התראת-מק (✅/⚠️/❌)
bash scripts/mems26_verify.sh          # שירותים · DLL↔repo · אינדקס · feed · DB lag
curl -s localhost:8000/api/v9/health   # {"status":"ok"}
```
**feed טרי נדרש רק בתוך RTH** (08:30–15:00 CT). מחוץ ל-RTH feed ישן = תקין.

## 4 · לוגים ואבחון-שירותים
```bash
tail -50 /tmp/backend.err.log            # שגיאות-בקאנד (הכי חשוב)
tail -50 /tmp/bridge.err.log             # דחיפות הברידג' (צריך push ל-localhost:8000)
cat /tmp/mems26_startup_report.txt       # דוח הבדיקה-האחרונה
grep env_loader /tmp/backend.err.log | tail -1   # אילו דגלים נטענו (canonical, לא ps)
```
**ריסטארט בקאנד = תמיד דרך launchd, לא nohup:**
`launchctl kickstart -k gui/$(id -u)/com.mems26.backend`

## 5 · החצי של סיארה (הידני — סיארה כבר מותקנת אצלך)
אם `mems26_doctor.sh §8` אומר שאין export files:
1. `cd <repo> && scripts/build_monolithic_cpp.sh --deploy`
2. ב-Sierra: **Analysis → Build Custom Studies DLL → Remote Build** (0 שגיאות)
3. הצמד `MES_AI_DataExport` לצ'ארט ה-MES 5-דק'
4. **Input-4** (תיקיית-ייצוא) = הנתיב מ-`.env` (`V9_EXPORT_DIR`, בד"כ `~/SierraChart_Data/v9_export/`)
5. הגדר **חוזה** נוכחי · **Input-21 EnableOrderPlacement=0** עד שמוכנים
6. ודא `*.json` מתעדכנים ≤2s ב-RTH. רשימה מלאה: `install/SIERRA_SETUP_CHECKLIST.md`

## 6 · כללי-בטיחות (מחייבים)
- **localhost בלבד.** אם ראית `push FAILED to https://...` — עצור, בדוק `.env`/קונפיג.
- **החלטות-סטנדינג נשארות כבויות:** chop gates · cooldown · COT/AMT (`CLAUDE.md §Standing Decisions`). אל תדליק.
- **אל תדליק דגל trading-risk** (LIVE, halt, OPENING_WINDOW_FIRE_V1, EOD_RISK_WINDOW_V1...) בלי אישור מפורש של Michael.
- לפני שינוי מחוץ-ל-git (`.env`/DLL/LaunchAgent): `scripts/mems26_snapshot.sh "why"`. גלגול-לאחור: `scripts/mems26_restore.sh`.
- **אל תדחוף ל-git** מהמכונה הזו — זו מכונת-מסחר, לא פיתוח. עדכונים מגיעים מהמכונה של Michael.
- ראיה-ולא-טענה (Rule 5): כל "תוקן" → הדבק פקודה+פלט.

## 7 · איך מגיעים עדכונים (מהמכונה של Michael)
Michael דוחף ל-GitHub מהמכונה-הראשית. כאן מושכים ומרעננים בבטחה:
```bash
bash install/mems26_update.sh --branch release   # snapshot → ff-pull → deps → restart → verify
```
הוא **מסרב לרסטרט אם יש עסקה פתוחה** — קודם flatten, ואז הרץ שוב.

## 8 · הפעלה יומית (routine)
1. הדלק/התחבר → 4 השירותים עולים לבד → התראת `com.mems26.startup_check` תופיע (✅/⚠️/❌).
2. אם ⚠️/❌ → `bash scripts/mems26_doctor.sh` → פעל לפי ה-NEXT STEP.
3. לפני מסחר: `docs/runbooks/PRE_TRADE_PROTOCOL.md`.
4. דשבורד: http://localhost:3000.

**אם נתקעת ולא ברור:** הרץ `bash scripts/mems26_doctor.sh` והדבק את כל הפלט ל-Michael (או לצ'אט-הפיתוח במכונה הראשית) — זו התמונה המלאה במבט אחד.
