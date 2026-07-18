# CC משימה 1 — סטופ-מגן אוטומטי לפוזיציה-יתומה (ORPHAN_AUTO_STOP_V1)

**פסיקת-מייקל 2026-07-17 (בכתב, "מאשרת"):** גוברת על הדחייה הקודמת של auto-adopt המתועדת ב-
`recommend_orphan_stop` docstring. **מטרה: פוזיציה-לא-מתועדת לא תשב עירומה — המערכת תניח לה סטופ-מגן.**
**מבצע: cc-imac (Claude Code). מאמת: cowork-dev. יעד: מסחר-תקין ביום שני.**

## הראיה שהצדיקה את זה (07-17 בערב, כסף-אמת)
```
23:05:07 [Reconciler] SYS-3 DIVERGENCE: TM says 0 contracts [], Sierra says -5 (src=state).
  🔴 NAKED ORPHAN SHORT 5c @ 7502.7 → PLACE PROTECTIVE STOP @ 7512.75 (10pt).
```
5 חוזים שורט **בלי סטופ** על החשבון החי. הרקונסיילר זיהה נכון, חישב את הסטופ המדויק — **ולא עשה כלום**
(`phantom-heal streak 0/3`, alert-only). לולא מייקל היה שם, פוזיציה עירומה הייתה יושבת בלי הגנה
(וזו החזרה השלישית: 07-10, 07-14, 07-17).

## מה לבנות

**דגל `ORPHAN_AUTO_STOP_V1`, default OFF.** כשהוא ON וכל התנאים מתקיימים — הנח סטופ-מגן.
**אל תסגור פוזיציה. אל תיגע ב-op=EXIT (שבור, אסור — CLAUDE.md).**

