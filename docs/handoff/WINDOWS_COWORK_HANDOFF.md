# פרומפט מלא ל-Claude במחשב Windows — הקמת MEMS26
*(העתק את כל הבלוק למטה → Google Doc → פתח במחשב Windows → הדבק ל-Claude שם.)*

---

שלום. אני מיכאל, **לא מתכנת**. עזור לי **שלב-אחר-שלב, לאט**, להקים על מחשב ה-Windows הזה את מערכת-המסחר שלי **MEMS26** (מערכת אוטונומית לחוזים עתידיים שכבר עובדת על המאק שלי). כללי-עבודה: הסבר כל צעד בפשטות, בצע **צעד אחד בכל פעם**, **חכה שאני אאשר**, ואז המשך. אם משהו נכשל — **עצור ותגיד לי** מה קרה, אל תמשיך לבד.

## רקע
- המאק = מחשב-הפיתוח (כבר מוקם). ה-Windows הזה = מכונת-המסחר עם **Sierra Chart** (רק זה מותקן כרגע).
- כל הקוד ב-GitHub: `https://github.com/michaelbarg/mems26-web` , ענף `stabilize/mems26-local-truth-2026-05-16`.
- בתוך הקוד יש מדריך-Windows מלא: **`docs/runbooks/WINDOWS_SETUP.md`** — אחרי ה-clone, קרא אותו ועבוד לפיו.
- חוזה-המסחר הוא **MESU26 (ספטמבר)**, לא יוני.
- בתיקיית-Google-Drive שלי בשם **MEMS26_to_Windows** הנחתי את הקבצים שצריך: קובץ ה-`.env`, ה-chartbook של Sierra (`AAMichael_lap25.Cht`), וקבצי-הסטאדי. אוריד אותם ואתן לך נתיב — אל תניח שהם כבר במחשב.

## הצעדים (לפי הסדר — חכה לאישור שלי בין שלב לשלב)

**1. התקנת כלים.** הכי קל: בתיקיית-Drive יש `setup_all.ps1` (וגם בקוד תחת `scripts\windows\`). פתח PowerShell **כאדמין**, הרץ `Set-ExecutionPolicy -Scope Process Bypass -Force`, ואז הרץ את `setup_all.ps1` — הוא מתקין **Git + Python 3.11 + PostgreSQL 16 + Node.js LTS**. (אם תעדיף ידני: `winget install --id Git.Git -e`, וכן הלאה לכל אחד.) הערה: מתקין PostgreSQL יבקש לבחור סיסמה — לא נורא אם נשכח אותה, נעקוף בצעד 4.

**2. שכפול הקוד.**
```
git clone https://github.com/michaelbarg/mems26-web.git C:\mems26_web_git
cd C:\mems26_web_git
git checkout stabilize/mems26-local-truth-2026-05-16
```
(אם git מבקש התחברות ל-GitHub — הדרך אותי ליצור Personal Access Token.)

**3. קרא את המדריך.** פתח `docs/runbooks/WINDOWS_SETUP.md` ועבוד לפיו מכאן והלאה — הוא מכסה את כל השאר.

**4. PostgreSQL — בלי סיסמה (כמו במאק).** במאק אין סיסמה (trust על localhost); הגדר אותו דבר כאן כדי שלא ניתקע על סיסמה שאני לא זוכר:
   1. פתח `C:\Program Files\PostgreSQL\16\data\pg_hba.conf`
   2. בשורות של `127.0.0.1/32` ושל `::1/128` — שנה את שיטת-האימות מ-`scram-sha-256` (או `md5`) ל-`trust`. שמור.
   3. ב-PowerShell כאדמין: `Restart-Service postgresql-x64-16`
   4. צור את ה-DB: `& "C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres mems26`
   (הנתונים ההיסטוריים לא חובה — מתחילים נקי. trust על localhost-בלבד תקין למכונה מקומית.)

**5. תלויות.** `pip install -r requirements.txt` , ואז `cd frontend\v9 ; npm install ; cd ..\..`

**6. קובץ `.env`.** בתיקיית-Drive יש קובץ בשם `env_for_windows_NEW (use this one, rename to .env).txt`. הורד אותו → שים ב-`C:\mems26_web_git\.env` (הסר את `.txt`). ודא שבתוכו:
   - `V9_EXPORT_DIR=C:\SierraChart\Data\v9_export` — תיקיית-הייצוא של Sierra בווינדוס (שנה לנתיב האמיתי).
   - `V9_CUMDELTA_EXPORT_PATH=C:\SierraChart\Data\v9_export\cumulative_delta.json` — **חשוב**, אחרת ה-Cumulative Volume (CVD) יראה אפסים.
   - כל שאר הדגלים — השאר **בדיוק כמו שהם**.

**7. Sierra — chartbook + סטאדיז (זה החלק שחייב לעבוד נכון).**
   1. הורד מתיקיית-Drive את ה-chartbook `AAMichael_lap25.Cht` → שים ב-`C:\SierraChart\Data\`.
   2. **הסטאדי המותאם שלנו חייב להיות מקומפל ב-Windows**, אחרת יופיע כ-"not found" ולא ייצא שום קובץ JSON. הקוד שלו בקוד שהורדת (`sc_study/`, למשל `MES_AI_DataExport.cpp`). ב-Sierra: העתק ל-`ACS_Source\` → **Analysis ▸ Build ▸ Remote Build** → טען מחדש את הסטאדי. (מדריך: `docs/runbooks/SIERRA_DLL_OPS.md`.) הסטאדיז המובנים של Sierra (Woodies CCI, Cumulative Delta, TPO, Volume Profile) נטענים לבד — לא צריך לקמפל אותם.
   3. פתח את ה-chartbook → העמד **כל צ'ארט על MESU26** (ספטמבר), לא יוני.
   4. בסטאדי-הייצוא קבע **Input-4** = אותה תיקייה כמו `V9_EXPORT_DIR`.
   5. ודא שקבצים מתעדכנים שם: `mes_ai_data.json`, `woodies_5min.json`, `cumulative_delta.json` ...

**8. הרצה.** צור והרץ `start_backend.bat` + `start_bridge.bat` (תבניות במדריך §E) + frontend (`cd frontend\v9 ; npx next dev`). אמת: `curl http://localhost:8000/health` מחזיר ok, לוג-ה-bridge מראה pushes, והדאשבורד נטען ב-`http://localhost:3000`.

## חוקים חשובים (אל תשבור)
- **כל דגלי-הפיצ'רים נשארים כמו שב-`.env`** — אל תדליק/תכבה כלום בלי שאני אבקש.
- **ה-bridge דוחף רק ל-`http://localhost:8000`** — לעולם לא לכתובת ענן.
- **PostgreSQL מקומי בלבד** (`localhost`) — לא ענן.
- אל תכתוב סודות (tokens) לקוד; ה-`.env` נשאר מקומי, לא נדחף ל-git.
- אם אתה נתקע במשהו שדורש ידע על המערכת שאין במדריך — תגיד לי לשאול את Claude שעל המאק.

**בוא נתחיל מצעד 1.**

---

*(סוף ההודעה.)*
