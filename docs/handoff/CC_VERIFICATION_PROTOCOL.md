# CC ↔ Cowork · Verification Protocol (STANDING — every task)

מטרה: לסגור כל משימה **פעם אחת**, בלי הלוך-ושוב. CC כותב ראיות לקובץ; Cowork סוקר
את הקובץ **ומצליב בלתי-תלוי**. משלים את `CC_HANDOFF_CONTRACT.md`.

## כלל-הזהב
שום טענה ("עובד" / "confirmed" / "passed") **בלי הפקודה + הפלט הגולמי מתחתיה** (Rule 5).
סיכום בלי raw output = לא קביל.

## 1. CC — בסיום כל משימה, כתוב קובץ-אימות אחד
נתיב קבוע: **`docs/reports/VERIFY_<TASK-ID>_<YYYY-MM-DD>.md`**
(למשל `docs/reports/VERIFY_CUTOVER_2026-06-05.md`).

המבנה (חובה, בסדר הזה):

```
# VERIFY <TASK-ID> · <תאריך>

## 1. SCOPE
מה התבקש (קישור לפרומפט) + מה במשימה הזו / מה לא.

## 2. CHANGES
git log --oneline -N   ← הדבק
git status --short      ← הדבק (מה committed / uncommitted)
git diff --stat <base>..HEAD ← הדבק

## 3. EVIDENCE (פר פריט-קבלה)
לכל פריט: שורת ```command``` ואז בלוק ```פלט גולמי```. בלי סיכום באמצע.

## 4. TESTS
pytest <files> -v   ← הדבק את הסיכום (X passed/Y failed) + כל FAIL.
RED-on-revert: הוכח שכל regression חדש נכשל על הקוד הישן (הדבק).

## 5. RUNTIME
curl/psql גולמי שמוכיח שהשינוי **פעיל בשרת הרץ** (לא רק בקובץ).

## 6. NOT-DONE
מה לא נעשה/נדחה ולמה. שדה שמקורו שותק ונשאר NULL. כל הסתייגות.

## 7. CONFIG VALUES
כל ערך-סף/risk שהוזן + אישור Michael (כן/לא/ממתין).
```

## 2. Cowork — לולאת-הסקירה (בלתי-תלויה)
1. קרא את קובץ-האימות.
2. **הצלב כל פריט בעצמי** מול: הקוד/git (repo ממונט) · ה-API החי (Chrome→`localhost:8000`) ·
   הרצה-חוזרת היכן שאפשר. לא לקבל מספר בלי לשחזר אותו ממקור-אמת.
3. כל טענה שאי-אפשר לשחזר → לסמן במפורש "לא-מאומת בלתי-תלוי" + מה צריך כדי לאמת.
4. תוצר: **GO / NO-GO** עם רשימת מה-אומת ✅ / מה-חסר ⛔ — בלי הלוך-ושוב.

## 3. אסור
- "הכל עובד" בלי raw. · הסבר במקום פלט (כמו "ps לא מציג — מגבלת-תצוגה") בלי הוכחה חלופית.
- לאשר reset/restart/LIVE לפני שקובץ-האימות מלא ו-Cowork נתן GO.

## 4. תבנית קבועה — Cowork מבקש סגירה
> "כתוב `docs/reports/VERIFY_<TASK>_<תאריך>.md` לפי `CC_VERIFICATION_PROTOCOL.md` —
> 7 הסעיפים, raw output לכל פריט. אל תסכם 'עובד'. כשמוכן — תגיד, ואני סוקר ומצליב."
