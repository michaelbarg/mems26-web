# CC — day_type=UNKNOWN (root) + Woodies A5 mislabel · 2026-06-05 (RTH live)

מקור-אמת: **Sierra v9_export + הגשר** (לא חישובי-בקנד/API). כל "DONE" = פקודה + raw
output (Rule 5) + NOT-DONE. אל תיגע בלוגיקת-מסחר/סיווג בלי אישור Michael — A הוא
diagnose-only; B הוא תיקון-תצוגה בלבד.

═══════════════════════════════════════
## A · 🔴 day_type=UNKNOWN 30+ דק' לתוך RTH — diagnose-first (root)
═══════════════════════════════════════
**למה זה חמור:** UNKNOWN מקרין — S2 מדלג בשקט על תבניות-יום (Pkg 5a/5b/5c,
`five_min_system.py:857`), ו-Woodies A2 (day_type query) מנוון. כנראה משתק חלק מהירי.

**השערה (מהקוד):** S1 מחזיר UNKNOWN כשחסר קלט (`detector.py:137`), תואם לבאג הידוע
"`bar.atr`=None → re-eval מת". **אמת מול הקלט האמיתי, לא תתקן מהזיכרון.**

שלוף והדבק raw:
1. **קלט-Sierra לפתיחה** — מ-`~/SierraChart_Data/v9_export/`: 3–6 הברים הראשונים מ-08:30 CT
   (OHLC, IB high/low), ו-`atr_daily`/ATR14 שמגיע (או חסר) ל-S1. האם Sierra מייצאת את זה?
2. **state + לוג של S1** — `grep -i "day_type\|S1\|opening\|atr\|reeval\|UNKNOWN"` בלוג-הבקנד מ-08:30 CT;
   ו-`SELECT * FROM v9_day_type_state ORDER BY id DESC LIMIT 5` (stage/classification/lock_state/atr).
3. **אבחן את החתך המדויק:** האם `atr_daily` מגיע ל-`classify_ib_width_atr`/`detect_opening_type`?
   האם ה-opening type סווג (3 ברים) או תקוע? האם ה-re-eval/staging נחסם?
4. **דווח root ל-Michael** (classifier = trading-logic → strategic-stop). אל תתקן לפני אישור.

═══════════════════════════════════════
## B · 🟡 Woodies "A5 חוסם" — תיקון-תצוגה (לא-מסחרי)
═══════════════════════════════════════
**הממצא (אומת ב-Cowork):** `a5_otf_clarity_query.py:47` — A5 הוא **"Advisory only —
returns warnings, NEVER blocks entry."** A5 מחזיר רק אזהרה (`NONE`/`NO_CLARITY`/
`DIRECTION_MISMATCH`), הוא **לא יכול לחסום ירי**. אם ה-decision-tree/build_status מציג
"לא ירה בגלל A5" — **זו תקלת-תצוגה**, והחסימה האמיתית במקום אחר (A1 strategic / A3 no-pattern /
A7 universal / gateway).

תקן:
1. אתר היכן ה-decision-tree/build_status ממפה A5 כ-reject/block reason. ודא ש-A5 מוצג כ-
   **advisory warning** ולא כסיבת-חסימה.
2. ודא שה-reason המוצג כשאין ירי הוא ה-**שלב-החוסם האמיתי** (A1/A3/A7/gateway `blocked_by`),
   לא A5.
3. regression: setup שבו A5=`NO_CLARITY`/`DIRECTION_MISMATCH` אבל A3 מצא תבנית תקינה →
   הירי **לא** נחסם בגלל A5; וכשאין תבנית → ה-reason=A3 (לא A5). revert→RED.

═══════════════════════════════════════
## הקשר
שני אלה + ה-ZLR (A3 לא מצא תבנית) נכנסים לדוח-הדיאגנוסטיקה (`CC_PROMPT_PATTERN_DIAGNOSTICS_2026-06-05.md`).
NOT-DONE: כל קלט-Sierra שלא נמצא, וכל פער Sierra↔backend.
