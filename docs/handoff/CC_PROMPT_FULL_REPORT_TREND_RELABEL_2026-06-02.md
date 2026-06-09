# CC PROMPT — דוח מלא: D-WDIAG trend relabel (מצב + הסבר עצמי) · 2026-06-02

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.**
**תווית:** `D-WDIAG` · **מאת:** Michael → **אל:** Claude Code
**זה בקשת דוח בלבד — אל תשנה קוד.** תכתוב דוח מלא לפי תבנית החוזה (§C), עם ראיה גולמית (Rule 5) ו**הסבר עצמי כן** (§B3) על מה שלא בוצע ולמה.

## מה הדוח חייב לכלול

1. **מה מומש** (`b2be53c`): היכן בדיוק נמצא ה-relabel, ולמה זה "מקור יחיד". הדבק את הקטע.

2. **הטסט (`c9f3883`) — הסבר מלא:** הטסט הנוכחי **מדמה** את הלוגיקה (`# Simulate the relabel logic`) ולא קורא ל-`process_bar`/`decision_tree`. הסבר **למה** בחרת לדמות במקום לקרוא לקוד האמיתי:
   - מה חוסם טסט אינטגרציה אמיתי? (`process_bar` דורש event/gateway/DB/async? משהו אחר?) — תאר במדויק.
   - **מבחן הליטמוס (§B1):** האם אם מבטלים את התיקון ב-`woodies_system.py` הטסט הנוכחי הופך אדום? הרץ והוכח. אם לא → הצהר שהטסט לא תקף.

3. **מה לא בוצע (§B3 NOT DONE / DEVIATIONS):** רשום במפורש כל פריט מפרומפט האימות שלא בוצע + הסיבה:
   - טסט שקורא לקוד אמיתי (`_a1_trend_gate`/`decision_tree`) — בוצע? אם לא, למה?
   - הוכחת shadow (HFE מנותב על בר ±200, אפס fires שגויים) — בוצע? אם לא, למה?

4. **המלצתך:** מה הדרך הריאלית להוכיח שזה עובד — טסט ישיר על `decision_tree._a1_trend_gate` עם `studies` שעבר relabel (קוד אמיתי, קל מ-`process_bar` מלא) + shadow? או דרך אחרת? נמק.

## פורמט (חוזה §C)
טבלת phases (DONE/PARTIAL/NOT-DONE + evidence) · שורת "if reverted → RED/GREEN because ___" לטסט הקיים · סעיף NOT DONE / DEVIATIONS · open items. **אל תכתוב "בוצע" בלי command+output.**
