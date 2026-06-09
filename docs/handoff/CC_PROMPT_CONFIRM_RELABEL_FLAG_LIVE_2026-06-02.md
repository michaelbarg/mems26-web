# CC PROMPT — ודא שדגל ה-relabel דלוק ב-SHADOW + שיש תיעוד ל-HFE · 2026-06-02

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.**
**תווית:** `D-WDIAG` · **מאת:** Michael → **אל:** Claude Code
**מטרה:** לוודא שהמנגנון באמת ייצר נתוני השוואה ב-SHADOW. בלי לשנות קוד — בדיקה + ראיה גולמית (Rule 5).

## 1 · הדגל דלוק ב-backend הרץ? (לא בקוד — ב-runtime)
הדפס את הערך **החי** של `S4_EXTREME_TREND_RELABEL` מתוך ה-backend הרץ ב-SHADOW (לא מ-`atr.py` שברירת-המחדל שלו OFF). למשל endpoint/health שמחזיר את הדגלים, או `print` מתוך התהליך הרץ, או הצגת ה-plist בפועל (`~/Library/LaunchAgents/...plist` → ה-`EnvironmentVariables`).
- **הדבק:** את הערך החי + מהיכן נקרא (plist/env).
- אם הוא **OFF** ב-runtime → זה אומר שלא ייאסף שום נתון. דווח, והצע איפה להדליק (plist `EnvironmentVariables` + reload).

## 2 · יש תיעוד ל-HFE שיורה? (כדי שתהיה השוואה)
הראה איפה נרשם כש-HFE מנותב ב-SHADOW על בר ±200:
- האם זה נכנס לטבלת ה-shadow trades / signals הרגילה? (איזו טבלה, איזה שדה מזהה שזה HFE על בר extreme?)
- אם **אין** דרך להבחין "HFE שירה בזכות ה-relabel" מ-fires רגילים → הצע תיוג מינימלי (למשל לסמן בלוג/שדה שה-trend עבר relabel באותו בר) כדי שנוכל להשוות "עם relabel" מול "בלי" (האפס ההיסטורי).

## 3 · סיכום השוואה
תאר במשפט: ברגע שיגיע בר ±200 ב-RTH עם הדגל ON — מה בדיוק נראה (איפה, איזה רשומה), ואיך משווים לאפס הקודם.

## פורמט (חוזה §C)
טבלת בדיקות (DONE/NOT-DONE + raw output) · סעיף NOT DONE / DEVIATIONS · open. אל תכתוב "דלוק" בלי פלט חי.
