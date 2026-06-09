# CC Prompt — DB Corruption TRUE ROOT FIX (אכיפת נתיב-כתיבה + בידוד) · 2026-06-02

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

## אבחון (Cowork אימת בקוד)
- `safe_writer.py` **תקין**: `_write_lock = threading.Lock()` singleton ברמת-מודול, מסרל נכון כל כתיבה שעוברת דרכו (WAL+busy_timeout, open→write→commit→close).
- אבל ה-corruption **חוזר תחת כתיבה חיה** (5 שגיאות integrity 16:40, אחרי נקי backend-כבוי 16:29; footprint כבר כבוי). VACUUM ניקה את הנזק המובנה — אבל **כתיבה חיה משחיתה מחדש**.
- **שורש:** כותבים שעדיין **עוקפים** את safe_writer עם `sqlite3.connect` גולמי שכותב בלי ה-lock. אומת: `tpo_system.py:88` (+ חשד: `woodies_system.py:141/549/573`, `reversal_handler.py:75`, ועוד). כתיבה אחת מחוץ ל-lock מתנגשת במסורלות → משחיתה. הגישה "לזכור לקרוא safe_execute" שברירית.

## עיקרון התיקון: להפוך עקיפה לבלתי-אפשרית + לבודד את הרועשים. (אין דדליין — נכונות לפני מהירות.)

## Phase A · אבחון מדויק (read-only)
- מצא **כל** `sqlite3.connect` ב-`backend/` שמבצע כתיבה (INSERT/UPDATE/DELETE/CREATE) ו**אינו** read-only (`mode=ro`). רשום רשימה מלאה (קובץ:שורה). זה ה-baseline של הדליפות.
- **דווח לפני תיקון** (B6).

## Phase B · אכיפת writer יחיד (מבני — לא הסתמכות על זיכרון)
- נתב את **כל** הכתיבות דרך `safe_writer` (או thread כותב יחיד עם queue שמחזיק את החיבור היחיד).
- **הפוך כל חיבור אחר ל-read-only:** פתח את כל החיבורים שאינם הכותב דרך `file:{DB}?mode=ro` →
  ניסיון כתיבה דרכם **יזרוק** מיידית (לא יושחת בשקט). ככה עקיפה הופכת בלתי-אפשרית מבנית.
- (חזק יותר, מומלץ) thread כותב יחיד שמחזיק את החיבור ה-RW היחיד; כולם enqueue.

## Phase C · בידוד הטבלאות הרועשות
- העבר `footprint_journal`, `tpo_journal`, `tick_reversal` (מאות אלפי שורות, כתיבה כל tick) ל-**store נפרד** (קובץ SQLite נפרד או ring בזיכרון), FIFO-capped. ה-DB הראשי = רק durable תדירות-נמוכה (trades, day_type, bars_5min, signals) → מעט כתיבות, בטוח, ואם הרועש נשחת — לא נוגע ב-trades.

## Phase D · הוכחה דטרמיניסטית (לא soak ארוך)
המטרה היא **להוכיח שעקיפה בלתי-אפשרית**, לא "לחכות ולראות אם נשחת". לכן:
- **הוכחה 1 (קוד):** `grep` מוכיח **0** חיבורי `sqlite3.connect` שכותבים מחוץ ל-safe_writer (כל השאר `mode=ro`).
- **הוכחה 2 (טסט):** ניסיון כתיבה דרך חיבור ro **זורק** (אם לא זורק → הכשל את הטסט). זה מוכיח שהאכיפה עובדת.
- **הוכחה 3 (קצרה):** שקם DB נקי → `integrity_check` backend-כבוי = ok → burst כתיבה קצר (~2 דק' תחת עומס) → `integrity_check` שוב = ok. **לא צריך 20 דק'** — אם אין נתיב עוקף, אין מה ש"יתפתח" לאורך זמן.

## טסט אנטי-טאוטולוגי
- repro: כתיבה דרך נתיב-עוקף → `integrity` נכשל **לפני**; **אחרי** Phase B — חיבור ro **זורק** על כתיבה (עקיפה בלתי-אפשרית). שורת *"if reverted → RED because בלי ro-enforcement עקיפה אפשרית ומשחיתה"*.

## שער GO
GO = הוכחה 1 (grep=0 עוקפים) **+** הוכחה 2 (ro זורק) **+** הוכחה 3 (integrity נקי backend-כבוי, לפני ואחרי burst קצר). **דטרמיניסטי — בלי soak ארוך.** Cowork יצליב את ה-grep ואת ה-integrity.

## דוח חובה (חלק C) + NOT-DONE + עדכון STATUS_BOARD/ROADMAP/LEDGER.
