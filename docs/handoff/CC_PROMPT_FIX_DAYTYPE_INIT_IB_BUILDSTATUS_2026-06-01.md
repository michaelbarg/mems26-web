# CC PROMPT — תיקון כשל אתחול day-type (IB + סוג-יום לא מזוהים) + Build Status

**תאריך:** 2026-06-01 (RTH חי) · **מקור:** Cowork (Michael) · **מצב:** SHADOW · Rule 5 · אפס שינוי order/risk/sizing.
**הקשר:** Michael עשה Remote Build (`4984cd1`, תיקון TPO/IB study reading). אבל **IB של היום עדיין לא מזוהה + day-type תקוע A1**. שורש (CC, דוח קודם): **מכונת ה-day-type לא מקבלת ברים** — `bar_count=0`, המנוי `_day_type_on_bar` נשבר אחרי restart (כשל אתחול שקט; `.env` לא נטען ב-LaunchAgent → לוגינג מושתק → השגיאה נבלעה). מערכות אחרות (TPO/Footprint/FiveMin) כן מקבלות. **תיקון אחד פותר את שלושתם: day-type + IB + Build Status.**

## P1 · לחשוף ולתקן את כשל האתחול (תשתית — לא לוגיקה)
1. הוסף `print()` (לא logger — print עובד בלי .env) או `logging.basicConfig(level=logging.INFO)` בראש `main.py`, בבלוק אתחול ה-DayType (~`main.py:141-339`), כדי **לחשוף את החריגה הנבלעת**.
2. restart, לכוד את השגיאה המדויקת, **תקן** כך ש: `day_type_machine` נוצר במלואו + `bar_router.subscribe("5min", _day_type_on_bar)` רץ + המכונה מקבלת ברים.
3. **תקן את השורש:** `.env` לא נטען ב-LaunchAgent → לוגינג/קונפיג חסר (תקלות שקטות). ודא שה-mems26 logger ב-INFO גם תחת LaunchAgent (לא להסתיר שגיאות עתידיות).

## P2 · אימות שחזור (Rule 5)
אחרי התיקון, ב-RTH:
- `bar_count` עולה · `_day_type_on_bar` נקרא (לוג).
- **IB מזוהה:** ib_high/ib_low מתמלאים + width + lock בזמן (10:30 ET).
- **day-type מתקדם** מעבר ל-A1 ומסווג (opening_type, vote, confidence) — **לפי האפיון** (אם עדיין לא לפי האפיון אחרי שמקבל ברים → diagnose נפרד, strategic-stop).
- POC/VAH/VAL תואמים Sierra chart 3 (אחרי ה-Remote Build).

## P3 · Build Status — להציג S1 (day-type + פתיחה + IB)
מקור: `CC_PROMPT_BUILD_STATUS_DAYTYPE_OPENING_VISIBILITY_2026-06-01.md`. אחרי שהמכונה מקבלת ברים — להציג section S1 מסודר (opening_type+conf · IB high/low/width/class/lock · day_type vote · lock_state · confidence · stage), Live/Required/Present, כך ש-Michael רואה שהמערכת מזהה ומטפלת.

## פלט
`docs/reports/FIX_DAYTYPE_INIT_IB_2026-06-01.md`: השגיאה הנבלעת שנחשפה + diff התיקון · אימות bar_count עולה + IB מזוהה + day-type מתקדם + Build Status מציג. עדכון STATUS_BOARD.

**שערים:** P1 = תיקון תשתית/אתחול (בטוח, לא לוגיקת-day-type). אם נדרש שינוי **לוגיקת** הסיווג → strategic-stop + אישור Michael. אפס שינוי order/risk/sizing.
