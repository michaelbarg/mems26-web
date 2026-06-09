# פרומפט CC — תיקון באג TZ ב-BarLevelDetector (מאושר Michael 31/5)

> להדבקה ב-Claude Code. **קרא קודם `CLAUDE.md` (Rule 4 TZ · No silent failures).**
> מבוסס אבחון: `docs/reports/DIAGNOSE_T1_TZ_2026-05-31.md`. **היקף מצומצם בלבד.**
> Michael אישר: **לא** משנים כוונת ההשוואה/רמות/כללים — רק נרמול TZ + הסרת בליעה.

---

## מה לתקן (בדיוק זה, לא יותר)

### 1. נרמול TZ — `bar_level_detector.py:87-92` (Option B · aware-UTC)
הבעיה: `if not hasattr(trade_entry, "tzinfo")` תמיד True (באג); ו-`entry_ts` חוזר
naive מ-SQLite מול `bar_ts` aware → TypeError.

```python
from datetime import timezone
...
if bar_ts is not None and trade.entry_ts is not None:
    trade_entry = trade.entry_ts
    if trade_entry.tzinfo is None:
        trade_entry = trade_entry.replace(tzinfo=timezone.utc)
    if bar_ts.tzinfo is None:
        bar_ts = bar_ts.replace(tzinfo=timezone.utc)
    if bar_ts < trade_entry:
        continue
```
**אסור** לשנות את כוונת ה-guard (לדלג על ברים שלפני entry) או רמות T1/T2/stop.

### 2. הסרת הבליעה השקטה — ה-`except Exception` (~שורה 127)
היום ה-TypeError נבלע → T1 לא נתפס בשקט. שנה כך שהשגיאה **תירשם**
(`logger.warning`, rate-limited אם צריך) במקום להיבלע. **אל תרחיב** את ה-except
ל-bare/pass — שיתפוס, יירשם, וימשיך (או יקרוס בצורה גלויה, לפי הדפוס הקיים).

**אסור:** כל שינוי אחר ב-`bar_level_detector` · לגעת ברמות/כללים/מערכות אחרות.

---

## רגרסיה (חובה)
1. `tests/atomic/test_cross_system_integration.py::test_bar_level_detector_closes_trades` → **PASS**.
2. טסט חדש: bar עם ts **naive** (בלי offset) מטופל נכון (UTC).
3. טסט חדש: bar עם ts **לפני** entry_ts **מדולג** (כוונת ה-guard נשמרת).
4. טסטי `test_bar_level_detector_entry_guard` הקיימים ממשיכים לעבור.
5. **`pytest tests/ -q` מלא = 0 failed** (זה סוגר את ה-1 שנשאר). הדבק raw.

## השפעת SHADOW (לתעד — זה משנה התנהגות לכיוון הנכון)
אחרי התיקון ה-detector יתחיל לתפוס T1/T2/T3/stop. עסקאות שהיו "תקועות פתוחות" כי
ה-target לא נתפס **עלולות להיסגר** — ייתכן backlog בהרצה הראשונה. תעד baseline:
כמה עסקאות active לפני, כמה נסגרות בריצת ה-detector הראשונה אחרי, ולמה. זו התנהגות
**תקינה** (targets אמורים להיתפס), אבל לתעד כדי שלא יראה כאנומליה.

## תוצר
`docs/reports/FIX_T1_TZ_2026-05-31.md`: ה-diff (2 השינויים בלבד), פלט רגרסיה גולמי
(5 הבדיקות), `pytest -q` = 0 failed, ו-baseline SHADOW לפני/אחרי.

## אסור
שינוי כוונת ההשוואה/רמות/כללי מסחר · "תוך כדי" refactor · לגעת ב-order/sizing/risk ·
to bury errors שוב. רק 2 השינויים שאושרו.