### תנאי-הפעלה (ALL must hold — fail-safe: אם משהו חסר → אל תפעל, השאר את ההתראה כמו היום)
1. `ORPHAN_AUTO_STOP_V1=1`.
2. הרקונסיילר במצב DIVERGENCE-יתום: Sierra `position_qty != 0` **וגם** ה-TM לא מתחזק עסקה תואמת.
3. **הפוזיציה באמת עירומה:** `working_orders == 0` מ-`sierra_state.json` הטרי. אם יש הוראות-עבודה — אל תפעל (יש כבר הגנה).
4. **מקור טרי:** `sierra_state.json` בגיל ≤ `STATE_MAX_AGE_S` (10ש') — אחרת None → אל תפעל (Rule 1).
5. `recommend_orphan_stop()` החזיר dict תקין (לא None).
6. **גודל שפוי:** `abs(qty) <= ORPHAN_AUTO_STOP_MAX_QTY` (ברירת-מחדל 10) — הגנה מפני קריאה משובשת.
7. **חד-פעמיות (idempotency):** לא הונח כבר סטופ לאותה פוזיציה. שמור מפתח
   `(qty, avg_price)` + חותמת; אל תניח שוב באותו מחזור/פוזיציה. אם הפוזיציה השתנתה (qty אחר) — מותר שוב.
8. **קצב:** מקסימום ניסיון אחד ל-N שניות (`ORPHAN_AUTO_STOP_COOLDOWN_S`, ברירת-מחדל 60).

### מה בדיוק להניח
- צד: `LONG→` סטופ מתחת, `SHORT→` סטופ מעל (כבר מחושב ב-`recommend_orphan_stop`: side/qty/entry/stop/points).
- מרחק: `ORPHAN_STOP_POINTS` (10 כברירת-מחדל, כבר קיים).
- כמות: בדיוק `abs(position_qty)` — לכסות את כל הפוזיציה.

### ⚠️ החקירה שחייבת להיות ראשונה (אל תנחש)
**האם ה-DLL תומך בהנחת סטופ עצמאי לפוזיציה קיימת?** קרא `sc_study/MES_AI_DataExport.cpp` +
`docs/runbooks/SIERRA_DLL_OPS.md` + `backend/v9/services/sierra_command.py` וקבע:
- אם קיים op שמניח stop-order עצמאי (לא bracket שלם, לא EXIT) → השתמש בו.
- אם `MODIFY_STOP` דורש trade_id מתועד → בדוק אם אפשר לאמץ (adopt) את היתום לרשומת-TM מינימלית ואז MODIFY_STOP.
- אם **אין** נתיב בטוח קיים → **אל תמציא op חדש**. במקום זה: דווח בדיוק מה חסר, והשאר את ההתראה
  כפי שהיא. זה תוצר לגיטימי — עדיף לא-לפעול מאשר לשלוח פקודה שה-DLL יפרש לא-נכון על כסף-אמת.

## בטיחות (חובה)
- כל הבלוק ב-`try/except` — **הרקונסיילר לעולם לא נופל** בגלל הפיצ'ר הזה; שגיאה → לוג + ההתראה הרגילה.
- לוג CRITICAL + `ops_log` (`scripts/ops_log.py log_event`) + phone push על **כל** הנחה: qty/entry/stop/תוצאה.
- כשלון-הנחה → מיד להסלים להתראה הקיימת (לא לבלוע).
- אפס שינוי בהתנהגות כשהדגל OFF (byte-identical).

## טסטים (anti-tautological, לא-טאוטולוגיים — לפי CC_HANDOFF_CONTRACT)
`tests/v9/regression/test_orphan_auto_stop.py`:
1. דגל OFF + יתום-עירום → **לא** מונח סטופ, ההתראה כמו היום (pin ההתנהגות הישנה).
2. דגל ON + שורט-יתום ‎-5 @7502.7, working=0, state טרי → מונח סטופ **מעל** במרחק 10pt (7512.75), qty=5.
3. מראה: לונג-יתום ‎+3 → סטופ **מתחת**.
4. `working_orders>0` → **לא** מונח (כבר מוגן).
5. state בגיל 30ש' (מעופש) → **לא** מונח (Rule 1).
6. `qty=50` (מעל MAX_QTY) → **לא** מונח.
7. חד-פעמיות: שתי קריאות רצופות באותה פוזיציה → **הנחה אחת בלבד**.
8. הנחה נכשלת (stub זורק) → הרקונסיילר לא קורס + ההתראה עדיין נשלחת.
9. אין-רגרסיה: המקרה ה"בריא" (TM ו-Sierra תואמים) לא נגוע.

הרץ גם: `tests/v9/regression/test_fix13_state_reconcile.py` + `test_trade_reality_detection.py` (חייבים להישאר ירוקים).

## ממשל (governance)
- `docs/FLAG_REGISTRY.yaml`: 3 ערכים — `ORPHAN_AUTO_STOP_V1` (risk, default OFF, why=הפסיקה+הראיה),
  `ORPHAN_AUTO_STOP_MAX_QTY`, `ORPHAN_AUTO_STOP_COOLDOWN_S`. הרץ `gen_flag_index.py`.
- **אל תיגע ב-`config/RULED_FLAGS.yaml` ואל תדליק ב-.env** — ההדלקה היא פסיקה נפרדת של מייקל אחרי אימות-סים.
- `python3 scripts/gen_index.py` אחרי הוספת קבצים.

## אימות שתחזיר (חוק-5 — פקודה + פלט גולמי, לא "עובד")
1. `pytest tests/v9/regression/test_orphan_auto_stop.py test_fix13_state_reconcile.py test_trade_reality_detection.py -q` — פלט מלא.
2. הוכחת-RED: הפוך זמנית את התיקון → הטסט הרלוונטי נכשל → החזר. הדבק את שני הפלטים.
3. **אימות-סים (חובה לפני שמייקל ידליק):** על Sierra-סים (`is_sim=1` מאומת) — צור פוזיציה-יתומה
   (כניסה ידנית בסים בלי שהמערכת תדע), הדלק את הדגל בסביבת-הסים בלבד, והראה: הסטופ הונח בפועל
   בצד ובמחיר הנכונים, הפוזיציה מוגנת, ולוג/פלאפון קיבלו. הדבק את שורות-הלוג ואת מצב-הסיירה.
4. סעיף **NOT-DONE** חובה: מה לא נעשה/לא-ודאי (במיוחד אם נתיב-ה-DLL לא נמצא).

## הקשר
`docs/handoff/EOD_REPORT_2026-07-17.md` · `docs/handoff/PATTERN_MGMT_AUDIT_2026-07-17.md` ·
S-9 (07-10/07-14/07-17 החזרות) · `CLAUDE.md` §op=EXIT-שבור §Standing-Decisions.
