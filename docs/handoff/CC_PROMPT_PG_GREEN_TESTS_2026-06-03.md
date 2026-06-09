# CC PROMPT — Green 9 failing tests + verify migration didn't break anything real (gate ל-SHADOW) · 2026-06-03

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** המשך ל-`POSTGRES_MIGRATION_REPORT_2026-06-03.md`. **הכרעת Michael:** לירוק את הטסטים ולוודא נקי לפני שמסתמכים על SHADOW.

## למה זה הצעד הבא
ההגירה GO (Cowork אימת constraints + soak). אבל חבילת-הטסטים **אדומה** (9): אחרי הגירת שכבת-DB,
טסט אדום הוא בדיוק המקום שבו רגרסיה אמיתית מתחבאת. אסור לסמוך על נתוני SHADOW עם CI אדום.

## הטסטים האדומים (מהדוח)
- `test_historical_replay.py` — 3 failures
- `test_day_type_api_v9.py` — 6 errors
**שורש שדווח:** ה-fixtures יוצרים DB-SQLite משלהם ב-`sqlite3.connect`, בעוד הקוד שהומר משתמש ב-engine הגלובלי (`db/read.py`, `safe_writer` engine-based) → קריאה/כתיבה הולכת ל-DB אחר מזה שה-fixture זרע.

## פעולות
1. **אבחן כל כשל לפני תיקון (Rule: diagnose-first):** לכל אחד מ-9 — האם זה **באמת fixture-only** (הטסט מצביע ל-sqlite משלו בזמן שהקוד פונה ל-engine), או שהוא חושף **רגרסיה אמיתית** מההגירה (קריאה/כתיבה שנשברה ב-PG, conflict-col שגוי, טיפוס). הדבק את ה-traceback הגולמי + הסיווג פר-טסט.
2. **תקן את ה-fixtures לעקביות עם הקוד שהומר:** ה-fixture חייב לזרוע דרך אותה מכונה שהקוד קורא ממנה — `init_db()` + `SessionLocal`/engine על DB-טסט ייעודי (sqlite זמני קביל ל-unit, כי safe_writer שומר fallback ל-sqlite; או schema-PG חד-פעמי). **לא** `sqlite3.connect` ידני מקביל ל-engine.
3. **❌ אל תחליש קוד-פרודקשן כדי לירוק טסט.** אם טסט נכשל כי הקוד שגוי ב-PG — תקן את הקוד, לא את הטסט. אם הטסט עצמו מיושן (בודק התנהגות SQLite שכבר לא קיימת) — עדכן/הסר עם נימוק מפורש.
4. **green מלא:** הרץ את כל החבילה. הדבק `pytest` raw summary (`N passed, 0 failed, 0 errors`).
5. **וידוא "לא נשבר כלום":** הרץ smoke קצר על נתיב-קריאה ונתיב-כתיבה מומרים מול PG (לדוגמה `read_all('SELECT count(*) FROM v9_bars_5min')` + `safe_execute` upsert) והדבק תוצאה — לוודא שהירוק לא בא ממעקף.

## Acceptance (✓/✗ + raw)
- [ ] טבלת 9-הטסטים: traceback + סיווג (fixture-only / רגרסיה-אמיתית-שתוקנה). 
- [ ] חבילה מלאה ירוקה — `pytest` raw (`0 failed, 0 errors`).
- [ ] 0 שינויי קוד-פרודקשן שנועדו רק לירוק טסט (או נימוק מפורש לכל חריג).
- [ ] smoke קריאה+כתיבה מול PG עובד (raw). [ ] commit · `git log -1`.

## Invariants
localhost-PG בלבד · ❌ לא Render/Upstash/prod-PG · אנטי-טאוטולוגי (טסט שנכשל אם הקוד מתהפך) + סעיף NOT-DONE · Cowork מאמת בלתי-תלוי. אחרי ירוק → פותחים SHADOW soak.
