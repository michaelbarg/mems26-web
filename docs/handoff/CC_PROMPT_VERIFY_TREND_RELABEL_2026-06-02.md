# CC PROMPT — Verify Extreme-CCI Trend Relabel (test + shadow proof) · 2026-06-02

**תווית:** `D-WDIAG` · **מאת:** Michael → **אל:** Claude Code
**רקע:** commit `b2be53c` מימם את ה-relabel במקור יחיד (`studies["trend_state"]` בשורה ~278, מאחורי דגל `S4_EXTREME_TREND_RELABEL`, default OFF). **המיקום נכון — אבל אין טסט ואין הוכחה שזה עובד.** הפרומפט הזה משלים רק את האימות. **אל תשנה את הלוגיקה.**

> Rule 5: הדבק `command + raw output` לכל טענה. אל תכתוב "עובד" בלי פלט.

## 1 · טסט regression
הוסף טסט ל-`tests/`:
- **דגל OFF:** בר עם `trend_state=GRAY` + `cci_14=331` → `studies["trend_state"]` נשאר **GRAY** (זהה להתנהגות לפני התיקון).
- **דגל ON:** אותו בר → `studies["trend_state"]` הופך ל-**BLUE**, **וגם** `decision_tree._a1_trend_gate` רואה BLUE (לא GRAY), וה-HFE מגיע ל-`ready_to_route=True`.
- בר רגיל (CCI=80, GRAY) עם דגל ON → נשאר GRAY (לא משנה ברים לא-קיצוניים).
הדבק פלט `pytest` ירוק.

## 2 · אימות shadow חי
הדלק `S4_EXTREME_TREND_RELABEL=1` ב-SHADOW והדבק ראיה:
- בר ±200 שבעבר נחסם → עכשיו `ready_to_route=True` וה-HFE מנותב (פלט/לוג).
- ברים רגילים (לא ±200) → **אפס** fires חדשים/שגויים.
אם יש רעש (fires שגויים) → דווח ו**אל תשאיר דלוק**.

## 3 · עצור לאישור
אחרי ההוכחה — **עצור ושאל את Michael** לפני שמשאירים את הדגל ON קבוע ב-live.

## בסיום
עדכן `DECISION_LEDGER.md` + `STATUS_BOARD.md` עם פלט האימות (Rule 5). תווית `D-WDIAG`.
