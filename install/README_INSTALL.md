# MEMS26 — התקנה על מחשב חדש

חבילת-התקנה שמעמידה את **כל החצי-שלנו** (backend · bridge · Postgres · frontend · שירותי-רקע)
בפקודה אחת, ומשאירה לך צ'קליסט קצר לחצי-של-Sierra (שאף מתקין לא יכול לבצע — תוכנת צד-שלישי מורשית).

> הרקע המלא, השיקולים, ולמה לא-Docker-לפני-LIVE: `docs/plans/PORTABILITY_INSTALLABLE_APP_2026-07-03.md`.

---

## התקנה מהירה (מאק נקי)

```bash
# 1. הבא את הקוד
git clone <GITHUB_REMOTE> ~/mems26/mems26_web_git
cd ~/mems26/mems26_web_git

# 2. הרץ את המתקין (אפשר קודם --dry-run כדי לראות מה הוא יעשה)
install/install_mems26.sh --dry-run
install/install_mems26.sh

# 3. עשה את החצי-של-Sierra
open install/SIERRA_SETUP_CHECKLIST.md
```

המתקין: מתקין תלויות חסרות (Homebrew) · יוצר venv + `pip install` · יוצר DB `mems26` + סכימה + מיגרציות ·
בונה frontend · כותב `.env` מ-`env.template` (לא דורס קיים) · מתקין ומרים את ה-LaunchAgents · מאמת health.

**הפעלה-אוטומטית + בדיקה-עצמית:** כל ה-LaunchAgents עם `RunAtLoad` — **עולים לבד בכל הדלקה/התחברות**. נוסף שירות `com.mems26.startup_check` שרץ בהתחברות, מחכה שהכל יתחבר, בודק את כל השרשרת (בקאנד↔Postgres↔ברידג'↔feed-סיארה↔frontend), כותב דוח ל-`/tmp/mems26_startup_report.txt` ו**מקפיץ התראת-מק** ✅/⚠️/❌. אפשר להריץ ידנית בכל רגע: `scripts/mems26_startup_check.sh`.

**דרישות שאינן אוטומטיות:** Postgres.app (אפליקציית-GUI — התקן ידנית מ-postgresapp.com), ורישיון+התקנת Sierra.

---

## הקבצים בחבילה

| קובץ | תפקיד |
|---|---|
| `install_mems26.sh` | המתקין הראשי (idempotent · `--dry-run` · לא-דורס-`.env`) |
| `env.template` | תבנית `.env` — מפתחות-מכונה + baseline-דגלים מתוארך (מקור-אמת חי: `docs/FLAG_INDEX.md`) |
| `launchagents/*.plist.tmpl` | תבניות LaunchAgent (backend/bridge/promoter) עם `__REPO__/__PYTHON__/__EXPORT_DIR__/__BRIDGE_TOKEN__` |
| `SIERRA_SETUP_CHECKLIST.md` | החצי-הידני: DLL · Remote-Build · Inputs · חוזה · אימות-feed |
| `mems26_update.sh` | עדכון מ-GitHub (snapshot → ff-pull → deps → restart → verify · מסרב אם יש עסקה פתוחה) |
| `scripts/mems26_startup_check.sh` | בדיקה-עצמית בהדלקה (דוח + התראת-מק) — רץ אוטומטית ע"י `com.mems26.startup_check` |
| `uninstall_mems26.sh` | עוצר ומסיר LaunchAgents (`--purge-db`/`--purge-repo` אופציונלי) |

---

## עדכון מהמחשב-הזה (dev) אל מכונת-המסחר

נקודת-הסנכרון = **GitHub**. אני (הסוכן כאן) דוחף לענף; מכונת-המסחר מושכת. שתי רמות:

1. **ידני-מגודר (מומלץ לפני-LIVE):** על מכונת-המסחר —
   ```bash
   install/mems26_update.sh --branch release
   ```
   עושה snapshot, מושך fast-forward בלבד, מרענן deps אם השתנו, restart דרך launchd, ו-verify.
   **מסרב לרסטארט אם יש עסקה/סלוט פתוח.**

2. **אוטומטי (אחרי-LIVE):** LaunchAgent שמריץ את הסקריפט על ענף `release` כל X דקות =
   "אפליקציה שמתעדכנת לבד". מומלץ להשאיר כבוי עד שהמערכת יציבה ב-LIVE, ורק על ענף-`release` נפרד
   (לא `main`), כדי ששום קומיט-עבודה לא ידלף אוטומטית למכונת-כסף.

> אני **לא** ניגש ישירות למכונה-האחרת — GitHub הוא המתווך (audit-trail + rollback). כשנרצה לעדכן:
> אני דוחף ל-`release` כאן, ואתה (או הסוכן-האוטומטי) מריץ `mems26_update.sh` שם.

---

## אזהרות (pre-LIVE)

- **localhost-only קדוש:** הברידג' דוחף רק ל-`localhost:8000` — גם על המכונה החדשה. המתקין לא נוגע בזה.
- **רישיון Sierra פר-משתמש.** מכונה נוספת שלך — תקין. הפצה לסוחרים אחרים = מסלול-מוצר כבד (רישוי/סודות/תמיכה) — דיון נפרד.
- **החלטות-סטנדינג נשארות כבויות** בכל התקנה (chop gates · cooldown · COT/AMT) — CLAUDE.md §Standing Decisions.
- כל שינוי מחוץ-ל-git = `scripts/mems26_snapshot.sh` לפני, `mems26_verify.sh` אחרי.

---

## מה עוד כדאי (שיפורי-ניוד, לא-חוסמים — פרק 4 במסמך-הניוד)

הקוד רץ נכון על מכונה אחרת גם היום (ה-`.env` נושא את הנתיבים המוחלטים). לניקוי: להפוך את ברירות-המחדל
הקשיחות (`/Users/michael/...`) ל-`~`-יחסי, ולהקשיח את `db/session.py` שיכשל-רועש אם `DATABASE_URL` חסר
(במקום ליפול בשקט ל-SQLite). זה שיפור, לא תנאי — נכלל ברשימת-המשימות ל-CC.
